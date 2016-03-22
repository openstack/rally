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

from rally import exceptions
from rally.plugins.openstack.scenarios.heat import utils
from tests.unit import test

HEAT_UTILS = "rally.plugins.openstack.scenarios.heat.utils"

CONF = utils.CONF


class HeatScenarioTestCase(test.ScenarioTestCase):
    def setUp(self):
        super(HeatScenarioTestCase, self).setUp()
        self.stack = mock.Mock()
        self.scenario = utils.HeatScenario(self.context)
        self.default_template = "heat_template_version: 2013-05-23"
        self.dummy_parameters = {"dummy_param": "dummy_key"}
        self.dummy_files = ["dummy_file.yaml"]
        self.dummy_environment = {"dummy_env": "dummy_env_value"}
        self.default_output_key = "dummy_output_key"

    def test_list_stacks(self):
        scenario = utils.HeatScenario(self.context)
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
        return_stack = self.scenario._create_stack(self.default_template,
                                                   self.dummy_parameters,
                                                   self.dummy_files,
                                                   self.dummy_environment)
        args, kwargs = self.clients("heat").stacks.create.call_args
        self.assertIn(self.dummy_parameters, kwargs.values())
        self.assertIn(self.default_template, kwargs.values())
        self.assertIn(self.dummy_files, kwargs.values())
        self.assertIn(self.dummy_environment, kwargs.values())
        self.mock_wait_for.mock.assert_called_once_with(
            self.stack,
            update_resource=self.mock_get_from_manager.mock.return_value,
            ready_statuses=["CREATE_COMPLETE"],
            failure_statuses=["CREATE_FAILED"],
            check_interval=CONF.benchmark.heat_stack_create_poll_interval,
            timeout=CONF.benchmark.heat_stack_create_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self.assertEqual(self.mock_wait_for.mock.return_value, return_stack)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "heat.create_stack")

    def test_update_stack(self):
        self.clients("heat").stacks.update.return_value = None
        scenario = utils.HeatScenario(self.context)
        scenario._update_stack(self.stack, self.default_template,
                               self.dummy_parameters, self.dummy_files,
                               self.dummy_environment)
        args, kwargs = self.clients("heat").stacks.update.call_args
        self.assertIn(self.dummy_parameters, kwargs.values())
        self.assertIn(self.default_template, kwargs.values())
        self.assertIn(self.dummy_files, kwargs.values())
        self.assertIn(self.dummy_environment, kwargs.values())
        self.assertIn(self.stack.id, args)
        self.mock_wait_for.mock.assert_called_once_with(
            self.stack,
            update_resource=self.mock_get_from_manager.mock.return_value,
            ready_statuses=["UPDATE_COMPLETE"],
            failure_statuses=["UPDATE_FAILED"],
            check_interval=CONF.benchmark.heat_stack_update_poll_interval,
            timeout=CONF.benchmark.heat_stack_update_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "heat.update_stack")

    def test_check_stack(self):
        scenario = utils.HeatScenario(self.context)
        scenario._check_stack(self.stack)
        self.clients("heat").actions.check.assert_called_once_with(
            self.stack.id)
        self.mock_wait_for.mock.assert_called_once_with(
            self.stack,
            update_resource=self.mock_get_from_manager.mock.return_value,
            ready_statuses=["CHECK_COMPLETE"],
            failure_statuses=["CHECK_FAILED"],
            check_interval=CONF.benchmark.heat_stack_check_poll_interval,
            timeout=CONF.benchmark.heat_stack_check_timeout)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "heat.check_stack")

    def test_delete_stack(self):
        scenario = utils.HeatScenario(self.context)
        scenario._delete_stack(self.stack)
        self.stack.delete.assert_called_once_with()
        self.mock_wait_for_status.mock.assert_called_once_with(
            self.stack,
            ready_statuses=["DELETE_COMPLETE"],
            failure_statuses=["DELETE_FAILED"],
            check_deletion=True,
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.heat_stack_delete_poll_interval,
            timeout=CONF.benchmark.heat_stack_delete_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "heat.delete_stack")

    def test_suspend_stack(self):
        scenario = utils.HeatScenario(self.context)
        scenario._suspend_stack(self.stack)
        self.clients("heat").actions.suspend.assert_called_once_with(
            self.stack.id)
        self.mock_wait_for.mock.assert_called_once_with(
            self.stack,
            update_resource=self.mock_get_from_manager.mock.return_value,
            ready_statuses=["SUSPEND_COMPLETE"],
            failure_statuses=["SUSPEND_FAILED"],
            check_interval=CONF.benchmark.heat_stack_suspend_poll_interval,
            timeout=CONF.benchmark.heat_stack_suspend_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "heat.suspend_stack")

    def test_resume_stack(self):
        scenario = utils.HeatScenario(self.context)
        scenario._resume_stack(self.stack)
        self.clients("heat").actions.resume.assert_called_once_with(
            self.stack.id)
        self.mock_wait_for.mock.assert_called_once_with(
            self.stack,
            update_resource=self.mock_get_from_manager.mock.return_value,
            ready_statuses=["RESUME_COMPLETE"],
            failure_statuses=["RESUME_FAILED"],
            check_interval=CONF.benchmark.heat_stack_resume_poll_interval,
            timeout=CONF.benchmark.heat_stack_resume_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "heat.resume_stack")

    def test_snapshot_stack(self):
        scenario = utils.HeatScenario(self.context)
        scenario._snapshot_stack(self.stack)
        self.clients("heat").stacks.snapshot.assert_called_once_with(
            self.stack.id)
        self.mock_wait_for.mock.assert_called_once_with(
            self.stack,
            update_resource=self.mock_get_from_manager.mock.return_value,
            ready_statuses=["SNAPSHOT_COMPLETE"],
            failure_statuses=["SNAPSHOT_FAILED"],
            check_interval=CONF.benchmark.heat_stack_snapshot_poll_interval,
            timeout=CONF.benchmark.heat_stack_snapshot_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "heat.snapshot_stack")

    def test_restore_stack(self):
        scenario = utils.HeatScenario(self.context)
        scenario._restore_stack(self.stack, "dummy_id")
        self.clients("heat").stacks.restore.assert_called_once_with(
            self.stack.id, "dummy_id")
        self.mock_wait_for.mock.assert_called_once_with(
            self.stack,
            update_resource=self.mock_get_from_manager.mock.return_value,
            ready_statuses=["RESTORE_COMPLETE"],
            failure_statuses=["RESTORE_FAILED"],
            check_interval=CONF.benchmark.heat_stack_restore_poll_interval,
            timeout=CONF.benchmark.heat_stack_restore_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "heat.restore_stack")

    def test__count_instances(self):
        self.clients("heat").resources.list.return_value = [
            mock.Mock(resource_type="OS::Nova::Server"),
            mock.Mock(resource_type="OS::Nova::Server"),
            mock.Mock(resource_type="OS::Heat::AutoScalingGroup")]
        scenario = utils.HeatScenario(self.context)
        self.assertEqual(scenario._count_instances(self.stack), 2)
        self.clients("heat").resources.list.assert_called_once_with(
            self.stack.id,
            nested_depth=1)

    def test__scale_stack(self):
        scenario = utils.HeatScenario(self.context)
        scenario._count_instances = mock.Mock(side_effect=[3, 3, 2])
        scenario._stack_webhook = mock.Mock()

        scenario._scale_stack(self.stack, "test_output_key", -1)

        scenario._stack_webhook.assert_called_once_with(self.stack,
                                                        "test_output_key")
        self.mock_wait_for.mock.assert_called_once_with(
            self.stack,
            is_ready=mock.ANY,
            failure_statuses=["UPDATE_FAILED"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            timeout=CONF.benchmark.heat_stack_scale_timeout,
            check_interval=CONF.benchmark.heat_stack_scale_poll_interval)
        self.mock_get_from_manager.mock.assert_called_once_with()

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "heat.scale_with_test_output_key")

    @mock.patch("requests.post")
    def test_stack_webhook(self, mock_post):
        scenario = utils.HeatScenario(self.context)
        stack = mock.Mock(outputs=[
            {"output_key": "output1", "output_value": "url1"},
            {"output_key": "output2", "output_value": "url2"}])

        scenario._stack_webhook(stack, "output1")
        mock_post.assert_called_with("url1")
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "heat.output1_webhook")

    @mock.patch("requests.post")
    def test_stack_webhook_invalid_output_key(self, mock_post):
        scenario = utils.HeatScenario(self.context)
        stack = mock.Mock()
        stack.outputs = [{"output_key": "output1", "output_value": "url1"},
                         {"output_key": "output2", "output_value": "url2"}]

        self.assertRaises(exceptions.InvalidConfigException,
                          scenario._stack_webhook, stack, "bogus")

    def test_stack_show_output(self):
        scenario = utils.HeatScenario(self.context)
        scenario._stack_show_output(self.stack, self.default_output_key)
        self.clients("heat").stacks.output_show.assert_called_once_with(
            self.stack.id, self.default_output_key)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "heat.show_output")

    def test_stack_show_output_via_API(self):
        scenario = utils.HeatScenario(self.context)
        scenario._stack_show_output_via_API(
            self.stack, self.default_output_key)
        self.clients("heat").stacks.get.assert_called_once_with(
            stack_id=self.stack.id)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "heat.show_output_via_API")

    def test_stack_list_output(self):
        scenario = utils.HeatScenario(self.context)
        scenario._stack_list_output(self.stack)
        self.clients("heat").stacks.output_list.assert_called_once_with(
            self.stack.id)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "heat.list_output")

    def test_stack_list_output_via_API(self):
        scenario = utils.HeatScenario(self.context)
        scenario._stack_list_output_via_API(self.stack)
        self.clients("heat").stacks.get.assert_called_once_with(
            stack_id=self.stack.id)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "heat.list_output_via_API")


class HeatScenarioNegativeTestCase(test.ScenarioTestCase):
    patch_benchmark_utils = False

    def test_failed_create_stack(self):
        self.clients("heat").stacks.create.return_value = {
            "stack": {"id": "test_id"}
        }
        stack = mock.Mock()
        resource = mock.Mock()
        resource.stack_status = "CREATE_FAILED"
        stack.manager.get.return_value = resource
        self.clients("heat").stacks.get.return_value = stack
        scenario = utils.HeatScenario(context=self.context)
        ex = self.assertRaises(exceptions.GetResourceErrorStatus,
                               scenario._create_stack, "stack_name")
        self.assertIn("has CREATE_FAILED status", str(ex))

    def test_failed_update_stack(self):
        stack = mock.Mock()
        resource = mock.Mock()
        resource.stack_status = "UPDATE_FAILED"
        stack.manager.get.return_value = resource
        self.clients("heat").stacks.get.return_value = stack
        scenario = utils.HeatScenario(context=self.context)
        ex = self.assertRaises(exceptions.GetResourceErrorStatus,
                               scenario._update_stack, stack,
                               "heat_template_version: 2013-05-23")
        self.assertIn("has UPDATE_FAILED status", str(ex))
