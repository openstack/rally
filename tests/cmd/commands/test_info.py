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

import mock

from rally.benchmark.scenarios.dummy import dummy
from rally.cmd.commands import info
from tests import test


class InfoCommandsTestCase(test.TestCase):
    def setUp(self):
        super(InfoCommandsTestCase, self).setUp()
        self.info = info.InfoCommands()

    @mock.patch("rally.searchutils.find_benchmark_scenario_group")
    def test_find_dummy_scenario_group(self, mock_find):
        query = "Dummy"
        mock_find.return_value = dummy.Dummy
        status = self.info.find(query)
        mock_find.assert_called_once_with(query)
        self.assertEqual(None, status)

    @mock.patch("rally.searchutils.find_benchmark_scenario")
    def test_find_dummy_scenario(self, mock_find):
        query = "Dummy.dummy"
        mock_find.return_value = dummy.Dummy.dummy
        status = self.info.find(query)
        mock_find.assert_called_once_with(query)
        self.assertEqual(None, status)

    @mock.patch("rally.searchutils.find_benchmark_scenario")
    def test_find_failure_status(self, mock_find):
        query = "Dummy.non_existing"
        mock_find.return_value = None
        status = self.info.find(query)
        mock_find.assert_called_once_with(query)
        self.assertEqual(1, status)
