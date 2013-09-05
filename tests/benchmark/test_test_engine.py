# vim: tabstop=4 shiftwidth=4 softtabstop=4

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
import os

from rally.benchmark import engine
from rally import exceptions
from rally import test


class TestEngineTestCase(test.NoDBTestCase):

    def setUp(self):
        super(TestEngineTestCase, self).setUp()
        self.valid_test_config = {
            'verify': ['sanity', 'smoke'],
            'benchmark': []
        }
        self.invalid_test_config = {
            'verify': ['sanity', 'some_not_existing_test'],
            'benchmark': []
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
        run_success = {
            'proc': {'msg': 'msg', 'status': 0, 'proc_name': 'proc'}
        }
        self.run_mock = mock.patch('rally.benchmark.utils.Tester.run',
                                   mock.Mock(return_value=run_success))
        self.run_mock.start()

    def tearDown(self):
        self.run_mock.stop()
        super(TestEngineTestCase, self).tearDown()

    def test_verify_test_config(self):
        try:
            engine.TestEngine(self.valid_test_config)
        except Exception as e:
            self.fail("Unexpected exception in test config" +
                      "verification: %s" % str(e))
        self.assertRaises(exceptions.NoSuchTestException,
                          engine.TestEngine, self.invalid_test_config)

    def test_bind(self):
        test_engine = engine.TestEngine(self.valid_test_config)
        with test_engine.bind(self.valid_cloud_config):
            self.assertTrue(os.path.exists(test_engine.cloud_config_path))
        self.assertFalse(os.path.exists(test_engine.cloud_config_path))

    def test_verify(self):
        test_engine = engine.TestEngine(self.valid_test_config)
        with test_engine.bind(self.valid_cloud_config):
            self.assertTrue(test_engine.verify())
