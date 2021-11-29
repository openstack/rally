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

import collections
import io
import os
from unittest import mock

from rally.cli import cliutils
from rally.cli.commands import deployment
from rally.cli import envutils
from rally import consts
from rally import exceptions
from tests.unit import fakes
from tests.unit import test


class DeploymentCommandsTestCase(test.TestCase):
    def setUp(self):
        super(DeploymentCommandsTestCase, self).setUp()
        self.deployment = deployment.DeploymentCommands()
        self.fake_api = fakes.FakeAPI()

    @mock.patch.dict(os.environ, {"RALLY_DEPLOYMENT": "my_deployment_id"})
    @mock.patch("rally.cli.commands.deployment.DeploymentCommands.list")
    @mock.patch("rally.cli.commands.deployment.open",
                side_effect=mock.mock_open(read_data="{\"some\": \"json\"}"),
                create=True)
    def test_create(self, mock_open, mock_deployment_commands_list):
        self.deployment.create(self.fake_api, "fake_deploy", False,
                               "path_to_config.json")
        self.fake_api.deployment.create.assert_called_once_with(
            config={"some": "json"}, name="fake_deploy")

    @mock.patch.dict(os.environ, {"RALLY_DEPLOYMENT": "my_deployment_id"})
    @mock.patch("rally.cli.commands.deployment.DeploymentCommands.list")
    def test_create_empty(self, mock_deployment_commands_list):
        self.deployment.create(self.fake_api, "fake_deploy")
        self.fake_api.deployment.create.assert_called_once_with(
            config={}, name="fake_deploy")

    @mock.patch("rally.env.env_mgr.EnvManager.create_spec_from_sys_environ",
                return_value={"spec": {"auth_url": "http://fake"}})
    def test_create_fromenv(self, mock_create_spec_from_sys_environ):
        self.deployment.create(self.fake_api, "from_env", True)
        self.fake_api.deployment.create.assert_called_once_with(
            config={"auth_url": "http://fake"},
            name="from_env"
        )

    @mock.patch("rally.env.env_mgr.EnvManager.create_spec_from_sys_environ")
    def test_create_fromenv_openstack(self, mock_create_spec_from_sys_environ):

        mock_create_spec_from_sys_environ.side_effect = lambda: {
            "spec": {
                "existing@openstack": {
                    "https_key": "some key",
                    "another_key": "another"
                }
            }
        }
        mock_rally_os = mock.Mock()
        mock_rally_os.__version_tuple__ = (1, 4, 0)

        with mock.patch.dict("sys.modules",
                             {"rally_openstack": mock_rally_os}):
            self.deployment.create(self.fake_api, "from_env", True)
            self.fake_api.deployment.create.assert_called_once_with(
                config={"existing@openstack": {"another_key": "another"}},
                name="from_env"
            )

            self.fake_api.deployment.create.reset_mock()
            mock_rally_os.__version_tuple__ = (1, 5, 0)
            self.deployment.create(self.fake_api, "from_env", True)
            self.fake_api.deployment.create.assert_called_once_with(
                config={"existing@openstack": {"another_key": "another",
                                               "https_key": "some key"}},
                name="from_env"
            )

    @mock.patch("rally.cli.commands.deployment.DeploymentCommands.list")
    @mock.patch("rally.cli.commands.deployment.DeploymentCommands.use")
    @mock.patch("rally.cli.commands.deployment.open",
                side_effect=mock.mock_open(read_data="{\"uuid\": \"uuid\"}"),
                create=True)
    def test_create_and_use(self, mock_open, mock_deployment_commands_use,
                            mock_deployment_commands_list):
        self.fake_api.deployment.create.return_value = dict(uuid="uuid")
        self.deployment.create(self.fake_api, "fake_deploy", False,
                               "path_to_config.json", True)
        self.fake_api.deployment.create.assert_called_once_with(
            config={"uuid": "uuid"}, name="fake_deploy")
        mock_deployment_commands_list.assert_called_once_with(
            self.fake_api, deployment_list=[{"uuid": "uuid"}])
        mock_deployment_commands_use.assert_called_once_with(
            self.fake_api, self.fake_api.deployment.create.return_value)

    def test_recreate(self):
        deployment_id = "43924f8b-9371-4152-af9f-4cf02b4eced4"
        self.deployment.recreate(self.fake_api, deployment_id)
        self.fake_api.deployment.recreate.assert_called_once_with(
            deployment=deployment_id, config=None)

    @mock.patch("rally.cli.commands.deployment.open",
                side_effect=mock.mock_open(read_data="{\"some\": \"json\"}"),
                create=True)
    def test_recreate_config(self, mock_open):
        deployment_id = "43924f8b-9371-4152-af9f-4cf02b4eced4"
        self.deployment.recreate(self.fake_api, deployment_id,
                                 filename="my.json")
        self.fake_api.deployment.recreate.assert_called_once_with(
            deployment=deployment_id, config={"some": "json"})

    @mock.patch("rally.cli.commands.deployment.envutils.get_global")
    def test_recreate_no_deployment_id(self, mock_get_global):
        mock_get_global.side_effect = exceptions.InvalidArgumentsException
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.deployment.recreate, None)

    def test_destroy(self):
        deployment_id = "53fd0273-60ce-42e5-a759-36f1a683103e"
        self.deployment.destroy(self.fake_api, deployment_id)
        self.fake_api.deployment.destroy.assert_called_once_with(
            deployment=deployment_id)

    @mock.patch("rally.cli.commands.deployment.envutils.get_global")
    def test_destroy_no_deployment_id(self, mock_get_global):
        mock_get_global.side_effect = exceptions.InvalidArgumentsException
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.deployment.destroy, self.fake_api, None)

    @mock.patch("rally.cli.commands.deployment.cliutils.print_list")
    @mock.patch("rally.cli.commands.deployment.utils.Struct")
    @mock.patch("rally.cli.commands.deployment.envutils.get_global")
    def test_list_different_deployment_id(self, mock_get_global, mock_struct,
                                          mock_print_list):
        current_deployment_id = "26a3ce76-0efa-40e4-86e5-514574bd1ff6"
        mock_get_global.return_value = current_deployment_id
        fake_deployment_list = [
            {"uuid": "fa34aea2-ae2e-4cf7-a072-b08d67466e3e",
             "created_at": "03-12-2014",
             "name": "dep1",
             "status": "deploy->started",
             "active": "False"}]

        self.fake_api.deployment.list.return_value = fake_deployment_list
        self.deployment.list(self.fake_api)

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
    def test_list_current_deployment_id(self, mock_get_global, mock_struct,
                                        mock_print_list):
        current_deployment_id = "64258e84-ffa1-4011-9e4c-aba07bdbcc6b"
        mock_get_global.return_value = current_deployment_id
        fake_deployment_list = [{"uuid": current_deployment_id,
                                 "created_at": "13-12-2014",
                                 "name": "dep2",
                                 "status": "deploy->finished",
                                 "active": "True"}]
        self.fake_api.deployment.list.return_value = fake_deployment_list
        self.deployment.list(self.fake_api)

        fake_deployment = fake_deployment_list[0]
        fake_deployment["active"] = "*"
        mock_struct.assert_called_once_with(**fake_deployment)

        headers = ["uuid", "created_at", "name", "status", "active"]
        mock_print_list.assert_called_once_with([mock_struct()], headers,
                                                sortby_index=headers.index(
                                                "created_at"))

    @mock.patch("json.dumps")
    def test_config(self, mock_json_dumps):
        deployment_id = "fa4a423e-f15d-4d83-971a-89574f892999"
        value = {"config": "config"}
        self.fake_api.deployment.get.return_value = value
        self.deployment.config(self.fake_api, deployment_id)
        mock_json_dumps.assert_called_once_with(value["config"],
                                                sort_keys=True, indent=4)
        self.fake_api.deployment.get.assert_called_once_with(
            deployment=deployment_id)

    @mock.patch("rally.cli.commands.deployment.envutils.get_global")
    def test_config_no_deployment_id(self, mock_get_global):
        mock_get_global.side_effect = exceptions.InvalidArgumentsException
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.deployment.config, self.fake_api, None)

    @mock.patch("rally.cli.commands.deployment.cliutils.print_list")
    @mock.patch("rally.cli.commands.deployment.utils.Struct")
    def test_show(self, mock_struct, mock_print_list):
        deployment_id = "b1a6153e-a314-4cb3-b63b-cf08c1a416c3"
        value = {"admin": {"auth_url": "url",
                           "username": "u",
                           "password": "p",
                           "tenant_name": "t",
                           "region_name": "r",
                           "endpoint_type": consts.EndpointType.INTERNAL},
                 "users": []}
        deployment = self.fake_api.deployment.get
        deployment.return_value = {"credentials": {"openstack": [
            {"admin": value["admin"],
             "users": []}]}}
        self.deployment.show(self.fake_api, deployment_id)
        self.fake_api.deployment.get.assert_called_once_with(
            deployment=deployment_id)

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
    @mock.patch("os.path.exists", return_value=True)
    @mock.patch("rally.cli.envutils._update_env_file")
    def test_use(self, mock__update_env_file, mock_path_exists,
                 mock_symlink, mock_remove):
        deployment_id = "593b683c-4b16-4b2b-a56b-e162bd60f10b"
        self.fake_api.deployment.get.return_value = {
            "uuid": deployment_id,
            "credentials": {
                "openstack": [{
                    "admin": {"auth_url": "fake_auth_url",
                              "username": "fake_username",
                              "password": "fake_password",
                              "tenant_name": "fake_tenant_name",
                              "endpoint": "fake_endpoint",
                              "region_name": None}}]}}

        with mock.patch("rally.cli.commands.deployment.open", mock.mock_open(),
                        create=True) as mock_file:
            self.deployment.use(self.fake_api, deployment_id)
            self.assertEqual(3, mock_path_exists.call_count)
            mock__update_env_file.assert_has_calls([
                mock.call(os.path.expanduser("~/.rally/globals"),
                          "RALLY_DEPLOYMENT", "%s\n" % deployment_id),
                mock.call(os.path.expanduser("~/.rally/globals"),
                          "RALLY_ENV", "%s\n" % deployment_id),
            ])

            mock_file.return_value.write.assert_any_call(
                "export OS_ENDPOINT='fake_endpoint'\n")
            mock_file.return_value.write.assert_any_call(
                "export OS_AUTH_URL='fake_auth_url'\n"
                "export OS_USERNAME='fake_username'\n"
                "export OS_PASSWORD='fake_password'\n"
                "export OS_TENANT_NAME='fake_tenant_name'\n"
                "export OS_PROJECT_NAME='fake_tenant_name'\n")
            mock_symlink.assert_called_once_with(
                os.path.expanduser("~/.rally/openrc-%s" % deployment_id),
                os.path.expanduser("~/.rally/openrc"))
            mock_remove.assert_called_once_with(os.path.expanduser(
                "~/.rally/openrc"))

    @mock.patch("os.remove")
    @mock.patch("os.symlink")
    @mock.patch("os.path.exists", return_value=True)
    @mock.patch("rally.cli.envutils._update_env_file")
    def test_use_with_v3_auth(self, mock__update_env_file, mock_path_exists,
                              mock_symlink, mock_remove):
        deployment_id = "593b683c-4b16-4b2b-a56b-e162bd60f10b"

        self.fake_api.deployment.get.return_value = {
            "uuid": deployment_id,
            "credentials": {
                "openstack": [{
                    "admin": {"auth_url": "http://localhost:5000/v3",
                              "username": "fake_username",
                              "password": "fake_password",
                              "tenant_name": "fake_tenant_name",
                              "endpoint": "fake_endpoint",
                              "region_name": None,
                              "user_domain_name": "fake_user_domain",
                              "project_domain_name": "fake_project_domain"}}]}}

        with mock.patch("rally.cli.commands.deployment.open", mock.mock_open(),
                        create=True) as mock_file:
            self.deployment.use(self.fake_api, deployment_id)
            self.assertEqual(3, mock_path_exists.call_count)
            mock__update_env_file.assert_has_calls([
                mock.call(os.path.expanduser("~/.rally/globals"),
                          "RALLY_DEPLOYMENT", "%s\n" % deployment_id),
                mock.call(os.path.expanduser("~/.rally/globals"),
                          "RALLY_ENV", "%s\n" % deployment_id)
            ])
            mock_file.return_value.write.assert_any_call(
                "export OS_ENDPOINT='fake_endpoint'\n")
            mock_file.return_value.write.assert_any_call(
                "export OS_AUTH_URL='http://localhost:5000/v3'\n"
                "export OS_USERNAME='fake_username'\n"
                "export OS_PASSWORD='fake_password'\n"
                "export OS_TENANT_NAME='fake_tenant_name'\n"
                "export OS_PROJECT_NAME='fake_tenant_name'\n")
            mock_file.return_value.write.assert_any_call(
                "export OS_IDENTITY_API_VERSION=3\n"
                "export OS_USER_DOMAIN_NAME='fake_user_domain'\n"
                "export OS_PROJECT_DOMAIN_NAME='fake_project_domain'\n")
            mock_symlink.assert_called_once_with(
                os.path.expanduser("~/.rally/openrc-%s" % deployment_id),
                os.path.expanduser("~/.rally/openrc"))
            mock_remove.assert_called_once_with(os.path.expanduser(
                "~/.rally/openrc"))

    @mock.patch("rally.cli.commands.deployment.DeploymentCommands."
                "_update_openrc_deployment_file")
    @mock.patch("rally.cli.envutils.update_globals_file")
    def test_use_by_name(self, mock_update_globals_file,
                         mock__update_openrc_deployment_file):
        fake_credentials = {"admin": "foo_admin", "users": ["foo_user"]}
        fake_deployment = {"uuid": "fake_uuid",
                           "credentials": {"openstack": [fake_credentials]}}
        self.fake_api.deployment.list.return_value = [fake_deployment]
        self.fake_api.deployment.get.return_value = fake_deployment
        status = self.deployment.use(self.fake_api, deployment="fake_name")
        self.assertIsNone(status)
        self.fake_api.deployment.get.assert_called_once_with(
            deployment="fake_name")
        mock_update_globals_file.assert_has_calls([
            mock.call(envutils.ENV_DEPLOYMENT, "fake_uuid"),
            mock.call(envutils.ENV_ENV, "fake_uuid")
        ])
        mock__update_openrc_deployment_file.assert_called_once_with(
            "fake_uuid", "foo_admin")

    def test_deployment_not_found(self):
        deployment_id = "e87e4dca-b515-4477-888d-5f6103f13b42"
        exc = exceptions.DBRecordNotFound(criteria="uuid: %s" % deployment_id,
                                          table="deployments")
        self.fake_api.deployment.get.side_effect = exc
        self.assertEqual(1, self.deployment.use(self.fake_api, deployment_id))

    @mock.patch("rally.cli.commands.deployment.logging.is_debug",
                return_value=False)
    @mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_deployment_check(self, mock_stdout, mock_is_debug):
        deployment_uuid = "some"
        # OrderedDict is used to predict the order of platfrom in output
        self.fake_api.deployment.check.return_value = collections.OrderedDict([
            ("openstack", [{"services": [
                {"name": "nova", "type": "compute"},
                {"name": "keystone", "type": "identity"},
                {"name": "cinder", "type": "volume"}]}]),
            ("docker", [{"admin_error": {"etype": "ProviderError",
                                         "msg": "No money - no funny!",
                                         "trace": "file1\nline1"},
                        "services": []}]),
            ("something", [{"services": [
                {"name": "foo", "type": "bar", "version": "777"},
                {"name": "xxx", "type": "yyy", "version": "777",
                 "status": "Failed", "description": "Fake service"}]},
                {"services": [], "user_error":
                    {"etype": "ProviderError",
                     "msg": "No money - no funny!",
                     "trace": "file1\nline1"}}
            ])])

        origin_print_list = cliutils.print_list

        def print_list(*args, **kwargs):
            kwargs["out"] = mock_stdout
            return origin_print_list(*args, **kwargs)

        with mock.patch.object(deployment.cliutils, "print_list",
                               new=print_list):
            self.assertEqual(
                1, self.deployment.check(self.fake_api, deployment_uuid))

        self.assertEqual(
            "-----------------------------------------------------------------"
            "---------------\nPlatform openstack:\n"
            "-----------------------------------------------------------------"
            "---------------\n\nAvailable services:\n"
            "+----------+--------------+-----------+\n"
            "| Service  | Service Type | Status    |\n"
            "+----------+--------------+-----------+\n"
            "| cinder   | volume       | Available |\n"
            "| keystone | identity     | Available |\n"
            "| nova     | compute      | Available |\n"
            "+----------+--------------+-----------+\n\n\n"
            "-----------------------------------------------------------------"
            "---------------\nPlatform docker:\n"
            "-----------------------------------------------------------------"
            "---------------\n\n"
            "Error while checking admin credentials:\n"
            "\tProviderError: No money - no funny!\n\n\n"
            "-----------------------------------------------------------------"
            "---------------\nPlatform something #1:\n"
            "-----------------------------------------------------------------"
            "---------------\n\nAvailable services:\n"
            "+---------+--------------+-----------+---------+--------------+\n"
            "| Service | Service Type | Status    | Version | Description  |\n"
            "+---------+--------------+-----------+---------+--------------+\n"
            "| foo     | bar          | Available | 777     |              |\n"
            "| xxx     | yyy          | Failed    | 777     | Fake service |\n"
            "+---------+--------------+-----------+---------+--------------+\n"
            "\n\n-------------------------------------------------------------"
            "-------------------\nPlatform something #2:\n"
            "-----------------------------------------------------------------"
            "---------------\n\n"
            "Error while checking users credentials:\n"
            "\tProviderError: No money - no funny!",
            mock_stdout.getvalue().strip())

    @mock.patch("rally.cli.commands.deployment.logging.is_debug",
                return_value=True)
    @mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_deployment_check_is_debug_turned_on(self, mock_stdout,
                                                 mock_is_debug):
        deployment_uuid = "some"
        self.fake_api.deployment.check.return_value = {
            "openstack": [{"services": [], "admin_error": {
                "etype": "KeystoneError",
                "msg": "connection refused",
                "trace": "file1\n\tline1\n\n"
                         "KeystoneError: connection refused"}}]
        }

        self.assertEqual(
            1, self.deployment.check(self.fake_api, deployment_uuid))

        self.assertEqual(
            "-----------------------------------------------------------------"
            "---------------\nPlatform openstack:\n"
            "-----------------------------------------------------------------"
            "---------------\n\n"
            "Error while checking admin credentials:\n"
            "file1\n\tline1\n\n"
            "KeystoneError: connection refused",
            mock_stdout.getvalue().strip())
