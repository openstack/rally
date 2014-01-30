# Copyright 2013: Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import collections
import functools
import multiprocessing
from multiprocessing import pool as multiprocessing_pool
import random
import sys
import time
import uuid

from rally.benchmark import base
from rally.benchmark import utils
from rally import exceptions
from rally.openstack.common.gettextutils import _
from rally.openstack.common import log as logging
from rally import utils as rutils


LOG = logging.getLogger(__name__)


# NOTE(msdubov): These objects are shared between multiple scenario processes.
__openstack_clients__ = {}
__admin_clients__ = []


def _run_scenario_loop(args):
    i, cls, method_name, kwargs = args

    LOG.info("ITER: %s" % i)

    # TODO(boris-42): remove context
    scenario = cls(context={},
                   admin_clients=__admin_clients__,
                   clients=random.choice(__openstack_clients__))

    try:
        scenario_output = None
        with rutils.Timer() as timer:
            scenario_output = getattr(scenario, method_name)(**kwargs)
        error = None
    except Exception as e:
        error = utils.format_exc(e)
    finally:
        return {"time": timer.duration() - scenario.idle_time(),
                "idle_time": scenario.idle_time(), "error": error,
                "scenario_output": scenario_output,
                "atomic_actions_time": scenario.atomic_actions_time()}


