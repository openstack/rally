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
import os
import sys
import tempfile
from unittest import mock

from rally.common import db
from rally.env import env_mgr
from tests.unit.cli import test


# a deployment dict as the API returns it, for the create tests that stub the
# deployment-provisioning step
CREATED = {"uuid": "uuid", "created_at": "2016-01-01T00:00:00",
           "name": "fake_deploy", "status": "finished", "credentials": {}}


class DeploymentCommandsTestCase(test.CLITestCase):

    def _create_deployment(self, name="Some Deploy", spec=None):
        """Insert a real deployment (environment) row and return its dict."""
        db.env_create(name=name, status=env_mgr.STATUS.READY, description="",
                      extras={}, config={}, spec=spec or {}, platforms=[])
        return db.env_get(name)

    def test_deprecation_warning(self):
        # running a subcommand warns that ``deployment`` is deprecated...
        result = self.invoke(["deployment", "list"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("deprecated", result.stderr)

        # ...but merely rendering help does not (bootstrap flags --help via
        # sys.argv)
        with mock.patch.object(sys, "argv", ["rally", "deployment", "--help"]):
            result = self.invoke(["deployment", "--help"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertNotIn("deprecated", result.stderr)

    @mock.patch("rally.api._Deployment.create")
    def test_create(self, mock_create):
        mock_create.return_value = CREATED
        with tempfile.NamedTemporaryFile("w", suffix=".json") as tf:
            tf.write('{"some": "json"}')
            tf.flush()
            result = self.invoke([
                "deployment", "create", "--name", "fake_deploy",
                "--filename", tf.name])

        self.assertEqual(0, result.exit_code, result.output)
        mock_create.assert_called_once_with(
            config={"some": "json"}, name="fake_deploy")

    @mock.patch("rally.api._Deployment.create")
    def test_create_empty(self, mock_create):
        mock_create.return_value = CREATED

        result = self.invoke([
            "deployment", "create", "--name", "fake_deploy"])

        self.assertEqual(0, result.exit_code, result.output)
        mock_create.assert_called_once_with(config={}, name="fake_deploy")

    @mock.patch("rally.api._Deployment.create")
    @mock.patch("rally.env.env_mgr.EnvManager.create_spec_from_sys_environ",
                return_value={"spec": {"auth_url": "http://fake"}})
    def test_create_fromenv(self, mock_create_spec_from_sys_environ,
                            mock_create):
        mock_create.return_value = CREATED

        result = self.invoke([
            "deployment", "create", "--name", "from_env", "--fromenv"])

        self.assertEqual(0, result.exit_code, result.output)
        mock_create.assert_called_once_with(
            config={"auth_url": "http://fake"}, name="from_env")

    @mock.patch("rally.api._Deployment.create")
    def test_create_and_use(self, mock_create):
        mock_create.return_value = CREATED
        with tempfile.NamedTemporaryFile("w", suffix=".json") as tf:
            tf.write('{"uuid": "uuid"}')
            tf.flush()
            result = self.invoke([
                "deployment", "create", "--name", "fake_deploy",
                "--filename", tf.name])

        self.assertEqual(0, result.exit_code, result.output)
        mock_create.assert_called_once_with(
            config={"uuid": "uuid"}, name="fake_deploy")
        # the created deployment is listed and set as the default
        self.assertIn("uuid", result.output)
        self.assertIn("Using deployment: uuid", result.output)

    def test_recreate(self):
        # recreate is temporarily disabled in the API and raises for any input
        for args in ([], ["--filename", "my.json"]):
            with self.subTest(args=args):
                extra = []
                if args:
                    tf = tempfile.NamedTemporaryFile("w", suffix=".json")
                    self.addCleanup(tf.close)
                    tf.write('{"some": "json"}')
                    tf.flush()
                    extra = ["--filename", tf.name]
                result = self.invoke(
                    ["deployment", "recreate", "some-uuid", *extra])
                self.assertNotEqual(0, result.exit_code)
                self.assertIn("temporary disabled", result.output)

    @mock.patch("rally.api._Deployment.destroy")
    def test_destroy(self, mock_destroy):
        deployment = self._create_deployment()

        result = self.invoke(["deployment", "destroy", deployment["uuid"]])

        self.assertEqual(0, result.exit_code, result.output)
        mock_destroy.assert_called_once_with(deployment=deployment["uuid"])

    def test_list(self):
        deployment = self._create_deployment()

        # without RALLY_DEPLOYMENT the row is not marked active; with it the
        # matching row is flagged with "*"
        for env, active in (({}, False),
                            ({"RALLY_DEPLOYMENT": deployment["uuid"]}, True)):
            with self.subTest(active=active):
                result = self.invoke(["deployment", "list"], env=env)
                self.assertEqual(0, result.exit_code, result.output)
                self.assertIn(deployment["uuid"], result.output)
                self.assertIn("Some Deploy", result.output)
                self.assertEqual(active, "*" in result.output)

    def test_config(self):
        deployment = self._create_deployment(spec={"foo": "bar"})

        result = self.invoke(["deployment", "config", deployment["uuid"]])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("foo", result.output)
        self.assertIn("bar", result.output)

    @mock.patch("rally.api._Deployment.get")
    def test_show(self, mock_get):
        password = "S3cr3t-P@ssw0rd!"
        mock_get.return_value = {
            "credentials": {"openstack": [{
                "admin": {"auth_url": "http://localhost:5000/v3",
                          "username": "admin", "password": password,
                          "tenant_name": "demo", "region_name": "RegionOne",
                          "endpoint_type": "internal"},
                "users": []}]}}

        result = self.invoke(["deployment", "show", "some-uuid"])

        self.assertEqual(0, result.exit_code, result.output)
        # the password never leaks -- it is replaced by "***"
        self.assertNotIn(password, result.output)
        self.assertEqual(
            "+--------------------------+----------+----------+"
            "-------------+-------------+---------------+\n"
            "| auth_url                 | username | password |"
            " tenant_name | region_name | endpoint_type |\n"
            "+--------------------------+----------+----------+"
            "-------------+-------------+---------------+\n"
            "| http://localhost:5000/v3 | admin    | ***      |"
            " demo        | RegionOne   | internal      |\n"
            "+--------------------------+----------+----------+"
            "-------------+-------------+---------------+\n",
            result.stdout)

    @mock.patch("rally.api._Deployment.get")
    def test_use(self, mock_get):
        deployment_id = "593b683c-4b16-4b2b-a56b-e162bd60f10b"
        v2 = {"auth_url": "fake_auth_url", "username": "fake_username",
              "password": "fake_password", "tenant_name": "fake_tenant_name",
              "endpoint": "fake_endpoint", "region_name": None}
        v3 = dict(v2, auth_url="http://localhost:5000/v3",
                  user_domain_name="fake_user_domain",
                  project_domain_name="fake_project_domain")

        for admin in (v2, v3):
            with self.subTest(auth_url=admin["auth_url"]):
                mock_get.return_value = {
                    "uuid": deployment_id,
                    "credentials": {"openstack": [{"admin": admin}]}}

                result = self.invoke(["deployment", "use", deployment_id])

                self.assertEqual(0, result.exit_code, result.output)
                self.assertIn("Using deployment: %s" % deployment_id,
                              result.output)
                openrc = os.path.expanduser(
                    "~/.rally/openrc-%s" % deployment_id)
                with open(openrc) as f:
                    content = f.read()
                self.assertIn("export OS_AUTH_URL='%s'\n" % admin["auth_url"],
                              content)
                self.assertIn("export OS_USERNAME='fake_username'\n", content)
                if "user_domain_name" in admin:
                    self.assertIn(
                        "export OS_IDENTITY_API_VERSION=3\n", content)

    @mock.patch("rally.api._Deployment.get")
    def test_use_by_name(self, mock_get):
        fake_credentials = {"admin": {"auth_url": "url", "username": "u",
                                      "password": "p", "tenant_name": "t"},
                            "users": []}
        mock_get.return_value = {
            "uuid": "fake_uuid",
            "credentials": {"openstack": [fake_credentials]}}

        result = self.invoke(["deployment", "use", "fake_name"])

        self.assertEqual(0, result.exit_code, result.output)
        mock_get.assert_called_once_with(deployment="fake_name")
        self.assertIn("Using deployment: fake_uuid", result.output)

    def test_deployment_not_found(self):
        deployment_id = "e87e4dca-b515-4477-888d-5f6103f13b42"

        result = self.invoke(["deployment", "use", deployment_id])

        self.assertEqual(1, result.exit_code)
        self.assertIn("is not found", result.output)

    @mock.patch("rally.api._Deployment.check")
    def test_deployment_check(self, mock_check):
        # OrderedDict is used to predict the order of platforms in output
        mock_check.return_value = collections.OrderedDict([
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

        result = self.invoke(["deployment", "check", "some-uuid"])

        self.assertEqual(1, result.exit_code)
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
            result.stdout.strip())

    @mock.patch("rally.cli.commands.deployment.logging.is_debug",
                return_value=True)
    @mock.patch("rally.api._Deployment.check")
    def test_deployment_check_is_debug_turned_on(self, mock_check,
                                                 mock_is_debug):
        mock_check.return_value = {
            "openstack": [{"services": [], "admin_error": {
                "etype": "KeystoneError",
                "msg": "connection refused",
                "trace": "file1\n\tline1\n\n"
                         "KeystoneError: connection refused"}}]
        }

        result = self.invoke(["deployment", "check", "some-uuid"])

        self.assertEqual(1, result.exit_code)
        self.assertEqual(
            "-----------------------------------------------------------------"
            "---------------\nPlatform openstack:\n"
            "-----------------------------------------------------------------"
            "---------------\n\n"
            "Error while checking admin credentials:\n"
            "file1\n\tline1\n\n"
            "KeystoneError: connection refused",
            result.stdout.strip())
