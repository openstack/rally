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
__openstack_clients__ = []
__admin_clients__ = {}
__scenario_context__ = {}


def _run_scenario_loop(args):
    i, cls, method_name, kwargs = args

    LOG.info("ITER: %s" % i)

    scenario = cls(context=__scenario_context__,
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
                "scenario_output": scenario_output}


class ScenarioRunner(object):
    """Tool that gets and runs one Scenario."""
    def __init__(self, task, endpoint):
        self.task = task
        self.endpoint = endpoint

        global __admin_clients__
        keys = ['username', 'password', 'tenant_name', 'auth_url']
        __admin_clients__ = utils.create_openstack_clients([self.endpoint],
                                                           keys)[0]
        base.Scenario.register()

    def _create_temp_tenants_and_users(self, tenants, users_per_tenant):
        run_id = str(uuid.uuid4())
        self.tenants = [__admin_clients__["keystone"].tenants.create(
                            "temp_%(rid)s_tenant_%(iter)i" % {"rid": run_id,
                                                              "iter": i})
                        for i in range(tenants)]
        self.users = []
        temporary_endpoints = []
        for tenant in self.tenants:
            for uid in range(users_per_tenant):
                username = "%(tname)s_user_%(uid)d" % {"tname": tenant.name,
                                                       "uid": uid}
                password = "password"
                user = __admin_clients__["keystone"].users.create(username,
                                                                  password,
                                                                  "%s@test.com"
                                                                  % username,
                                                                  tenant.id)
                self.users.append(user)
                endpoint = {
                    'auth_url': self.endpoint['auth_url'],
                    'username': username,
                    'password': password,
                    'tenant_name': tenant.name,
                }
                temporary_endpoints.append(endpoint)
        return temporary_endpoints

    @classmethod
    def _cleanup_with_clients(cls, indexes):
        for index in indexes:
            clients = __openstack_clients__[index]
            try:
                utils.delete_nova_resources(clients["nova"])
                utils.delete_glance_resources(clients["glance"],
                                              clients["keystone"].project_id)
                utils.delete_cinder_resources(clients["cinder"])
            except Exception as e:
                LOG.debug(_("Not all resources were cleaned."),
                          exc_info=sys.exc_info())
                LOG.warning(_('Unable to fully cleanup the cloud: %s') %
                            (e.message))

    def _cleanup_scenario(self, concurrent):
        indexes = range(0, len(__openstack_clients__))
        chunked_indexes = [indexes[i:i + concurrent]
                           for i in range(0, len(indexes), concurrent)]
        pool = multiprocessing.Pool(concurrent)
        for client_indicies in chunked_indexes:
            pool.apply_async(utils.async_cleanup, args=(ScenarioRunner,
                                                        client_indicies,))
        try:
            utils.delete_keystone_resources(__admin_clients__["keystone"])
        except Exception as e:
            LOG.debug(_("Not all resources were cleaned."),
                      exc_info=sys.exc_info())
            LOG.warning(_('Unable to fully cleanup keystone service: %s') %
                        (e.message))

        pool.close()
        pool.join()

    def _delete_temp_tenants_and_users(self):
        for user in self.users:
            user.delete()
        for tenant in self.tenants:
            tenant.delete()

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
                result = {"time": timeout, "idle_time": cls.idle_time,
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
                result = {"time": timeout, "idle_time": cls.idle_time,
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
                result = {"time": timeout, "idle_time": cls.idle_time,
                          "error": utils.format_exc(e)}
            results.append(result)

        return results

    def _run_scenario(self, cls, method, args, execution_type, config):

        timeout = config.get("timeout", 10000)

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

    def run(self, name, kwargs):
        cls_name, method_name = name.split(".")
        cls = base.Scenario.get_by_name(cls_name)

        args = kwargs.get('args', {})
        init_args = kwargs.get('init', {})
        execution_type = kwargs.get('execution', 'continuous')
        config = kwargs.get('config', {})
        tenants = config.get('tenants', 1)
        users_per_tenant = config.get('users_per_tenant', 1)

        temp_users = self._create_temp_tenants_and_users(tenants,
                                                         users_per_tenant)

        global __openstack_clients__, __scenario_context__

        # NOTE(msdubov): Call init() with admin openstack clients
        cls._clients = __admin_clients__
        __scenario_context__ = cls.init(init_args)

        method = getattr(cls, method_name)
        validators = getattr(method, "validators", [])
        for validator in validators:
            result = validator(clients=__admin_clients__, **args)
            if not result.is_valid:
                raise exceptions.InvalidScenarioArgument(message=result.msg)

        # NOTE(msdubov): Launch scenarios with non-admin openstack clients
        keys = ["username", "password", "tenant_name", "auth_url"]
        __openstack_clients__ = utils.create_openstack_clients(temp_users,
                                                               keys)

        results = self._run_scenario(cls, method_name, args,
                                     execution_type, config)

        self._cleanup_scenario(config.get("active_users", 1))
        self._delete_temp_tenants_and_users()

        return results
