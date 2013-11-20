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
import json
import mock
import os

from rally.benchmark import engine
from rally import consts
from rally import exceptions
from rally import test
from tests.benchmark.scenarios.nova import test_utils


class TestEngineTestCase(test.TestCase):

    def setUp(self):
        super(TestEngineTestCase, self).setUp()

        self.valid_test_config_continuous_times = {
            'verify': ['sanity', 'smoke'],
            'benchmark': {
                'NovaServers.boot_and_delete_server': [
                    {'args': {'flavor_id': 1, 'image_id': 'img'},
                     'execution': 'continuous',
                     'config': {'times': 10, 'active_users': 2,
                                'tenants': 3, 'users_per_tenant': 2}}
                ]
            }
        }
        self.valid_test_config_continuous_duration = {
            'verify': ['sanity', 'smoke'],
            'benchmark': {
                'NovaServers.boot_and_delete_server': [
                    {'args': {'flavor_id': 1, 'image_id': 'img'},
                     'execution': 'continuous',
                     'config': {'duration': 4, 'active_users': 2,
                                'tenants': 3, 'users_per_tenant': 2}}
                ]
            }
        }
        self.invalid_test_config_bad_test_name = {
            'verify': ['sanity', 'some_not_existing_test'],
            'benchmark': {}
        }
        self.invalid_test_config_bad_key = {
            'verify': ['sanity', 'smoke'],
            'benchmarck': {}
        }
        self.invalid_test_config_bad_execution_type = {
            'verify': ['sanity', 'smoke'],
            'benchmark': {
                'NovaServers.boot_and_delete_server': [
                    {'args': {'flavor_id': 1, 'image_id': 'img'},
                     'execution': 'contitnuous',
                     'config': {'times': 10, 'active_users': 2,
                                'tenants': 3, 'users_per_tenant': 2}}
                ]
            }
        }
        self.invalid_test_config_bad_config_parameter = {
            'verify': ['sanity', 'smoke'],
            'benchmark': {
                'NovaServers.boot_and_delete_server': [
                    {'args': {'flavor_id': 1, 'image_id': 'img'},
                     'execution': 'continuous',
                     'config': {'times': 10, 'activeusers': 2,
                                'tenants': 3, 'users_per_tenant': 2}}
                ]
            }
        }
        self.invalid_test_config_parameters_conflict = {
            'verify': ['sanity', 'smoke'],
            'benchmark': {
                'NovaServers.boot_and_delete_server': [
                    {'args': {'flavor_id': 1, 'image_id': 'img'},
                     'execution': 'continuous',
                     'config': {'times': 10, 'duration': 100,
                                'tenants': 3, 'users_per_tenant': 2}}
                ]
            }
        }
        self.valid_cloud_config = {
            'identity': {
                'admin_name': 'admin',
                'admin_password': 'admin'
            },
            'compute': {
                'controller_nodes': 'localhost'
            }
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
        self.assertRaises(exceptions.NoSuchVerificationTest,
                          engine.TestEngine,
                          self.invalid_test_config_bad_test_name,
                          mock.MagicMock())
        self.assertRaises(exceptions.InvalidConfigException,
                          engine.TestEngine,
                          self.invalid_test_config_bad_key,
                          mock.MagicMock())
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

    def test_bind(self):
        tester = engine.TestEngine(self.valid_test_config_continuous_times,
                                   mock.MagicMock())
        with tester.bind(self.valid_cloud_config):
            self.assertTrue(os.path.exists(tester.cloud_config_path))
        self.assertFalse(os.path.exists(tester.cloud_config_path))

    @mock.patch('rally.benchmark.utils.Verifier.run')
    def test_verify(self, mock_run):
        tester = engine.TestEngine(self.valid_test_config_continuous_times,
                                   mock.MagicMock())
        mock_run.return_value = self.run_success
        with tester.bind(self.valid_cloud_config):
            try:
                tester.verify()
            except Exception as e:
                self.fail("Exception in TestEngine.verify: %s" % str(e))

    @mock.patch("rally.benchmark.utils.ScenarioRunner.run")
    @mock.patch("rally.benchmark.utils.osclients")
    def test_benchmark(self, mock_osclients, mock_run):
        mock_osclients.Clients.return_value = test_utils.FakeClients()
        tester = engine.TestEngine(self.valid_test_config_continuous_times,
                                   mock.MagicMock())
        with tester.bind(self.valid_cloud_config):
            tester.benchmark()

    @mock.patch("rally.benchmark.utils.ScenarioRunner.run")
    @mock.patch("rally.benchmark.utils.Verifier.run")
    @mock.patch("rally.benchmark.utils.osclients")
    def test_task_status_basic_chain(self, mock_osclients, mock_run,
                                     mock_scenario_run):
        fake_task = mock.MagicMock()
        tester = engine.TestEngine(self.valid_test_config_continuous_times,
                                   fake_task)
        mock_osclients.Clients.return_value = test_utils.FakeClients()
        mock_run.return_value = self.run_success
        mock_scenario_run.return_value = {}
        with tester.bind(self.valid_cloud_config):
            tester.verify()
            tester.benchmark()

        benchmark_name = 'NovaServers.boot_and_delete_server'
        benchmark_results = {
            'name': benchmark_name, 'pos': 0,
            'kw': self.valid_test_config_continuous_times['benchmark']
                                                         [benchmark_name][0],
        }

        s = consts.TaskStatus
        expected = [
            mock.call.update_status(s.TEST_TOOL_VERIFY_OPENSTACK),
            mock.call.update_verification_log(json.dumps(
                [self.run_success, self.run_success])),
            mock.call.update_status(s.TEST_TOOL_BENCHMARKING),
            mock.call.append_results(benchmark_results, {'raw': {}}),
            mock.call.update_status(s.FINISHED)
        ]
        # NOTE(msdubov): Ignore task['uuid'] calls which are used for logging
        mock_calls = filter(lambda call: '__getitem__' not in call[0],
                            fake_task.mock_calls)
        self.assertEqual(mock_calls, expected)

    @mock.patch("rally.benchmark.utils.ScenarioRunner.run")
    @mock.patch("rally.benchmark.utils.Verifier.run")
    @mock.patch("rally.benchmark.utils.osclients")
    def test_task_status_failed(self, mock_osclients, mock_run,
                                mock_scenario_run):
        fake_task = mock.MagicMock()
        tester = engine.TestEngine(self.valid_test_config_continuous_times,
                                   fake_task)
        mock_osclients.Clients.return_value = test_utils.FakeClients()
        mock_run.return_value = self.run_success
        mock_scenario_run.side_effect = exceptions.TestException()
        try:
            with tester.bind(self.valid_cloud_config):
                tester.verify()
                tester.benchmark()
        except exceptions.TestException:
            pass

        s = consts.TaskStatus
        expected = [
            mock.call.update_status(s.TEST_TOOL_VERIFY_OPENSTACK),
            mock.call.update_verification_log(json.dumps(
                [self.run_success, self.run_success])),
            mock.call.update_status(s.TEST_TOOL_BENCHMARKING),
            mock.call.update_status(s.FAILED)
        ]
        # NOTE(msdubov): Ignore task['uuid'] calls which are used for logging
        mock_calls = filter(lambda call: '__getitem__' not in call[0],
                            fake_task.mock_calls)
        self.assertEqual(mock_calls, expected)

    def test_task_status_invalid_config(self):
        fake_task = mock.MagicMock()
        try:
            engine.TestEngine(self.invalid_test_config_bad_key, fake_task)
        except exceptions.InvalidConfigException:
            pass
        expected = []
        # NOTE(msdubov): Ignore task['uuid'] calls which are used for logging
        mock_calls = filter(lambda call: '__getitem__' not in call[0],
                            fake_task.mock_calls)
        self.assertEqual(mock_calls, expected)
