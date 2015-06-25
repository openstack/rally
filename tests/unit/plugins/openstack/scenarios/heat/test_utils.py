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

from rally import exceptions
from rally.plugins.openstack.scenarios.heat import utils
from tests.unit import test

BM_UTILS = "rally.task.utils"
HEAT_UTILS = "rally.plugins.openstack.scenarios.heat.utils"

CONF = utils.CONF


class HeatScenarioTestCase(test.ClientsTestCase):
    def setUp(self):
        super(HeatScenarioTestCase, self).setUp()
        self.stack = mock.Mock()
        self.res_is = mockpatch.Patch(BM_UTILS + ".resource_is")
        self.get_fm = mockpatch.Patch(BM_UTILS + ".get_from_manager")
        self.wait_for = mockpatch.Patch(HEAT_UTILS + ".utils.wait_for")
        self.wait_for_delete = mockpatch.Patch(
            HEAT_UTILS + ".utils.wait_for_delete")
        self.useFixture(self.wait_for)
        self.useFixture(self.wait_for_delete)
        self.useFixture(self.res_is)
        self.useFixture(self.get_fm)
        self.gfm = self.get_fm.mock
        self.useFixture(mockpatch.Patch("time.sleep"))
        self.scenario = utils.HeatScenario()
        self.default_template = "heat_template_version: 2013-05-23"
        self.dummy_parameters = {"dummy_param": "dummy_key"}
        self.dummy_files = ["dummy_file.yaml"]
        self.dummy_environment = {"dummy_env": "dummy_env_value"}

    def test_list_stacks(self):
        scenario = utils.HeatScenario()
        return_stacks_list = scenario._list_stacks()
        self.clients("heat").stacks.list.assert_called_once_with()
        self.assertEqual(list(self.clients("heat").stacks.list.return_value),
                         return_stacks_list)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "heat.list_stacks")

    def test_create_stack(self):
        self.clients("heat").stacks.create.return_value = {
            "stack": {"id": "test_id"}
        }
        self.clients("heat").stacks.get.return_value = self.stack
        scenario = utils.HeatScenario()
        return_stack = scenario._create_stack(self.default_template,
                                              self.dummy_parameters,
                                              self.dummy_files,
                                              self.dummy_environment)
        args, kwargs = self.clients("heat").stacks.create.call_args
        self.assertIn(self.dummy_parameters, kwargs.values())
        self.assertIn(self.default_template, kwargs.values())
        self.assertIn(self.dummy_files, kwargs.values())
        self.assertIn(self.dummy_environment, kwargs.values())
        self.wait_for.mock.assert_called_once_with(
            self.stack,
            update_resource=self.gfm(),
            is_ready=self.res_is.mock(),
            check_interval=CONF.benchmark.heat_stack_create_poll_interval,
            timeout=CONF.benchmark.heat_stack_create_timeout)
        self.res_is.mock.assert_has_calls([mock.call("CREATE_COMPLETE")])
        self.assertEqual(self.wait_for.mock(), return_stack)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "heat.create_stack")

    def test_update_stack(self):
        self.clients("heat").stacks.update.return_value = None
        scenario = utils.HeatScenario()
        scenario._update_stack(self.stack, self.default_template,
                               self.dummy_parameters, self.dummy_files,
                               self.dummy_environment)
        args, kwargs = self.clients("heat").stacks.update.call_args
        self.assertIn(self.dummy_parameters, kwargs.values())
        self.assertIn(self.default_template, kwargs.values())
        self.assertIn(self.dummy_files, kwargs.values())
        self.assertIn(self.dummy_environment, kwargs.values())
        self.assertIn(self.stack.id, args)
        self.wait_for.mock.assert_called_once_with(
            self.stack,
            update_resource=self.gfm(),
            is_ready=self.res_is.mock(),
            check_interval=CONF.benchmark.heat_stack_update_poll_interval,
            timeout=CONF.benchmark.heat_stack_update_timeout)
        self.res_is.mock.assert_has_calls([mock.call("UPDATE_COMPLETE")])
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "heat.update_stack")

    def test_check_stack(self):
        scenario = utils.HeatScenario()
        scenario._check_stack(self.stack)
        self.clients("heat").actions.check.assert_called_once_with(
            self.stack.id)
        self.wait_for.mock.assert_called_once_with(
            self.stack,
            update_resource=self.gfm(),
            is_ready=self.res_is.mock(),
            check_interval=CONF.benchmark.heat_stack_check_poll_interval,
            timeout=CONF.benchmark.heat_stack_check_timeout)
        self.res_is.mock.assert_has_calls([mock.call("CHECK_COMPLETE")])
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "heat.check_stack")

    def test_delete_stack(self):
        scenario = utils.HeatScenario()
        scenario._delete_stack(self.stack)
        self.stack.delete.assert_called_once_with()
        self.wait_for_delete.mock.assert_called_once_with(
            self.stack,
            update_resource=self.gfm(),
            check_interval=CONF.benchmark.heat_stack_delete_poll_interval,
            timeout=CONF.benchmark.heat_stack_delete_timeout)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "heat.delete_stack")

    def test_suspend_stack(self):
        scenario = utils.HeatScenario()
        scenario._suspend_stack(self.stack)
        self.clients("heat").actions.suspend.assert_called_once_with(
            self.stack.id)
        self.wait_for.mock.assert_called_once_with(
            self.stack,
            update_resource=self.gfm(),
            is_ready=self.res_is.mock(),
            check_interval=CONF.benchmark.heat_stack_suspend_poll_interval,
            timeout=CONF.benchmark.heat_stack_suspend_timeout)
        self.res_is.mock.assert_has_calls([mock.call("SUSPEND_COMPLETE")])
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "heat.suspend_stack")

    def test_resume_stack(self):
        scenario = utils.HeatScenario()
        scenario._resume_stack(self.stack)
        self.clients("heat").actions.resume.assert_called_once_with(
            self.stack.id)
        self.wait_for.mock.assert_called_once_with(
            self.stack,
            update_resource=self.gfm(),
            is_ready=self.res_is.mock(),
            check_interval=CONF.benchmark.heat_stack_resume_poll_interval,
            timeout=CONF.benchmark.heat_stack_resume_timeout)
        self.res_is.mock.assert_has_calls([mock.call("RESUME_COMPLETE")])
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "heat.resume_stack")

    def test_snapshot_stack(self):
        scenario = utils.HeatScenario()
        scenario._snapshot_stack(self.stack)
        self.clients("heat").stacks.snapshot.assert_called_once_with(
            self.stack.id)
        self.wait_for.mock.assert_called_once_with(
            self.stack,
            update_resource=self.gfm(),
            is_ready=self.res_is.mock(),
            check_interval=CONF.benchmark.heat_stack_snapshot_poll_interval,
            timeout=CONF.benchmark.heat_stack_snapshot_timeout)
        self.res_is.mock.assert_has_calls([mock.call("SNAPSHOT_COMPLETE")])
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "heat.snapshot_stack")

    def test_restore_stack(self):
        scenario = utils.HeatScenario()
        scenario._restore_stack(self.stack, "dummy_id")
        self.clients("heat").stacks.restore.assert_called_once_with(
            self.stack.id, "dummy_id")
        self.wait_for.mock.assert_called_once_with(
            self.stack,
            update_resource=self.gfm(),
            is_ready=self.res_is.mock(),
            check_interval=CONF.benchmark.heat_stack_restore_poll_interval,
            timeout=CONF.benchmark.heat_stack_restore_timeout)
        self.res_is.mock.assert_has_calls([mock.call("RESTORE_COMPLETE")])
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "heat.restore_stack")


