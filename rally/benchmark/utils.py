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

import multiprocessing
import os
import pytest
import random
import traceback
import uuid

import fuel_health.cleanup as fuel_cleanup

from rally.benchmark import base
from rally.openstack.common.gettextutils import _  # noqa
from rally.openstack.common import log as logging
from rally import osclients
from rally import utils


LOG = logging.getLogger(__name__)

# NOTE(msdubov): These objects are shared between multiple scenario processes.
__openstack_clients__ = []
__admin_clients__ = {}
__scenario_context__ = {}


def _format_exc(exc):
    return [str(type(exc)), str(exc), traceback.format_exc()]


def _run_scenario_loop(args):
    i, cls, method_name, kwargs = args

    LOG.info("ITER: %s" % i)

    # NOTE(msdubov): Each scenario run uses a random openstack client
    #                from a predefined set to act from different users.
    cls._clients = random.choice(__openstack_clients__)
    cls._admin_clients = __admin_clients__
    cls._context = __scenario_context__

    cls.idle_time = 0

    try:
        with utils.Timer() as timer:
            getattr(cls, method_name)(**kwargs)
    except Exception as e:
        return {"time": timer.duration() - cls.idle_time,
                "idle_time": cls.idle_time, "error": _format_exc(e)}
    return {"time": timer.duration() - cls.idle_time,
            "idle_time": cls.idle_time, "error": None}

    # NOTE(msdubov): Cleaning up after each scenario loop enables to delete
    #                the resources of the user the scenario was run from.
    cls.cleanup()


def _create_openstack_clients(users_endpoints, keys):
    # NOTE(msdubov): Creating here separate openstack clients for each of
    #                the temporary users involved in benchmarking.
    client_managers = [osclients.Clients(*[credentials[k] for k in keys])
                       for credentials in users_endpoints]

    clients = [
        dict((
            ("nova", cl.get_nova_client()),
            ("keystone", cl.get_keystone_client()),
            ("glance", cl.get_glance_client()),
            ("cinder", cl.get_cinder_client())
        )) for cl in client_managers
    ]

    return clients


class ScenarioRunner(object):
    """Tool that gets and runs one Scenario."""
    def __init__(self, task, cloud_config):
        self.task = task
        self.endpoints = cloud_config

        global __admin_clients__
        keys = ["admin_username", "admin_password", "admin_tenant_name", "uri"]
        __admin_clients__ = _create_openstack_clients([self.endpoints],
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
                user_credentials = {"username": username, "password": password,
                                    "tenant_name": tenant.name,
                                    "uri": self.endpoints["uri"]}
                temporary_endpoints.append(user_credentials)
        return temporary_endpoints

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
                result = {"time": timeout, "error": _format_exc(e)}
            except Exception as e:
                result = {"time": None, "error": _format_exc(e)}
            results.append(result)

        pool.close()
        pool.join()

        return results

    def _run_scenario(self, cls, method, args, execution_type, config):
        timeout = config.get("timeout", 10000)
        times = config.get("times", 1)
        concurrent = config.get("active_users", 1)

        if execution_type == "continuous":
            return self._run_scenario_continuously_for_times(cls, method,
                                                             args, times,
                                                             concurrent,
                                                             timeout)

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

        # NOTE(msdubov): Launch scenarios with non-admin openstack clients
        keys = ["username", "password", "tenant_name", "uri"]
        __openstack_clients__ = _create_openstack_clients(temp_users, keys)

        results = self._run_scenario(cls, method_name, args,
                                     execution_type, config)

        self._delete_temp_tenants_and_users()

        return results


def _run_test(test_args, ostf_config, queue):

    os.environ['CUSTOM_FUEL_CONFIG'] = ostf_config

    with utils.StdOutCapture() as out:
        status = pytest.main(test_args)

    queue.put({'msg': out.getvalue(), 'status': status,
               'proc_name': test_args[1]})


def _run_cleanup(config):

    os.environ['CUSTOM_FUEL_CONFIG'] = config
    fuel_cleanup.cleanup()


class Verifier(object):

    def __init__(self, task, cloud_config_path):
        self._cloud_config_path = os.path.abspath(cloud_config_path)
        self.task = task
        self._q = multiprocessing.Queue()

    @staticmethod
    def list_verification_tests():
        verification_tests_dict = {
            'sanity': ['--pyargs', 'fuel_health.tests.sanity'],
            'smoke': ['--pyargs', 'fuel_health.tests.smoke', '-k',
                      'not (test_007 or test_008 or test_009)'],
            'no_compute_sanity': ['--pyargs', 'fuel_health.tests.sanity',
                                  '-k', 'not infrastructure'],
            'no_compute_smoke': ['--pyargs', 'fuel_health.tests.smoke',
                                 '-k', 'user or flavor']
        }
        return verification_tests_dict

    def run_all(self, tests):
        """Launches all the given tests, trying to parameterize the tests
        using the test configuration.

        :param tests: Dictionary of form {'test_name': [test_args]}

        :returns: List of dicts, each dict containing the results of all
                  the run() method calls for the corresponding test
        """
        task_uuid = self.task['uuid']
        res = []
        for test_name in tests:
            res.append(self.run(tests[test_name]))
            LOG.debug(_('Task %s: Completed test `%s`.') %
                      (task_uuid, test_name))
        return res

    def run(self, test_args):
        """Launches a test (specified by pytest args).

        :param test_args: Arguments to be passed to pytest, e.g.
                          ['--pyargs', 'fuel_health.tests.sanity']

        :returns: Dict containing 'status', 'msg' and 'proc_name' fields
        """
        task_uuid = self.task['uuid']
        LOG.debug(_('Task %s: Running test: creating multiprocessing queue') %
                  task_uuid)

        test = multiprocessing.Process(target=_run_test,
                                       args=(test_args,
                                             self._cloud_config_path, self._q))
        test.start()
        test.join()
        result = self._q.get()
        if result['status'] and 'Timeout' in result['msg']:
            LOG.debug(_('Task %s: Test %s timed out.') %
                      (task_uuid, result['proc_name']))
        else:
            LOG.debug(_('Task %s: Process %s returned.') %
                      (task_uuid, result['proc_name']))
        self._cleanup()
        return result

    def _cleanup(self):
        cleanup = multiprocessing.Process(target=_run_cleanup,
                                          args=(self._cloud_config_path,))
        cleanup.start()
        cleanup.join()
        return
