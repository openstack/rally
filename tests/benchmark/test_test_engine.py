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


class TestEngineTestCase(test.NoDBTestCase):

    def setUp(self):
        super(TestEngineTestCase, self).setUp()

        self.valid_test_config = {
            'verify': ['sanity', 'smoke'],
            'benchmark': {}
        }
        self.invalid_test_config_bad_test_name = {
            'verify': ['sanity', 'some_not_existing_test'],
            'benchmark': {}
        }
        self.invalid_test_config_bad_key = {
            'verify': ['sanity', 'smoke'],
            'benchmarck': {}
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
            engine.TestEngine(self.valid_test_config, mock.MagicMock())
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

    def test_bind(self):
        test_engine = engine.TestEngine(self.valid_test_config,
                                        mock.MagicMock())
        with test_engine.bind(self.valid_cloud_config):
            self.assertTrue(os.path.exists(test_engine.cloud_config_path))
        self.assertFalse(os.path.exists(test_engine.cloud_config_path))

    def test_verify(self):
        test_engine = engine.TestEngine(self.valid_test_config,
                                        mock.MagicMock())
        with mock.patch('rally.benchmark.utils.Verifier.run') as mock_run:
            mock_run.return_value = self.run_success
            with test_engine.bind(self.valid_cloud_config):
                try:
                    test_engine.verify()
                except Exception as e:
                    self.fail("Exception in TestEngine.verify: %s" % str(e))

    def test_benchmark(self):
        test_engine = engine.TestEngine(self.valid_test_config,
                                        mock.MagicMock())
        with test_engine.bind(self.valid_cloud_config):
            test_engine.benchmark()

    def test_task_status_basic_chain(self):
        fake_task = mock.MagicMock()
        test_engine = engine.TestEngine(self.valid_test_config, fake_task)
        with mock.patch('rally.benchmark.utils.Verifier.run') as mock_run:
            mock_run.return_value = self.run_success
            with test_engine.bind(self.valid_cloud_config):
                test_engine.verify()
                test_engine.benchmark()

        s = consts.TaskStatus
        expected = [
            mock.call.update_status(s.TEST_TOOL_VERIFY_OPENSTACK),
            mock.call.update_verification_log(json.dumps(
                [self.run_success, self.run_success])),
            mock.call.update_status(s.TEST_TOOL_BENCHMARKING)
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
