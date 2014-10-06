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

import tempfile

import mock

from rally.benchmark.scenarios.heat import stacks
from tests.unit import test

HEAT_STACKS = "rally.benchmark.scenarios.heat.stacks.HeatStacks"


class HeatStacksTestCase(test.TestCase):

    @mock.patch(HEAT_STACKS + "._generate_random_name")
    @mock.patch(HEAT_STACKS + "._list_stacks")
    @mock.patch(HEAT_STACKS + "._create_stack")
    def test_create_and_list_stack(self, mock_create, mock_list,
                                   mock_random_name):
        template_file = tempfile.NamedTemporaryFile()
        heat_scenario = stacks.HeatStacks()
        mock_random_name.return_value = "test-rally-stack"
        heat_scenario.create_and_list_stack(template_path=template_file.name)
        self.assertEqual(1, mock_create.called)
        mock_list.assert_called_once_with()

    @mock.patch(HEAT_STACKS + "._generate_random_name")
    @mock.patch(HEAT_STACKS + "._list_stacks")
    @mock.patch(HEAT_STACKS + "._create_stack")
    def test_create_and_list_stack_fails(self, mock_create, mock_list,
                                         mock_random_name):
        heat_scenario = stacks.HeatStacks()
        mock_random_name.return_value = "test-rally-stack"
        self.assertRaises(IOError,
                          heat_scenario.create_and_list_stack,
                          template_path="/tmp/dummy")

    @mock.patch(HEAT_STACKS + "._generate_random_name")
    @mock.patch(HEAT_STACKS + "._delete_stack")
    @mock.patch(HEAT_STACKS + "._create_stack")
    def test_create_and_delete_stack(self, mock_create, mock_delete,
                                     mock_random_name):
        heat_scenario = stacks.HeatStacks()
        fake_stack = object()
        mock_create.return_value = fake_stack
        mock_random_name.return_value = "test-rally-stack"
        heat_scenario.create_and_delete_stack()

        self.assertEqual(1, mock_create.called)
        mock_delete.assert_called_once_with(fake_stack)
