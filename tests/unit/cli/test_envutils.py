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
from six import moves

from rally.cli import envutils
from rally import exceptions
from tests.unit import test


class EnvUtilsTestCase(test.TestCase):

    def test_default_from_global(self):

        @envutils.default_from_global("test_arg_name",
                                      "test_env_name",
                                      "test_missing_arg")
        def test_function(test_arg_name=None):
            pass

        with mock.patch("sys.stdout",
                        new_callable=moves.StringIO) as mock_stdout:
            test_function()
            self.assertEqual(mock_stdout.getvalue(),
                             "Missing argument: --test_missing_arg\n")

    @mock.patch.dict(os.environ,
                     values={envutils.ENV_DEPLOYMENT: "my_deployment_id"},
                     clear=True)
    def test_get_deployment_id_in_env(self):
        deployment_id = envutils.get_global(envutils.ENV_DEPLOYMENT)
        self.assertEqual("my_deployment_id", deployment_id)

    @mock.patch.dict(os.environ, values={}, clear=True)
    @mock.patch("rally.cli.envutils.fileutils.load_env_file")
    def test_get_deployment_id_with_exception(self, mock_load_env_file):
        self.assertRaises(exceptions.InvalidArgumentsException,
                          envutils.get_global, envutils.ENV_DEPLOYMENT, True)
        mock_load_env_file.assert_called_once_with(os.path.expanduser(
            "~/.rally/globals"))

    @mock.patch.dict(os.environ, values={}, clear=True)
    @mock.patch("rally.cli.envutils.fileutils.load_env_file")
    def test_get_deployment_id_with_none(self, mock_load_env_file):
        self.assertIsNone(envutils.get_global(envutils.ENV_DEPLOYMENT))
        mock_load_env_file.assert_called_once_with(os.path.expanduser(
            "~/.rally/globals"))

    @mock.patch.dict(os.environ, values={envutils.ENV_TASK: "my_task_id"},
                     clear=True)
    def test_get_task_id_in_env(self):
        self.assertEqual("my_task_id", envutils.get_global(envutils.ENV_TASK))

    @mock.patch.dict(os.environ, values={}, clear=True)
    @mock.patch("rally.cli.envutils.fileutils.load_env_file")
    def test_get_task_id_with_exception(self, mock_load_env_file):
        self.assertRaises(exceptions.InvalidArgumentsException,
                          envutils.get_global, envutils.ENV_TASK, True)
        mock_load_env_file.assert_called_once_with(os.path.expanduser(
            "~/.rally/globals"))

    @mock.patch.dict(os.environ, values={}, clear=True)
    @mock.patch("rally.cli.envutils.fileutils.load_env_file")
    def test_get_task_id_with_none(self, mock_load_env_file):
        self.assertIsNone(envutils.get_global("RALLY_TASK"))
        mock_load_env_file.assert_called_once_with(os.path.expanduser(
            "~/.rally/globals"))

    @mock.patch.dict(os.environ,
                     values={envutils.ENV_DEPLOYMENT: "test_deployment_id"},
                     clear=True)
    @mock.patch("os.path.exists")
    @mock.patch("rally.cli.envutils.fileutils.update_env_file",
                return_value=True)
    def test_clear_global(self, mock_update_env_file, mock_path_exists):
        envutils.clear_global(envutils.ENV_DEPLOYMENT)
        mock_update_env_file.assert_called_once_with(os.path.expanduser(
            "~/.rally/globals"), envutils.ENV_DEPLOYMENT, "\n")
        self.assertEqual(os.environ, {})

    @mock.patch.dict(os.environ,
                     values={envutils.ENV_DEPLOYMENT: "test_deployment_id",
                             envutils.ENV_TASK: "test_task_id"},
                     clear=True)
    @mock.patch("os.path.exists")
    @mock.patch("rally.cli.envutils.fileutils.update_env_file",
                return_value=True)
    def test_clear_env(self, mock_update_env_file, mock_path_exists):
        envutils.clear_env()
        self.assertEqual(os.environ, {})

    @mock.patch.dict(os.environ, {"OS_AUTH_URL": "fake_auth_url",
                                  "OS_USERNAME": "fake_username",
                                  "OS_PASSWORD": "fake_password",
                                  "OS_TENANT_NAME": "fake_tenant_name",
                                  "OS_REGION_NAME": "fake_region_name",
                                  "OS_ENDPOINT_TYPE": "fake_endpoint_typeURL",
                                  "OS_ENDPOINT": "fake_endpoint",
                                  "OS_INSECURE": "True",
                                  "OS_CACERT": "fake_cacert"})
    def test_get_creds_from_env_vars_keystone_v2(self):
        expected_creds = {
            "auth_url": "fake_auth_url",
            "admin": {
                "username": "fake_username",
                "password": "fake_password",
                "tenant_name": "fake_tenant_name"
            },
            "endpoint_type": "fake_endpoint_type",
            "endpoint": "fake_endpoint",
            "region_name": "fake_region_name",
            "https_cacert": "fake_cacert",
            "https_insecure": True
        }
        creds = envutils.get_creds_from_env_vars()
        self.assertEqual(expected_creds, creds)

    @mock.patch.dict(os.environ, {"OS_AUTH_URL": "fake_auth_url",
                                  "OS_USERNAME": "fake_username",
                                  "OS_PASSWORD": "fake_password",
                                  "OS_TENANT_NAME": "fake_tenant_name",
                                  "OS_REGION_NAME": "fake_region_name",
                                  "OS_ENDPOINT_TYPE": "fake_endpoint_typeURL",
                                  "OS_ENDPOINT": "fake_endpoint",
                                  "OS_INSECURE": "True",
                                  "OS_PROJECT_DOMAIN_NAME": "fake_pdn",
                                  "OS_USER_DOMAIN_NAME": "fake_udn",
                                  "OS_CACERT": "fake_cacert"})
    def test_get_creds_from_env_vars_keystone_v3(self):
        expected_creds = {
            "auth_url": "fake_auth_url",
            "admin": {
                "username": "fake_username",
                "password": "fake_password",
                "user_domain_name": "fake_udn",
                "project_domain_name": "fake_pdn",
                "project_name": "fake_tenant_name"
            },
            "endpoint_type": "fake_endpoint_type",
            "endpoint": "fake_endpoint",
            "region_name": "fake_region_name",
            "https_cacert": "fake_cacert",
            "https_insecure": True
        }
        creds = envutils.get_creds_from_env_vars()
        self.assertEqual(expected_creds, creds)

    @mock.patch.dict(os.environ, {"OS_AUTH_URL": "fake_auth_url",
                                  "OS_PASSWORD": "fake_password",
                                  "OS_REGION_NAME": "fake_region_name",
                                  "OS_ENDPOINT": "fake_endpoint",
                                  "OS_INSECURE": "True",
                                  "OS_CACERT": "fake_cacert"})
    def test_get_creds_from_env_vars_when_required_vars_missing(self):
        if "OS_USERNAME" in os.environ:
            del os.environ["OS_USERNAME"]
        self.assertRaises(exceptions.ValidationError,
                          envutils.get_creds_from_env_vars)

    @mock.patch.dict(os.environ, {"OS_TENANT_NAME": "fake_tenant_name"},
                     clear=True)
    def test_get_project_name_from_env_when_tenant_name(self):
        project_name = envutils.get_project_name_from_env()
        self.assertEqual("fake_tenant_name", project_name)

    @mock.patch.dict(os.environ, {"OS_PROJECT_NAME": "fake_project_name"},
                     clear=True)
    def test_get_project_name_from_env_when_project_name(self):
        project_name = envutils.get_project_name_from_env()
        self.assertEqual("fake_project_name", project_name)

    @mock.patch.dict(os.environ, {"OS_TENANT_NAME": "fake_tenant_name",
                                  "OS_PROJECT_NAME": "fake_project_name"})
    def test_get_project_name_from_env_when_both(self):
        project_name = envutils.get_project_name_from_env()
        self.assertEqual("fake_project_name", project_name)

    @mock.patch.dict(os.environ, values={}, clear=True)
    def test_get_project_name_from_env_when_neither(self):
        self.assertRaises(exceptions.ValidationError,
                          envutils.get_project_name_from_env)

    @mock.patch.dict(os.environ, {"OS_ENDPOINT_TYPE": "fake_endpoint_typeURL"},
                     clear=True)
    def test_get_endpoint_type_from_env_when_endpoint_type(self):
        endpoint_type = envutils.get_endpoint_type_from_env()
        self.assertEqual("fake_endpoint_type", endpoint_type)

    @mock.patch.dict(os.environ, {"OS_INTERFACE": "fake_interface"},
                     clear=True)
    def test_get_endpoint_type_from_env_when_interface(self):
        endpoint_type = envutils.get_endpoint_type_from_env()
        self.assertEqual("fake_interface", endpoint_type)

    @mock.patch.dict(os.environ, {"OS_ENDPOINT_TYPE": "fake_endpoint_typeURL",
                                  "OS_INTERFACE": "fake_interface"})
    def test_get_endpoint_type_from_env_when_both(self):
        endpoint_type = envutils.get_endpoint_type_from_env()
        self.assertEqual("fake_endpoint_type", endpoint_type)

    @mock.patch.dict(os.environ, values={}, clear=True)
    def test_get_endpoint_type_from_env_when_neither(self):
        endpoint_type = envutils.get_endpoint_type_from_env()
        self.assertIsNone(endpoint_type)
