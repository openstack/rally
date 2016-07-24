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

from keystoneclient import exceptions as keystone_exceptions
import mock

from rally.cli.commands import deployment
from rally.cli import envutils
from rally.common import objects
from rally import consts
from rally import exceptions
from tests.unit import fakes
from tests.unit import test


class DeploymentCommandsTestCase(test.TestCase):
    def setUp(self):
        super(DeploymentCommandsTestCase, self).setUp()
        self.deployment = deployment.DeploymentCommands()

    @mock.patch.dict(os.environ, {"RALLY_DEPLOYMENT": "my_deployment_id"})
    @mock.patch("rally.cli.commands.deployment.DeploymentCommands.list")
    @mock.patch("rally.cli.commands.deployment.api.Deployment.create")
    @mock.patch("rally.cli.commands.deployment.open",
                side_effect=mock.mock_open(read_data="{\"some\": \"json\"}"),
                create=True)
    def test_create(self, mock_open, mock_deployment_create,
                    mock_deployment_commands_list):
        self.deployment.create("fake_deploy", False, "path_to_config.json")
        mock_deployment_create.assert_called_once_with(
            {"some": "json"}, "fake_deploy")

    @mock.patch.dict(os.environ, {"OS_AUTH_URL": "fake_auth_url",
                                  "OS_USERNAME": "fake_username",
                                  "OS_PASSWORD": "fake_password",
                                  "OS_TENANT_NAME": "fake_tenant_name",
                                  "OS_REGION_NAME": "fake_region_name",
                                  "OS_ENDPOINT_TYPE": "fake_endpoint_typeURL",
                                  "OS_ENDPOINT": "fake_endpoint",
                                  "OS_INSECURE": "True",
                                  "OS_CACERT": "fake_cacert",
                                  "RALLY_DEPLOYMENT": "fake_deployment_id"})
    @mock.patch("rally.cli.commands.deployment.api.Deployment.create")
    @mock.patch("rally.cli.commands.deployment.DeploymentCommands.list")
    def test_createfromenv_keystonev2(self, mock_list, mock_deployment_create):
        self.deployment.create("from_env", True)
        mock_deployment_create.assert_called_once_with(
            {
                "type": "ExistingCloud",
                "auth_url": "fake_auth_url",
                "region_name": "fake_region_name",
                "endpoint_type": "fake_endpoint_type",
                "endpoint": "fake_endpoint",
                "admin": {
                    "username": "fake_username",
                    "password": "fake_password",
                    "tenant_name": "fake_tenant_name"
                },
                "https_insecure": True,
                "https_cacert": "fake_cacert"
            },
            "from_env"
        )

    @mock.patch.dict(os.environ, {"OS_AUTH_URL": "fake_auth_url",
                                  "OS_USERNAME": "fake_username",
                                  "OS_PASSWORD": "fake_password",
                                  "OS_TENANT_NAME": "fake_tenant_name",
                                  "OS_REGION_NAME": "fake_region_name",
                                  "OS_ENDPOINT_TYPE": "fake_endpoint_typeURL",
                                  "OS_PROJECT_DOMAIN_NAME": "fake_pdn",
                                  "OS_USER_DOMAIN_NAME": "fake_udn",
                                  "OS_ENDPOINT": "fake_endpoint",
                                  "OS_INSECURE": "True",
                                  "OS_CACERT": "fake_cacert",
                                  "RALLY_DEPLOYMENT": "fake_deployment_id"})
    @mock.patch("rally.cli.commands.deployment.api.Deployment.create")
    @mock.patch("rally.cli.commands.deployment.DeploymentCommands.list")
    def test_createfromenv_keystonev3(self, mock_list, mock_deployment_create):
        self.deployment.create("from_env", True)
        mock_deployment_create.assert_called_once_with(
            {
                "type": "ExistingCloud",
                "auth_url": "fake_auth_url",
                "region_name": "fake_region_name",
                "endpoint_type": "fake_endpoint_type",
                "endpoint": "fake_endpoint",
                "admin": {
                    "username": "fake_username",
                    "password": "fake_password",
                    "user_domain_name": "fake_udn",
                    "project_domain_name": "fake_pdn",
                    "project_name": "fake_tenant_name"
                },
                "https_insecure": True,
                "https_cacert": "fake_cacert"
            },
            "from_env"
        )

    @mock.patch("rally.cli.commands.deployment.DeploymentCommands.list")
    @mock.patch("rally.cli.commands.deployment.DeploymentCommands.use")
    @mock.patch("rally.cli.commands.deployment.api.Deployment.create",
                return_value=dict(uuid="uuid"))
    @mock.patch("rally.cli.commands.deployment.open",
                side_effect=mock.mock_open(read_data="{\"uuid\": \"uuid\"}"),
                create=True)
    def test_create_and_use(self, mock_open, mock_deployment_create,
                            mock_deployment_commands_use,
                            mock_deployment_commands_list):
        self.deployment.create("fake_deploy", False, "path_to_config.json",
                               True)
        mock_deployment_create.assert_called_once_with(
            {"uuid": "uuid"}, "fake_deploy")
        mock_deployment_commands_use.assert_called_once_with("uuid")

    @mock.patch("rally.cli.commands.deployment.api.Deployment.recreate")
    def test_recreate(self, mock_deployment_recreate):
        deployment_id = "43924f8b-9371-4152-af9f-4cf02b4eced4"
        self.deployment.recreate(deployment_id)
        mock_deployment_recreate.assert_called_once_with(deployment_id)

    @mock.patch("rally.cli.commands.deployment.envutils.get_global")
    def test_recreate_no_deployment_id(self, mock_get_global):
        mock_get_global.side_effect = exceptions.InvalidArgumentsException
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.deployment.recreate, None)

    @mock.patch("rally.cli.commands.deployment.api.Deployment.destroy")
    def test_destroy(self, mock_deployment_destroy):
        deployment_id = "53fd0273-60ce-42e5-a759-36f1a683103e"
        self.deployment.destroy(deployment_id)
        mock_deployment_destroy.assert_called_once_with(deployment_id)

    @mock.patch("rally.cli.commands.deployment.envutils.get_global")
    def test_destroy_no_deployment_id(self, mock_get_global):
        mock_get_global.side_effect = exceptions.InvalidArgumentsException
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.deployment.destroy, None)

    @mock.patch("rally.cli.commands.deployment.cliutils.print_list")
    @mock.patch("rally.cli.commands.deployment.utils.Struct")
    @mock.patch("rally.cli.commands.deployment.envutils.get_global")
    @mock.patch("rally.cli.commands.deployment.api.Deployment.list")
    def test_list_different_deployment_id(self, mock_deployment_list,
                                          mock_get_global, mock_struct,
                                          mock_print_list):
        current_deployment_id = "26a3ce76-0efa-40e4-86e5-514574bd1ff6"
        mock_get_global.return_value = current_deployment_id
        fake_deployment_list = [
            {"uuid": "fa34aea2-ae2e-4cf7-a072-b08d67466e3e",
             "created_at": "03-12-2014",
             "name": "dep1",
             "status": "deploy->started",
             "active": "False"}]

        mock_deployment_list.return_value = fake_deployment_list
        self.deployment.list()

        fake_deployment = fake_deployment_list[0]
        fake_deployment["active"] = ""
        mock_struct.assert_called_once_with(**fake_deployment)

        headers = ["uuid", "created_at", "name", "status", "active"]
        mock_print_list.assert_called_once_with([mock_struct()], headers,
                                                sortby_index=headers.index(
                                                "created_at"))

    @mock.patch("rally.cli.commands.deployment.cliutils.print_list")
    @mock.patch("rally.cli.commands.deployment.utils.Struct")
    @mock.patch("rally.cli.commands.deployment.envutils.get_global")
    @mock.patch("rally.cli.commands.deployment.api.Deployment.list")
    def test_list_current_deployment_id(self, mock_deployment_list,
                                        mock_get_global, mock_struct,
                                        mock_print_list):
        current_deployment_id = "64258e84-ffa1-4011-9e4c-aba07bdbcc6b"
        mock_get_global.return_value = current_deployment_id
        fake_deployment_list = [{"uuid": current_deployment_id,
                                 "created_at": "13-12-2014",
                                 "name": "dep2",
                                 "status": "deploy->finished",
                                 "active": "True"}]
        mock_deployment_list.return_value = fake_deployment_list
        self.deployment.list()

        fake_deployment = fake_deployment_list[0]
        fake_deployment["active"] = "*"
        mock_struct.assert_called_once_with(**fake_deployment)

        headers = ["uuid", "created_at", "name", "status", "active"]
        mock_print_list.assert_called_once_with([mock_struct()], headers,
                                                sortby_index=headers.index(
                                                "created_at"))

    @mock.patch("rally.cli.commands.deployment.api.Deployment.get")
    @mock.patch("json.dumps")
    def test_config(self, mock_json_dumps, mock_deployment_get):
        deployment_id = "fa4a423e-f15d-4d83-971a-89574f892999"
        value = {"config": "config"}
        mock_deployment_get.return_value = value
        self.deployment.config(deployment_id)
        mock_json_dumps.assert_called_once_with(value["config"],
                                                sort_keys=True, indent=4)
        mock_deployment_get.assert_called_once_with(deployment_id)

    @mock.patch("rally.cli.commands.deployment.envutils.get_global")
    def test_config_no_deployment_id(self, mock_get_global):
        mock_get_global.side_effect = exceptions.InvalidArgumentsException
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.deployment.config, None)

    @mock.patch("rally.cli.commands.deployment.cliutils.print_list")
    @mock.patch("rally.cli.commands.deployment.utils.Struct")
    @mock.patch("rally.cli.commands.deployment.api.Deployment.get")
    def test_show(self, mock_deployment_get, mock_struct, mock_print_list):
        deployment_id = "b1a6153e-a314-4cb3-b63b-cf08c1a416c3"
        value = {
            "admin": {
                "auth_url": "url",
                "username": "u",
                "password": "p",
                "tenant_name": "t",
                "region_name": "r",
                "endpoint_type": consts.EndpointType.INTERNAL
            },
            "users": []
        }
        mock_deployment_get.return_value = value
        self.deployment.show(deployment_id)
        mock_deployment_get.assert_called_once_with(deployment_id)

        headers = ["auth_url", "username", "password", "tenant_name",
                   "region_name", "endpoint_type"]
        fake_data = ["url", "u", "***", "t", "r", consts.EndpointType.INTERNAL]
        mock_struct.assert_called_once_with(**dict(zip(headers, fake_data)))
        mock_print_list.assert_called_once_with([mock_struct()], headers)

    @mock.patch("rally.cli.commands.deployment.envutils.get_global")
    def test_deploy_no_deployment_id(self, mock_get_global):
        mock_get_global.side_effect = exceptions.InvalidArgumentsException
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.deployment.show, None)

    @mock.patch("os.remove")
    @mock.patch("os.symlink")
    @mock.patch("rally.cli.commands.deployment.api.Deployment.get",
                return_value=fakes.FakeDeployment(
                    uuid="593b683c-4b16-4b2b-a56b-e162bd60f10b"))
    @mock.patch("os.path.exists", return_value=True)
    @mock.patch("rally.common.fileutils.update_env_file")
    def test_use(self, mock_update_env_file, mock_path_exists,
                 mock_deployment_get, mock_symlink, mock_remove):
        deployment_id = mock_deployment_get.return_value["uuid"]

        mock_deployment_get.return_value["admin"] = {
            "auth_url": "fake_auth_url",
            "username": "fake_username",
            "password": "fake_password",
            "tenant_name": "fake_tenant_name",
            "endpoint": "fake_endpoint",
            "region_name": None}

        with mock.patch("rally.cli.commands.deployment.open", mock.mock_open(),
                        create=True) as mock_file:
            self.deployment.use(deployment_id)
            self.assertEqual(2, mock_path_exists.call_count)
            mock_update_env_file.assert_called_once_with(os.path.expanduser(
                "~/.rally/globals"),
                "RALLY_DEPLOYMENT", "%s\n" % deployment_id)
            mock_file.return_value.write.assert_any_call(
                "export OS_ENDPOINT='fake_endpoint'\n")
            mock_file.return_value.write.assert_any_call(
                "export OS_AUTH_URL='fake_auth_url'\n"
                "export OS_USERNAME='fake_username'\n"
                "export OS_PASSWORD='fake_password'\n"
                "export OS_TENANT_NAME='fake_tenant_name'\n")
            mock_symlink.assert_called_once_with(
                os.path.expanduser("~/.rally/openrc-%s" % deployment_id),
                os.path.expanduser("~/.rally/openrc"))
            mock_remove.assert_called_once_with(os.path.expanduser(
                "~/.rally/openrc"))

    @mock.patch("os.remove")
    @mock.patch("os.symlink")
    @mock.patch("rally.cli.commands.deployment.api.Deployment.get",
                return_value=fakes.FakeDeployment(
                    uuid="593b683c-4b16-4b2b-a56b-e162bd60f10b"))
    @mock.patch("os.path.exists", return_value=True)
    @mock.patch("rally.common.fileutils.update_env_file")
    def test_use_with_v3_auth(self, mock_update_env_file, mock_path_exists,
                              mock_deployment_get, mock_symlink, mock_remove):
        deployment_id = mock_deployment_get.return_value["uuid"]

        mock_deployment_get.return_value["admin"] = {
            "auth_url": "http://localhost:5000/v3",
            "username": "fake_username",
            "password": "fake_password",
            "tenant_name": "fake_tenant_name",
            "endpoint": "fake_endpoint",
            "region_name": None,
            "user_domain_name": "fake_user_domain",
            "project_domain_name": "fake_project_domain"}

        with mock.patch("rally.cli.commands.deployment.open", mock.mock_open(),
                        create=True) as mock_file:
            self.deployment.use(deployment_id)
            self.assertEqual(2, mock_path_exists.call_count)
            mock_update_env_file.assert_called_once_with(os.path.expanduser(
                "~/.rally/globals"),
                "RALLY_DEPLOYMENT", "%s\n" % deployment_id)
            mock_file.return_value.write.assert_any_call(
                "export OS_ENDPOINT='fake_endpoint'\n")
            mock_file.return_value.write.assert_any_call(
                "export OS_AUTH_URL='http://localhost:5000/v3'\n"
                "export OS_USERNAME='fake_username'\n"
                "export OS_PASSWORD='fake_password'\n"
                "export OS_TENANT_NAME='fake_tenant_name'\n")
            mock_file.return_value.write.assert_any_call(
                "export OS_USER_DOMAIN_NAME='fake_user_domain'\n"
                "export OS_PROJECT_DOMAIN_NAME='fake_project_domain'\n")
            mock_symlink.assert_called_once_with(
                os.path.expanduser("~/.rally/openrc-%s" % deployment_id),
                os.path.expanduser("~/.rally/openrc"))
            mock_remove.assert_called_once_with(os.path.expanduser(
                "~/.rally/openrc"))

    @mock.patch("rally.cli.commands.deployment.DeploymentCommands."
                "_update_openrc_deployment_file")
    @mock.patch("rally.common.fileutils.update_globals_file")
    @mock.patch("rally.cli.commands.deployment.api.Deployment")
    def test_use_by_name(self, mock_api_deployment, mock_update_globals_file,
                         mock__update_openrc_deployment_file):
        fake_deployment = fakes.FakeDeployment(
            uuid="fake_uuid",
            admin="fake_credentials")
        mock_api_deployment.list.return_value = [fake_deployment]
        mock_api_deployment.get.return_value = fake_deployment
        status = self.deployment.use(deployment="fake_name")
        self.assertIsNone(status)
        mock_api_deployment.get.assert_called_once_with("fake_name")
        mock_update_globals_file.assert_called_once_with(
            envutils.ENV_DEPLOYMENT, "fake_uuid")
        mock__update_openrc_deployment_file.assert_called_once_with(
            "fake_uuid", "fake_credentials")

    @mock.patch("rally.cli.commands.deployment.api.Deployment.get")
    def test_deployment_not_found(self, mock_deployment_get):
        deployment_id = "e87e4dca-b515-4477-888d-5f6103f13b42"
        mock_deployment_get.side_effect = exceptions.DeploymentNotFound(
            deployment=deployment_id)
        self.assertEqual(1, self.deployment.use(deployment_id))

    @mock.patch("rally.cli.commands.deployment.cliutils.print_list")
    @mock.patch("rally.cli.commands.deployment.api.Deployment.check")
    @mock.patch("rally.cli.commands.deployment.api.Deployment.get")
    def test_deployment_check(self, mock_deployment_get,
                              mock_deployment_check, mock_print_list):
        deployment_id = "e87e4dca-b515-4477-888d-5f6103f13b42"
        sample_credential = objects.Credential("http://192.168.1.1:5000/v2.0/",
                                               "admin",
                                               "adminpass").to_dict()
        deployment = {"admin": sample_credential,
                      "users": [sample_credential]}
        mock_deployment_get.return_value = deployment
        mock_deployment_check.return_value = {}

        self.deployment.check(deployment_id)

        mock_deployment_get.assert_called_once_with(deployment_id)
        mock_deployment_check.assert_called_once_with(deployment)
        headers = ["services", "type", "status"]
        mock_print_list.assert_called_once_with([], headers)

    @mock.patch("rally.cli.commands.deployment.api.Deployment.get")
    def test_deployment_check_not_exist(self, mock_deployment_get):
        deployment_id = "e87e4dca-b515-4477-888d-5f6103f13b42"
        mock_deployment_get.side_effect = exceptions.DeploymentNotFound(
            deployment=deployment_id)
        self.assertEqual(self.deployment.check(deployment_id), 1)

    @mock.patch("rally.cli.commands.deployment.api.Deployment.check")
    @mock.patch("rally.cli.commands.deployment.api.Deployment.get")
    def test_deployment_check_raise(self, mock_deployment_get,
                                    mock_deployment_check):
        deployment_id = "e87e4dca-b515-4477-888d-5f6103f13b42"
        sample_credential = objects.Credential("http://192.168.1.1:5000/v2.0/",
                                               "admin",
                                               "adminpass").to_dict()
        sample_credential["not-exist-key"] = "error"
        mock_deployment_get.return_value = {"admin": sample_credential}
        refused = keystone_exceptions.ConnectionRefused()
        mock_deployment_check.side_effect = refused
        self.assertEqual(self.deployment.check(deployment_id), 1)