class HeatScenarioNegativeTestCase(test.ClientsTestCase):
    def test_failed_create_stack(self):
        self.clients("heat").stacks.create.return_value = {
            "stack": {"id": "test_id"}
        }
        stack = mock.Mock()
        resource = mock.Mock()
        resource.stack_status = "CREATE_FAILED"
        stack.manager.get.return_value = resource
        self.clients("heat").stacks.get.return_value = stack
        scenario = utils.HeatScenario()
        try:
            ex = self.assertRaises(exceptions.GetResourceErrorStatus,
                                   scenario._create_stack, "stack_name")
            self.assertIn("has CREATE_FAILED status", str(ex))
        except exceptions.TimeoutException:
            raise self.fail("Unrecognized error status")

    def test_failed_update_stack(self):
        stack = mock.Mock()
        resource = mock.Mock()
        resource.stack_status = "UPDATE_FAILED"
        stack.manager.get.return_value = resource
        self.clients("heat").stacks.get.return_value = stack
        scenario = utils.HeatScenario()
        try:
            ex = self.assertRaises(exceptions.GetResourceErrorStatus,
                                   scenario._update_stack, stack,
                                   "heat_template_version: 2013-05-23")
            self.assertIn("has UPDATE_FAILED status", str(ex))
        except exceptions.TimeoutException:
            raise self.fail("Unrecognized error status")
