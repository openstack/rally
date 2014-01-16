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

"""Tests for the Test engine."""

import mock

from keystoneclient import exceptions as keystone_exceptions

from rally.benchmark import engine
from rally import consts
from rally import exceptions
from tests import fakes
from tests import test


class TestEngineTestCase(test.TestCase):

    def setUp(self):
        super(TestEngineTestCase, self).setUp()

        self.valid_test_config_continuous_times = {
            'NovaServers.boot_and_delete_server': [
                {'args': {'flavor_id': 1, 'image_id': 'img'},
                 'execution': 'continuous',
                 'config': {'times': 10, 'active_users': 2,
                            'tenants': 3, 'users_per_tenant': 2}}
            ]
        }
        self.valid_test_config_continuous_duration = {
            'NovaServers.boot_and_delete_server': [
                {'args': {'flavor_id': 1, 'image_id': 'img'},
                 'execution': 'continuous',
                 'config': {'duration': 4, 'active_users': 2,
                            'tenants': 3, 'users_per_tenant': 2}}
            ]
        }
        self.invalid_test_config_bad_execution_type = {
            'NovaServers.boot_and_delete_server': [
                {'args': {'flavor_id': 1, 'image_id': 'img'},
                 'execution': 'contitnuous',
                 'config': {'times': 10, 'active_users': 2,
                            'tenants': 3, 'users_per_tenant': 2}}
            ]
        }
        self.invalid_test_config_bad_config_parameter = {
            'NovaServers.boot_and_delete_server': [
                {'args': {'flavor_id': 1, 'image_id': 'img'},
                 'execution': 'continuous',
                 'config': {'times': 10, 'activeusers': 2,
                            'tenants': 3, 'users_per_tenant': 2}}
            ]
        }
        self.invalid_test_config_parameters_conflict = {
            'NovaServers.boot_and_delete_server': [
                {'args': {'flavor_id': 1, 'image_id': 'img'},
                 'execution': 'continuous',
                 'config': {'times': 10, 'duration': 100,
                            'tenants': 3, 'users_per_tenant': 2}}
            ]
        }
        self.invalid_test_config_bad_param_for_periodic = {
            'NovaServers.boot_and_delete_server': [
                {'args': {'flavor_id': 1, 'image_id': 'img'},
                 'execution': 'periodic',
                 'config': {'times': 10, 'active_users': 3,
                            'tenants': 3, 'users_per_tenant': 2}}
            ]
        }
        self.valid_endpoint = {
            'auth_url': 'http://127.0.0.1:5000/v2.0',
            'username': 'admin',
            'password': 'admin',
            'tenant_name': 'admin',
        }

        self.run_success = {'msg': 'msg', 'status': 0, 'proc_name': 'proc'}

    def test_verify_test_config(self):
        try:
            engine.TestEngine(self.valid_test_config_continuous_times,
                              mock.MagicMock())
            engine.TestEngine(self.valid_test_config_continuous_duration,
                              mock.MagicMock())
        except Exception as e:
            self.fail("Unexpected exception in test config" +
                      "verification: %s" % str(e))
        self.assertRaises(exceptions.InvalidConfigException,
                          engine.TestEngine,
                          self.invalid_test_config_bad_execution_type,
                          mock.MagicMock())
        self.assertRaises(exceptions.InvalidConfigException,
                          engine.TestEngine,
                          self.invalid_test_config_bad_config_parameter,
                          mock.MagicMock())
        self.assertRaises(exceptions.InvalidConfigException,
                          engine.TestEngine,
                          self.invalid_test_config_parameters_conflict,
                          mock.MagicMock())
        self.assertRaises(exceptions.InvalidConfigException,
                          engine.TestEngine,
                          self.invalid_test_config_bad_param_for_periodic,
                          mock.MagicMock())

    @mock.patch("rally.benchmark.engine.osclients")
    def test_bind(self, mock_osclients):
        mock_osclients.Clients.return_value = fakes.FakeClients()
        tester = engine.TestEngine(self.valid_test_config_continuous_times,
                                   mock.MagicMock())
        with tester.bind(self.valid_endpoint):
            self.assertEqual(tester.endpoint, self.valid_endpoint)

    @mock.patch("rally.benchmark.engine.osclients")
    def test_bind_user_not_admin(self, mock_osclients):
        mock_osclients.Clients.return_value = fakes.FakeClients()
        mock_osclients.Clients.return_value.get_keystone_client(). \
            auth_ref['user']['roles'] = [{'name': 'notadmin'}]
        tester = engine.TestEngine(self.valid_test_config_continuous_times,
                                   mock.MagicMock())
        self.assertRaises(exceptions.InvalidAdminException,
                          tester.bind, self.valid_endpoint)

    @mock.patch("rally.cmd.main.api.engine.osclients.Clients"
                ".get_keystone_client")
    def test_bind_unauthorized_keystone(self, mock_osclients):
        mock_osclients.side_effect = keystone_exceptions.Unauthorized
        tester = engine.TestEngine(self.valid_test_config_continuous_times,
                                   mock.MagicMock())
        self.assertRaises(exceptions.InvalidEndpointsException,
                          tester.bind, self.valid_endpoint)

    @mock.patch("rally.cmd.main.api.engine.osclients.Clients"
                ".get_keystone_client")
    def test_bind_keystone_host_unreachable(self, mock_osclients):
        mock_osclients.side_effect = keystone_exceptions.AuthorizationFailure
        tester = engine.TestEngine(self.valid_test_config_continuous_times,
                                   mock.MagicMock())
        self.assertRaises(exceptions.HostUnreachableException,
                          tester.bind, self.valid_endpoint)

    @mock.patch("rally.benchmark.runner.ScenarioRunner.run")
    @mock.patch("rally.benchmark.utils.osclients")
    @mock.patch("rally.benchmark.engine.osclients")
    def test_run(self, mock_engine_osclients, mock_utils_osclients, mock_run):
        mock_engine_osclients.Clients.return_value = fakes.FakeClients()
        mock_utils_osclients.Clients.return_value = fakes.FakeClients()
        tester = engine.TestEngine(self.valid_test_config_continuous_times,
                                   mock.MagicMock())
        with tester.bind(self.valid_endpoint):
            tester.run()

    @mock.patch("rally.benchmark.runner.ScenarioRunner.run")
    @mock.patch("rally.benchmark.utils.osclients")
    @mock.patch("rally.benchmark.engine.osclients")
    def test_task_status_basic_chain(self, mock_engine_osclients,
                                     mock_utils_osclients, mock_scenario_run):
        fake_task = mock.MagicMock()
        tester = engine.TestEngine(self.valid_test_config_continuous_times,
                                   fake_task)
        mock_engine_osclients.Clients.return_value = fakes.FakeClients()
        mock_utils_osclients.Clients.return_value = fakes.FakeClients()
        mock_scenario_run.return_value = {}
        with tester.bind(self.valid_endpoint):
            tester.run()

        benchmark_name = 'NovaServers.boot_and_delete_server'
        benchmark_results = {
            'name': benchmark_name, 'pos': 0,
            'kw': self.valid_test_config_continuous_times[benchmark_name][0],
        }

        s = consts.TaskStatus
        expected = [
            mock.call.update_status(s.TEST_TOOL_BENCHMARKING),
            mock.call.append_results(benchmark_results, {'raw': {},
                                     'validation': {'is_valid': True}}),
            mock.call.update_status(s.FINISHED)
        ]
        # NOTE(msdubov): Ignore task['uuid'] calls which are used for logging
        mock_calls = filter(lambda call: '__getitem__' not in call[0],
                            fake_task.mock_calls)
        self.assertEqual(mock_calls, expected)

    @mock.patch("rally.benchmark.runner.ScenarioRunner.run")
    @mock.patch("rally.benchmark.utils.osclients")
    @mock.patch("rally.benchmark.engine.osclients")
    def test_task_status_basic_chain_validation_fails(self,
                                                      mock_engine_osclients,
                                                      mock_utils_osclients,
                                                      mock_scenario_run):
        fake_task = mock.MagicMock()
        tester = engine.TestEngine(self.valid_test_config_continuous_times,
                                   fake_task)
        mock_engine_osclients.Clients.return_value = fakes.FakeClients()
        mock_utils_osclients.Clients.return_value = fakes.FakeClients()
        validation_exc = exceptions.InvalidScenarioArgument()
        mock_scenario_run.side_effect = validation_exc

        with tester.bind(self.valid_endpoint):
            tester.run()

        benchmark_name = 'NovaServers.boot_and_delete_server'
        benchmark_results = {
            'name': benchmark_name, 'pos': 0,
            'kw': self.valid_test_config_continuous_times[benchmark_name][0],
        }

        s = consts.TaskStatus
        expected = [
            mock.call.update_status(s.TEST_TOOL_BENCHMARKING),
            mock.call.append_results(benchmark_results,
                                     {'raw': [],
                                      'validation': {'is_valid': False,
                                      'exc_msg': validation_exc.message}}),
            mock.call.update_status(s.FINISHED)
        ]
        # NOTE(msdubov): Ignore task['uuid'] calls which are used for logging
        mock_calls = filter(lambda call: '__getitem__' not in call[0],
                            fake_task.mock_calls)
        self.assertEqual(mock_calls, expected)

    @mock.patch("rally.benchmark.runner.ScenarioRunner.run")
    @mock.patch("rally.benchmark.utils.osclients")
    @mock.patch("rally.benchmark.engine.osclients")
    def test_task_status_failed(self, mock_engine_osclients,
                                mock_utils_osclients, mock_scenario_run):
        fake_task = mock.MagicMock()
        tester = engine.TestEngine(self.valid_test_config_continuous_times,
                                   fake_task)
        mock_engine_osclients.Clients.return_value = fakes.FakeClients()
        mock_utils_osclients.Clients.return_value = fakes.FakeClients()
        mock_scenario_run.side_effect = exceptions.TestException()
        try:
            with tester.bind(self.valid_endpoint):
                tester.run()
        except exceptions.TestException:
            pass

        s = consts.TaskStatus
        expected = [
            mock.call.update_status(s.TEST_TOOL_BENCHMARKING),
            mock.call.update_status(s.FAILED)
        ]
        # NOTE(msdubov): Ignore task['uuid'] calls which are used for logging
        mock_calls = filter(lambda call: '__getitem__' not in call[0],
                            fake_task.mock_calls)
        self.assertEqual(mock_calls, expected)
