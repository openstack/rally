# Copyright 2014: Mirantis Inc.
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

import mock

from rally.plugins.openstack.scenarios.tempest import tempest
from rally.plugins.openstack.scenarios.tempest import utils
from tests.unit import test

TS = "rally.plugins.openstack.scenarios.tempest"


class TempestLogWrappersTestCase(test.TestCase):

    def setUp(self):
        super(TempestLogWrappersTestCase, self).setUp()
        verifier = mock.MagicMock()
        verifier.parse_results.return_value = mock.MagicMock(
            total={"time": 0}, tests={})

        context = test.get_test_context()
        context.update({"tmp_results_dir": "/tmp/dir", "verifier": verifier})
        self.scenario = tempest.SingleTest(context)
        self.scenario._add_atomic_actions = mock.MagicMock()

    @mock.patch(TS + ".utils.tempfile")
    def test_launch_without_specified_log_file(self, mock_tempfile):
        mock_tempfile.NamedTemporaryFile().name = "tmp_file"
        target_func = mock.MagicMock()
        target_func.__name__ = "target_func"
        func = utils.tempest_log_wrapper(target_func)

        func(self.scenario)

        target_func.assert_called_once_with(self.scenario,
                                            log_file="/tmp/dir/tmp_file")

    @mock.patch(TS + ".utils.tempfile")
    def test_launch_with_specified_log_file(self, mock_tempfile):
        target_func = mock.MagicMock()
        target_func.__name__ = "target_func"
        func = utils.tempest_log_wrapper(target_func)

        func(self.scenario, log_file="log_file")

        target_func.assert_called_once_with(self.scenario,
                                            log_file="log_file")
        self.assertEqual(0, mock_tempfile.NamedTemporaryFile.call_count)

    def test_func_time_result_is_string(self):
        verifier = mock.MagicMock()
        verifier.parse_results.return_value = mock.MagicMock(
            total={"time": "0.1"}, tests={})
        context = test.get_test_context()
        context.update({"tmp_results_dir": "/tmp/dir", "verifier": verifier})
        scenario = tempest.SingleTest(context)

        target_func = mock.MagicMock()
        target_func.__name__ = "target_func"
        func = utils.tempest_log_wrapper(target_func)

        func(scenario)
        self.assertEqual(0.1, scenario._atomic_actions["test_execution"])
