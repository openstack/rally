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
from oslotest import mockpatch

from rally.benchmark.scenarios.heat import utils
from rally import exceptions
from tests.unit import test

BM_UTILS = 'rally.benchmark.utils'
HEAT_UTILS = 'rally.benchmark.scenarios.heat.utils'


class HeatScenarioTestCase(test.TestCase):

    def setUp(self):
        super(HeatScenarioTestCase, self).setUp()
        self.stack = mock.Mock()
        self.res_is = mockpatch.Patch(HEAT_UTILS + ".heat_resource_is")
        self.get_fm = mockpatch.Patch(BM_UTILS + '.get_from_manager')
        self.wait_for = mockpatch.Patch(HEAT_UTILS + ".bench_utils.wait_for")
        self.wait_for_delete = mockpatch.Patch(
            HEAT_UTILS + ".bench_utils.wait_for_delete")
        self.useFixture(self.wait_for)
        self.useFixture(self.wait_for_delete)
        self.useFixture(self.res_is)
        self.useFixture(self.get_fm)
        self.gfm = self.get_fm.mock
        self.useFixture(mockpatch.Patch('time.sleep'))
        self.scenario = utils.HeatScenario()

    def _test_atomic_action_timer(self, atomic_actions, name):
        action_duration = atomic_actions.get(name)
        self.assertIsNotNone(action_duration)
        self.assertIsInstance(action_duration, float)

    @mock.patch(HEAT_UTILS + '.HeatScenario.clients')
    def test_list_stacks(self, mock_clients):
        stacks_list = []
        mock_clients("heat").stacks.list.return_value = stacks_list
        scenario = utils.HeatScenario()
        return_stacks_list = scenario._list_stacks()
        self.assertEqual(stacks_list, return_stacks_list)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       'heat.list_stacks')

    @mock.patch(HEAT_UTILS + '.HeatScenario.clients')
    def test_create_stack(self, mock_clients):
        mock_clients("heat").stacks.create.return_value = {
            'stack': {'id': 'test_id'}
        }
        mock_clients("heat").stacks.get.return_value = self.stack
        scenario = utils.HeatScenario()
        return_stack = scenario._create_stack('stack_name')
        self.wait_for.mock.assert_called_once_with(self.stack,
                                                   update_resource=self.gfm(),
                                                   is_ready=self.res_is.mock(),
                                                   check_interval=1,
                                                   timeout=3600)
        self.res_is.mock.assert_has_calls(mock.call('CREATE_COMPLETE'))
        self.assertEqual(self.wait_for.mock(), return_stack)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       'heat.create_stack')

    def test_delete_stack(self):
        scenario = utils.HeatScenario()
        scenario._delete_stack(self.stack)
        self.stack.delete.assert_called_once_with()
        self.wait_for_delete.mock.assert_called_once_with(
            self.stack,
            update_resource=self.gfm(),
            check_interval=1,
            timeout=3600)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       'heat.delete_stack')

    def test_heat_resource_is(self):
        stack = {'stack_status': 'CREATE_COMPLETED'}
        status_fn = utils.heat_resource_is('CREATE_COMPLETED')
        status_fn(stack)


class HeatScenarioNegativeTestCase(test.TestCase):

    @mock.patch(HEAT_UTILS + '.HeatScenario.clients')
    @mock.patch(HEAT_UTILS + '.CONF.benchmark')
    def test_failed_create_stack(self, mock_bench, mock_clients):
        mock_bench.heat_stack_create_prepoll_delay = 2
        mock_bench.heat_stack_create_timeout = 1
        mock_bench.benchmark.heat_stack_create_poll_interval = 1

        mock_clients("heat").stacks.create.return_value = {
            'stack': {'id': 'test_id'}
        }
        stack = mock.Mock()
        resource = mock.Mock()
        resource.stack_status = "CREATE_FAILED"
        stack.manager.get.return_value = resource
        mock_clients("heat").stacks.get.return_value = stack
        scenario = utils.HeatScenario()
        try:
            ex = self.assertRaises(exceptions.GetResourceErrorStatus,
                                   scenario._create_stack, 'stack_name')
            self.assertIn('has CREATE_FAILED status', str(ex))
        except exceptions.TimeoutException:
            raise self.fail('Unrecognized error status')