class UserGenerator(object):
    """Context class for generating temporary users/tenants for benchmarks."""

    def __init__(self, admin_clients):
        self.keystone_client = admin_clients["keystone"]

    def _create_user(self, user_id, tenant_id):
        pattern = "%(tenant_id)s_user_%(uid)d"
        name = pattern % {"tenant_id": tenant_id, "uid": user_id}
        email = "%s@email.me" % name
        return self.keystone_client.users.create(name, "password",
                                                 email, tenant_id)

    def _create_tenant(self, run_id, i):
        pattern = "temp_%(run_id)s_tenant_%(iter)i"
        return self.keystone_client.tenants.create(pattern % {"run_id": run_id,
                                                              "iter": i})

    def create_users_and_tenants(self, tenants, users_per_tenant):
        run_id = str(uuid.uuid4())
        auth_url = self.keystone_client.auth_url
        self.tenants = [self._create_tenant(run_id, i)
                        for i in range(tenants)]

        self.users = []
        endpoints = []
        for tenant in self.tenants:
            for user_id in range(users_per_tenant):
                user = self._create_user(user_id, tenant.id)
                self.users.append(user)
                endpoints.append({'auth_url': auth_url,
                                  'username': user.name,
                                  'password': "password",
                                  'tenant_name': tenant.name})
        return endpoints

    def _delete_users_and_tenants(self):
        for user in self.users:
            try:
                user.delete()
            except Exception:
                LOG.info("Failed to delete user: %s" % user.name)

        for tenant in self.tenants:
            try:
                tenant.delete()
            except Exception:
                LOG.info("Failed to delete tenant: %s" % tenant.name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._delete_users_and_tenants()

        if exc_type:
            LOG.debug(_("Failed to generate temporary users."),
                      exc_info=(exc_type, exc_value, exc_traceback))
        else:
            LOG.debug(_("Completed deleting temporary users and tenants."))


class ResourceCleaner(object):
    """Context class for resource cleanup (both admin and non-admin)."""

    def __init__(self, admin=None, users=None):
        self.admin = admin
        self.users = users

    def _cleanup_users_resources(self):
        if not self.users:
            return

        for user in self.users:
            methods = [
                functools.partial(utils.delete_nova_resources, user["nova"]),
                functools.partial(utils.delete_glance_resources,
                                  user["glance"], user["keystone"]),
                functools.partial(utils.delete_cinder_resources,
                                  user["cinder"])
            ]

            for method in methods:
                try:
                    method()
                except Exception as e:
                    LOG.debug(_("Not all resources were cleaned."),
                              exc_info=sys.exc_info())
                    LOG.warning(_('Unable to fully cleanup the cloud: \n%s') %
                                (e.message))

    def _cleanup_admin_resources(self):
        if not self.admin:
            return

        try:
            utils.delete_keystone_resources(self.admin["keystone"])
        except Exception as e:
            LOG.debug(_("Not all resources were cleaned."),
                      exc_info=sys.exc_info())
            LOG.warning(_('Unable to fully cleanup keystone service: %s') %
                        (e.message))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._cleanup_users_resources()
        self._cleanup_admin_resources()

        if exc_type:
            LOG.debug(_("An error occurred while launching "
                        "the benchmark scenario."),
                      exc_info=(exc_type, exc_value, exc_traceback))
        else:
            LOG.debug(_("Completed resources cleanup."))


class ScenarioRunner(object):
    """Tool that gets and runs one Scenario."""

    def __init__(self, task, endpoint):
        base.Scenario.register()

        self.task = task
        self.endpoint = endpoint

        global __admin_clients__
        keys = ['username', 'password', 'tenant_name', 'auth_url']
        __admin_clients__ = utils.create_openstack_clients([self.endpoint],
                                                           keys)[0]

    def _run_scenario_continuously_for_times(self, cls, method, args,
                                             times, concurrent, timeout):
        test_args = [(i, cls, method, args) for i in xrange(times)]

        pool = multiprocessing.Pool(concurrent)
        iter_result = pool.imap(_run_scenario_loop, test_args)

        results = []

        for i in range(len(test_args)):
            try:
                result = iter_result.next(timeout)
            except multiprocessing.TimeoutError as e:
                result = {"time": timeout, "idle_time": 0,
                          "error": utils.format_exc(e)}
            results.append(result)

        pool.close()
        pool.join()

        return results

    def _run_scenario_continuously_for_duration(self, cls, method, args,
                                                duration, concurrent, timeout):
        pool = multiprocessing.Pool(concurrent)
        run_args = utils.infinite_run_args((cls, method, args))
        iter_result = pool.imap(_run_scenario_loop, run_args)

        start = time.time()

        results_queue = collections.deque([], maxlen=concurrent)

        while True:

            if time.time() - start > duration * 60:
                break

            try:
                result = iter_result.next(timeout)
            except multiprocessing.TimeoutError as e:
                result = {"time": timeout, "idle_time": 0,
                          "error": utils.format_exc(e)}
            results_queue.append(result)

        results = list(results_queue)

        pool.terminate()
        pool.join()

        return results

    def _run_scenario_periodically(self, cls, method, args,
                                   times, period, timeout):
        async_results = []

        for i in xrange(times):
            thread = multiprocessing_pool.ThreadPool(processes=1)
            async_result = thread.apply_async(_run_scenario_loop,
                                              ((i, cls, method, args),))
            async_results.append(async_result)

            if i != times - 1:
                time.sleep(period * 60)

        results = []
        for async_result in async_results:
            try:
                result = async_result.get()
            except multiprocessing.TimeoutError as e:
                result = {"time": timeout, "idle_time": 0,
                          "error": utils.format_exc(e)}
            results.append(result)

        return results

    def _run_scenario(self, cls, method, args, execution_type, config):
        # TODO(boris-42): This method should be replaced by OOP

        timeout = config.get("timeout", 600)

        if execution_type == "continuous":

            concurrent = config.get("active_users", 1)

            # NOTE(msdubov): If not specified, perform single scenario run.
            if "duration" not in config and "times" not in config:
                config["times"] = 1

            # Continiously run a benchmark scenario the specified
            # amount of times.
            if "times" in config:
                times = config["times"]
                return self._run_scenario_continuously_for_times(
                                cls, method, args, times, concurrent, timeout)

            # Continiously run a scenario as many times as needed
            # to fill up the given period of time.
            elif "duration" in config:
                duration = config["duration"]
                return self._run_scenario_continuously_for_duration(
                            cls, method, args, duration, concurrent, timeout)

        elif execution_type == "periodic":

            times = config["times"]
            period = config["period"]

            # Run a benchmark scenario the specified amount of times
            # with a specified period between two consecutive launches.
            return self._run_scenario_periodically(cls, method, args,
                                                   times, period, timeout)

    def _prepare_and_run_scenario(self, name, kwargs):

        cls_name, method_name = name.split(".")
        cls = base.Scenario.get_by_name(cls_name)

        args = kwargs.get('args', {})
        execution_type = kwargs.get('execution', 'continuous')
        config = kwargs.get('config', {})

        # TODO(boris-42): Validation should in benchmark.engine not here
        method = getattr(cls, method_name)
        validators = getattr(method, "validators", [])
        for validator in validators:
            result = validator(clients=__admin_clients__, **args)
            if not result.is_valid:
                raise exceptions.InvalidScenarioArgument(message=result.msg)

        # TODO(boris-42): Remove _run_scenario (and use subclasses)
        return self._run_scenario(cls, method_name, args, execution_type,
                                  config)

    def _run_as_admin(self, name, kwargs):
        global __openstack_clients__, __admin_clients__
        config = kwargs.get('config', {})

        with UserGenerator(__admin_clients__) as generator:
            tenants = config.get("tenants", 1)
            users_per_tenant = config.get("users_per_tenant", 1)
            temp_users = generator.create_users_and_tenants(tenants,
                                                            users_per_tenant)
            keys = ["username", "password", "tenant_name", "auth_url"]
            __openstack_clients__ = utils.create_openstack_clients(temp_users,
                                                                   keys)
            with ResourceCleaner(admin=__admin_clients__,
                                 users=__openstack_clients__):
                return self._prepare_and_run_scenario(name, kwargs)
        __openstack_clients__ = {}
        __admin_clients__ = []

    def _run_as_non_admin(self, name, kwargs):
        global __openstack_clients__

        # TODO(boris-42): Somehow setup clients from deployment/config
        with ResourceCleaner(users=__openstack_clients__):
            return self._prepare_and_run_scenario(name, kwargs)
        __openstack_clients__ = {}

    def run(self, name, kwargs):
        if __admin_clients__:
            return self._run_as_admin(name, kwargs)
        else:
            return self._run_as_non_admin(name, kwargs)
