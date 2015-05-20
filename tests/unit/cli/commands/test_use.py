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

from rally.cli.commands import use
from tests.unit import test

MOD = "rally.cli.commands.use."


class UseCommandsTestCase(test.TestCase):
    def setUp(self):
        super(UseCommandsTestCase, self).setUp()
        self.use = use.UseCommands()

    @mock.patch("rally.cli.commands.deployment.DeploymentCommands.use")
    def test_deployment(self, mock_deployment_use):
        self.use.deployment("fake_id")
        mock_deployment_use.assert_called_once_with("fake_id")

    @mock.patch("rally.cli.commands.task.TaskCommands.use")
    def test_task(self, mock_task_use):
        self.use.task("fake_id")
        mock_task_use.assert_called_once_with("fake_id")

    @mock.patch("rally.cli.commands.verify.VerifyCommands.use")
    def test_verification(self, mock_verify_use):
        self.use.verification("fake_id")
        mock_verify_use.assert_called_once_with("fake_id")
