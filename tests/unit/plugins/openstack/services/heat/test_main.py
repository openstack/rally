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

from rally.plugins.openstack.services.heat import main
from tests.unit import test


class Stack(main.Stack):
    def __init__(self):
        self.scenario = mock.Mock()


class StackTestCase(test.ScenarioTestCase):

    @mock.patch("rally.plugins.openstack.services.heat.main.open",
                create=True)
    def test___init__(self, mock_open):
        reads = [mock.Mock(), mock.Mock()]
        reads[0].read.return_value = "template_contents"
        reads[1].read.return_value = "file1_contents"
        mock_open.side_effect = reads
        stack = main.Stack("scenario", "task", "template",
                           parameters="parameters",
                           files={"f1_name": "f1_path"})
        self.assertEqual("template_contents", stack.template)
        self.assertEqual({"f1_name": "file1_contents"}, stack.files)
        self.assertEqual([mock.call("template"), mock.call("f1_path")],
                         mock_open.mock_calls)
        reads[0].read.assert_called_once_with()
        reads[1].read.assert_called_once_with()

    @mock.patch("rally.plugins.openstack.services.heat.main.utils")
    def test__wait(self, mock_utils):
        fake_stack = mock.Mock()
        stack = Stack()
        stack.stack = fake_stack = mock.Mock()
        stack._wait(["ready_statuses"], ["failure_statuses"])
        mock_utils.wait_for_status.assert_called_once_with(
            fake_stack, check_interval=1.0,
            ready_statuses=["ready_statuses"],
            failure_statuses=["failure_statuses"],
            timeout=3600.0,
            update_resource=mock_utils.get_from_manager())

    @mock.patch("rally.task.atomic")
    @mock.patch("rally.plugins.openstack.services.heat.main.open")
    @mock.patch("rally.plugins.openstack.services.heat.main.Stack._wait")
    def test_create(self, mock_stack__wait, mock_open, mock_task_atomic):
        mock_scenario = mock.MagicMock()
        mock_scenario.generate_random_name.return_value = "fake_name"
        mock_open().read.return_value = "fake_content"
        mock_new_stack = {
            "stack": {
                "id": "fake_id"
            }
        }
        mock_scenario.clients("heat").stacks.create.return_value = (
            mock_new_stack)

        stack = main.Stack(
            scenario=mock_scenario, task=mock.Mock(),
            template=mock.Mock(), files={}
        )
        stack.create()
        mock_scenario.clients("heat").stacks.create.assert_called_once_with(
            files={}, parameters=None, stack_name="fake_name",
            template="fake_content"
        )
        mock_scenario.clients("heat").stacks.get.assert_called_once_with(
            "fake_id")
        mock_stack__wait.assert_called_once_with(["CREATE_COMPLETE"],
                                                 ["CREATE_FAILED"])

    @mock.patch("rally.task.atomic")
    @mock.patch("rally.plugins.openstack.services.heat.main.open")
    @mock.patch("rally.plugins.openstack.services.heat.main.Stack._wait")
    def test_update(self, mock_stack__wait, mock_open, mock_task_atomic):
        mock_scenario = mock.MagicMock(stack_id="fake_id")
        mock_parameters = mock.Mock()
        mock_open().read.return_value = "fake_content"
        stack = main.Stack(
            scenario=mock_scenario, task=mock.Mock(),
            template=None, files={}, parameters=mock_parameters
        )
        stack.stack_id = "fake_id"
        stack.parameters = mock_parameters
        stack.update({"foo": "bar"})
        mock_scenario.clients("heat").stacks.update.assert_called_once_with(
            "fake_id", files={}, template="fake_content",
            parameters=mock_parameters
        )
        mock_stack__wait.assert_called_once_with(["UPDATE_COMPLETE"],
                                                 ["UPDATE_FAILED"])
