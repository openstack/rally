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

import os

import mock

from rally.cmd.commands import use
from rally.cmd import envutils
from rally import exceptions
from tests.unit import fakes
from tests.unit import test

MOD = "rally.cmd.commands.use."


class UseCommandsTestCase(test.TestCase):
    def setUp(self):
        super(UseCommandsTestCase, self).setUp()
        self.use = use.UseCommands()

    @mock.patch("rally.cmd.commands.use.db.deployment_get",
                side_effect=exceptions.DeploymentNotFound())
    def test_deployment_use_no_args(self, mock_d_get):
        status = self.use.deployment()
        self.assertEqual(1, status)

    @mock.patch(MOD + "UseCommands._update_openrc_deployment_file")
    @mock.patch(MOD + "UseCommands._update_attribute_in_global_file")
    @mock.patch(MOD + "UseCommands._ensure_rally_configuration_dir_exists")
    @mock.patch(MOD + "db")
    def test_deployment_use_by_name(self, m_db, m_ercde, m_uaigf, m_uodf):
        fake_deployment = fakes.FakeDeployment(
            uuid="fake_uuid",
            admin="fake_endpoints")
        m_db.deployment_list.return_value = [fake_deployment]
        m_db.deployment_get.return_value = fake_deployment
        status = self.use.deployment(deployment="fake_name")
        self.assertIsNone(status)
        m_db.deployment_get.assert_called_once_with("fake_name")
        m_ercde.assert_called_once_with()
        m_uaigf.assert_called_once_with(envutils.ENV_DEPLOYMENT, "fake_uuid")
        m_uodf.assert_called_once_with("fake_uuid", "fake_endpoints")

    @mock.patch("os.remove")
    @mock.patch("os.symlink")
    @mock.patch(
        MOD + "db.deployment_get",
        return_value=fakes.FakeDeployment(
            uuid="593b683c-4b16-4b2b-a56b-e162bd60f10b"))
    @mock.patch("os.path.exists", return_value=True)
    @mock.patch(MOD + "fileutils.update_env_file")
    def test_deployment(self, mock_env, mock_path, mock_deployment,
                        mock_symlink, mock_remove):
        deployment_id = mock_deployment.return_value["uuid"]

        mock_deployment.return_value["admin"] = {
                "auth_url": "fake_auth_url",
                "username": "fake_username",
                "password": "fake_password",
                "tenant_name": "fake_tenant_name",
                "region_name": None}

        with mock.patch("rally.cmd.commands.use.open", mock.mock_open(),
                        create=True) as mock_file:
            self.use.deployment(deployment_id)
            self.assertEqual(2, mock_path.call_count)
            mock_env.assert_called_once_with(os.path.expanduser(
                "~/.rally/globals"),
                "RALLY_DEPLOYMENT", "%s\n" % deployment_id)
            mock_file.return_value.write.assert_called_once_with(
                "export OS_AUTH_URL=fake_auth_url\n"
                "export OS_USERNAME=fake_username\n"
                "export OS_PASSWORD=fake_password\n"
                "export OS_TENANT_NAME=fake_tenant_name\n")
            mock_symlink.assert_called_once_with(
                os.path.expanduser("~/.rally/openrc-%s" % deployment_id),
                os.path.expanduser("~/.rally/openrc"))
            mock_remove.assert_called_once_with(os.path.expanduser(
                "~/.rally/openrc"))

    @mock.patch(MOD + "db.deployment_get")
    def test_deployment_not_found(self, mock_deployment):
        deployment_id = "e87e4dca-b515-4477-888d-5f6103f13b42"
        mock_deployment.side_effect = exceptions.DeploymentNotFound(
            uuid=deployment_id)
        self.assertEqual(1, self.use.deployment(deployment_id))

    @mock.patch(MOD + "fileutils._rewrite_env_file")
    @mock.patch(MOD + "db.task_get", return_value=True)
    def test_task(self, mock_task, mock_file):
        task_id = "80422553-5774-44bd-98ac-38bd8c7a0feb"
        self.use.task(task_id)
        mock_file.assert_called_once_with(
            os.path.expanduser("~/.rally/globals"),
            ["RALLY_TASK=%s\n" % task_id])

    @mock.patch(MOD + "db.task_get")
    def test_task_not_found(self, mock_task):
        task_id = "ddc3f8ba-082a-496d-b18f-72cdf5c10a14"
        mock_task.side_effect = exceptions.TaskNotFound(uuid=task_id)
        self.assertRaises(exceptions.TaskNotFound, self.use.task, task_id)
