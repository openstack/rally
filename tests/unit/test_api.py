# Copyright 2013: Mirantis Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
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

""" Test for api. """

import os

import ddt
import jsonschema
from keystoneclient import exceptions as keystone_exceptions
import mock

from rally import api
from rally.common import objects
from rally import consts
from rally.deployment import engine
from rally import exceptions
from tests.unit import fakes
from tests.unit import test


FAKE_DEPLOYMENT_CONFIG = {
    # TODO(akscram): A fake engine is more suitable for that.
    "type": "ExistingCloud",
    "auth_url": "http://example.net:5000/v2.0/",
    "admin": {
        "username": "admin",
        "password": "myadminpass",
        "tenant_name": "demo",
        "domain_name": None,
        "project_domain_name": "Default",
        "user_domain_name": "Default",
        "admin_domain_name": "Default"
    },
    "region_name": "RegionOne",
    "endpoint_type": consts.EndpointType.INTERNAL,
}


@ddt.ddt
class TaskAPITestCase(test.TestCase):
    def setUp(self):
        super(TaskAPITestCase, self).setUp()
        self.task_uuid = "b0d9cd6c-2c94-4417-a238-35c7019d0257"
        self.task = {
            "uuid": self.task_uuid,
        }

    @mock.patch("rally.api.objects.Task")
    @mock.patch("rally.api.objects.Deployment.get",
                return_value=fakes.FakeDeployment(uuid="deployment_uuid",
                                                  admin=mock.MagicMock(),
                                                  users=[]))
    @mock.patch("rally.api.engine.TaskEngine")
    def test_validate(
            self, mock_task_engine, mock_deployment_get, mock_task):
        api.Task.validate(mock_deployment_get.return_value["uuid"], "config")

        mock_task_engine.assert_has_calls([
            mock.call("config", mock_task.return_value,
                      admin=mock_deployment_get.return_value["admin"],
                      users=[]),
            mock.call().validate()
        ])

        mock_task.assert_called_once_with(
            temporary=True,
            deployment_uuid=mock_deployment_get.return_value["uuid"])
        mock_deployment_get.assert_called_once_with(
            mock_deployment_get.return_value["uuid"])

    @mock.patch("rally.api.objects.Task")
    @mock.patch("rally.api.objects.Deployment",
                return_value=fakes.FakeDeployment(uuid="deployment_uuid",
                                                  admin=mock.MagicMock(),
                                                  users=[]))
    @mock.patch("rally.api.engine.TaskEngine")
    def test_validate_engine_exception(self, mock_task_engine,
                                       mock_deployment, mock_task):

        excpt = exceptions.InvalidTaskException()
        mock_task_engine.return_value.validate.side_effect = excpt
        self.assertRaises(exceptions.InvalidTaskException, api.Task.validate,
                          mock_deployment.return_value["uuid"], "config")

    def test_render_template(self):
        self.assertEqual(
            "3 = 3",
            api.Task.render_template("{{a + b}} = {{c}}", a=1, b=2, c=3))

    def test_render_template_default_values(self):
        template = "{% set a = a or 1 %}{{a + b}} = {{c}}"

        self.assertEqual("3 = 3", api.Task.render_template(template, b=2, c=3))

        self.assertEqual(
            "5 = 5", api.Task.render_template(template, a=2, b=3, c=5))

    def test_render_template_default_filter(self):
        template = "{{ c | default(3) }}"

        self.assertEqual("3", api.Task.render_template(template))

        self.assertEqual("5", api.Task.render_template(template, c=5))

    def test_render_template_builtin(self):
        template = "{% for i in range(4) %}{{i}}{% endfor %}"
        self.assertEqual("0123", api.Task.render_template(template))

    def test_render_template_missing_args(self):
        self.assertRaises(TypeError, api.Task.render_template, "{{a}}")

    def test_render_template_include_other_template(self):
        other_template_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "samples/tasks/scenarios/nova/boot.json")
        template = "{%% include \"%s\" %%}" % os.path.basename(
            other_template_path)
        with open(other_template_path) as f:
            other_template = f.read()
        expect = api.Task.render_template(other_template)
        actual = api.Task.render_template(template,
                                          os.path.dirname(other_template_path))
        self.assertEqual(expect, actual)

    def test_render_template_min(self):
        template = "{{ min(1, 2)}}"
        self.assertEqual("1", api.Task.render_template(template))

    def test_render_template_max(self):
        template = "{{ max(1, 2)}}"
        self.assertEqual("2", api.Task.render_template(template))

    def test_render_template_ceil(self):
        template = "{{ ceil(2.2)}}"
        self.assertEqual("3", api.Task.render_template(template))

    def test_render_template_round(self):
        template = "{{ round(2.2)}}"
        self.assertEqual("2", api.Task.render_template(template))

    @mock.patch("rally.common.objects.Deployment.get",
                return_value={"uuid": "b0d9cd6c-2c94-4417-a238-35c7019d0257"})
    @mock.patch("rally.common.objects.Task")
    def test_create(self, mock_task, mock_deployment_get):
        tag = "a"
        api.Task.create(mock_deployment_get.return_value["uuid"], tag)
        mock_task.assert_called_once_with(
            deployment_uuid=mock_deployment_get.return_value["uuid"], tag=tag)

    @mock.patch("rally.api.objects.Task",
                return_value=fakes.FakeTask(uuid="some_uuid"))
    @mock.patch("rally.api.objects.Deployment.get",
                return_value=fakes.FakeDeployment(uuid="deployment_uuid",
                                                  admin=mock.MagicMock(),
                                                  users=[]))
    @mock.patch("rally.api.engine.TaskEngine")
    def test_start(self, mock_task_engine, mock_deployment_get,
                   mock_task):
        api.Task.start(mock_deployment_get.return_value["uuid"], "config")

        mock_task_engine.assert_has_calls([
            mock.call("config", mock_task.return_value,
                      admin=mock_deployment_get.return_value["admin"],
                      users=[], abort_on_sla_failure=False),
            mock.call().run(),
        ])

        mock_task.assert_called_once_with(
            deployment_uuid=mock_deployment_get.return_value["uuid"])

        mock_deployment_get.assert_called_once_with(
            mock_deployment_get.return_value["uuid"])

    @mock.patch("rally.api.objects.Task",
                return_value=fakes.FakeTask(uuid="some_uuid", task={},
                                            temporary=True))
    @mock.patch("rally.api.objects.Deployment.get",
                return_value=fakes.FakeDeployment(uuid="deployment_uuid",
                                                  admin=mock.MagicMock(),
                                                  users=[]))
    def test_start_temporary_task(self, mock_deployment_get,
                                  mock_task):

        self.assertRaises(ValueError, api.Task.start,
                          mock_deployment_get.return_value["uuid"], "config")

    @mock.patch("rally.api.objects.Task")
    @mock.patch("rally.api.objects.Deployment.get")
    @mock.patch("rally.api.engine.TaskEngine")
    def test_start_exception(self, mock_task_engine, mock_deployment_get,
                             mock_task):
        mock_task.return_value.is_temporary = False
        mock_task_engine.return_value.run.side_effect = TypeError
        self.assertRaises(TypeError, api.Task.start, "deployment_uuid",
                          "config")
        mock_deployment_get().update_status.assert_called_once_with(
            consts.DeployStatus.DEPLOY_INCONSISTENT)

    @ddt.data(True, False)
    @mock.patch("rally.api.time")
    @mock.patch("rally.api.objects.Task")
    def test_abort_sync(self, soft, mock_task, mock_time):
        mock_task.get_status.side_effect = (
            consts.TaskStatus.INIT,
            consts.TaskStatus.VERIFYING,
            consts.TaskStatus.RUNNING,
            consts.TaskStatus.ABORTING,
            consts.TaskStatus.SOFT_ABORTING,
            consts.TaskStatus.ABORTED)

        some_uuid = "ca441749-0eb9-4fcc-b2f6-76d314c55404"

        api.Task.abort(some_uuid, soft=soft, async=False)

        mock_task.get.assert_called_once_with(some_uuid)
        mock_task.get.return_value.abort.assert_called_once_with(soft=soft)
        self.assertEqual([mock.call(some_uuid)] * 6,
                         mock_task.get_status.call_args_list)
        self.assertTrue(mock_time.sleep.called)

    @ddt.data(True, False)
    @mock.patch("rally.api.time")
    @mock.patch("rally.api.objects.Task")
    def test_abort_async(self, soft, mock_task, mock_time):
        some_uuid = "133695fb-400d-4988-859c-30bfaa0488ce"

        api.Task.abort(some_uuid, soft=soft, async=True)

        mock_task.get.assert_called_once_with(some_uuid)
        mock_task.get.return_value.abort.assert_called_once_with(soft=soft)
        self.assertFalse(mock_task.get_status.called)
        self.assertFalse(mock_time.sleep.called)

    @mock.patch("rally.common.objects.task.db.task_delete")
    def test_delete(self, mock_task_delete):
        api.Task.delete(self.task_uuid)
        mock_task_delete.assert_called_once_with(
            self.task_uuid,
            status=consts.TaskStatus.FINISHED)

    @mock.patch("rally.common.objects.task.db.task_delete")
    def test_delete_force(self, mock_task_delete):
        api.Task.delete(self.task_uuid, force=True)
        mock_task_delete.assert_called_once_with(
            self.task_uuid, status=None)

    @mock.patch("rally.api.objects.Task")
    def test_get_detailed(self, mock_task):
        mock_task.get_detailed.return_value = "detailed_task_data"
        self.assertEqual("detailed_task_data",
                         api.Task.get_detailed("task_uuid"))
        mock_task.get_detailed.assert_called_once_with("task_uuid")

    @mock.patch("rally.api.objects.Task")
    def test_get_detailed_with_extended_results(self, mock_task):
        mock_task.get_detailed.return_value = (("uuid", "foo_uuid"),
                                               ("results", "raw_results"))
        mock_task.extend_results.return_value = "extended_results"
        self.assertEqual({"uuid": "foo_uuid", "results": "extended_results"},
                         api.Task.get_detailed("foo_uuid",
                                               extended_results=True))
        mock_task.get_detailed.assert_called_once_with("foo_uuid")
        mock_task.extend_results.assert_called_once_with("raw_results")


class BaseDeploymentTestCase(test.TestCase):
    def setUp(self):
        super(BaseDeploymentTestCase, self).setUp()
        self.deployment_config = FAKE_DEPLOYMENT_CONFIG
        self.deployment_uuid = "599bdf1d-fe77-461a-a810-d59b1490f4e3"
        admin_credential = FAKE_DEPLOYMENT_CONFIG.copy()
        admin_credential.pop("type")
        admin_credential["endpoint"] = None
        admin_credential.update(admin_credential.pop("admin"))
        admin_credential["permission"] = consts.EndpointPermission.ADMIN
        admin_credential["https_insecure"] = False
        admin_credential["https_cacert"] = None
        self.credentials = {"admin": admin_credential, "users": []}
        self.deployment = {
            "uuid": self.deployment_uuid,
            "name": "fake_name",
            "config": self.deployment_config,
            "admin": self.credentials["admin"],
            "users": []
        }


class DeploymentAPITestCase(BaseDeploymentTestCase):
    @mock.patch("rally.common.objects.deploy.db.deployment_update")
    @mock.patch("rally.common.objects.deploy.db.deployment_create")
    @mock.patch("rally.deployment.engine.Engine.validate")
    def test_create(self, mock_engine_validate,
                    mock_deployment_create, mock_deployment_update):
        mock_deployment_create.return_value = self.deployment
        mock_deployment_update.return_value = self.deployment
        api.Deployment.create(self.deployment_config, "fake_deployment")
        mock_deployment_create.assert_called_once_with({
            "name": "fake_deployment",
            "config": self.deployment_config,
        })
        mock_engine_validate.assert_called_with()
        mock_deployment_update.assert_has_calls([
            mock.call(self.deployment_uuid, self.credentials)
        ])

    @mock.patch("rally.common.objects.deploy.db.deployment_update")
    @mock.patch("rally.common.objects.deploy.db.deployment_create")
    @mock.patch("rally.deployment.engine.Engine.validate",
                side_effect=jsonschema.ValidationError("ValidationError"))
    def test_create_validation_error(
            self, mock_engine_validate, mock_deployment_create,
            mock_deployment_update):
        mock_deployment_create.return_value = self.deployment
        self.assertRaises(jsonschema.ValidationError,
                          api.Deployment.create,
                          self.deployment_config, "fake_deployment")
        mock_deployment_update.assert_called_once_with(
            self.deployment_uuid,
            {"status": consts.DeployStatus.DEPLOY_FAILED})

    @mock.patch("rally.api.LOG")
    @mock.patch("rally.common.objects.deploy.db.deployment_create",
                side_effect=exceptions.DeploymentNameExists(
                    deployment="fake_deploy"))
    def test_create_duplication_error(self, mock_deployment_create, mock_log):
        self.assertRaises(exceptions.DeploymentNameExists,
                          api.Deployment.create, self.deployment_config,
                          "fake_deployment")

    @mock.patch("rally.common.objects.deploy.db.deployment_delete")
    @mock.patch("rally.common.objects.deploy.db.deployment_update")
    @mock.patch("rally.common.objects.deploy.db.deployment_get")
    def test_destroy(self, mock_deployment_get,
                     mock_deployment_update, mock_deployment_delete):
        mock_deployment_get.return_value = self.deployment
        mock_deployment_update.return_value = self.deployment
        api.Deployment.destroy(self.deployment_uuid)
        mock_deployment_get.assert_called_once_with(self.deployment_uuid)
        mock_deployment_delete.assert_called_once_with(self.deployment_uuid)

    @mock.patch("rally.common.objects.deploy.db.deployment_update")
    @mock.patch("rally.common.objects.deploy.db.deployment_get")
    def test_recreate(self, mock_deployment_get, mock_deployment_update):
        mock_deployment_get.return_value = self.deployment
        mock_deployment_update.return_value = self.deployment
        api.Deployment.recreate(self.deployment_uuid)
        mock_deployment_get.assert_called_once_with(self.deployment_uuid)
        mock_deployment_update.assert_has_calls([
            mock.call(self.deployment_uuid, self.credentials)
        ])

    @mock.patch("rally.common.objects.deploy.db.deployment_get")
    def test_get(self, mock_deployment_get):
        deployment_id = "aaaa-bbbb-cccc-dddd"
        mock_deployment_get.return_value = self.deployment
        ret = api.Deployment.get(deployment_id)
        for key in self.deployment:
            self.assertEqual(ret[key], self.deployment[key])

    @mock.patch("rally.common.objects.Deployment.list")
    def test_list(self, mock_deployment_list):
        mock_deployment_list.return_value = self.deployment
        ret = api.Deployment.list()
        for key in self.deployment:
            self.assertEqual(ret[key], self.deployment[key])

    @mock.patch("rally.osclients.Clients.services")
    @mock.patch("rally.osclients.Keystone.create_client")
    def test_deployment_check(self, mock_keystone_create_client,
                              mock_clients_services):
        sample_credential = objects.Credential("http://192.168.1.1:5000/v2.0/",
                                               "admin",
                                               "adminpass").to_dict()
        deployment = {"admin": sample_credential,
                      "users": [sample_credential]}
        api.Deployment.check(deployment)
        mock_keystone_create_client.assert_called_with()
        mock_clients_services.assert_called_once_with()

    def test_deployment_check_raise(self):
        sample_credential = objects.Credential("http://192.168.1.1:5000/v2.0/",
                                               "admin",
                                               "adminpass").to_dict()
        sample_credential["not-exist-key"] = "error"
        deployment = {"admin": sample_credential}
        self.assertRaises(TypeError, api.Deployment.check, deployment)

    @mock.patch("rally.osclients.Clients.services")
    def test_deployment_check_connect_failed(self, mock_clients_services):
        sample_credential = objects.Credential("http://192.168.1.1:5000/v2.0/",
                                               "admin",
                                               "adminpass").to_dict()
        deployment = {"admin": sample_credential}
        refused = keystone_exceptions.ConnectionRefused()
        mock_clients_services.side_effect = refused
        self.assertRaises(
            keystone_exceptions.ConnectionRefused,
            api.Deployment.check, deployment)


class VerificationAPITestCase(BaseDeploymentTestCase):
    def setUp(self):
        super(VerificationAPITestCase, self).setUp()
        self.tempest = mock.Mock()

    @mock.patch("os.path.exists", return_value=True)
    @mock.patch("rally.common.objects.Deployment.get")
    @mock.patch("rally.api.objects.Verification")
    @mock.patch("rally.verification.tempest.tempest.Tempest")
    def test_verify(self, mock_tempest, mock_verification,
                    mock_deployment_get, mock_exists):
        mock_deployment_get.return_value = {"uuid": self.deployment_uuid}
        mock_tempest.return_value = self.tempest
        api.Verification.verify(
            self.deployment_uuid, set_name="smoke",
            regex=None, tests_file=None, tempest_config=None)

        self.tempest.verify.assert_called_once_with(
            set_name="smoke", regex=None, tests_file=None,
            tests_file_to_skip=None, expected_failures=None,
            concur=0, failing=False)

    @mock.patch("os.path.exists", return_value=True)
    @mock.patch("rally.api.objects.Deployment.get")
    @mock.patch("rally.api.objects.Verification")
    @mock.patch("rally.verification.tempest.tempest.Tempest")
    def test_verify_tests_file_specified(self, mock_tempest, mock_verification,
                                         mock_deployment_get, mock_exists):
        mock_deployment_get.return_value = {"uuid": self.deployment_uuid}
        mock_tempest.return_value = self.tempest
        tests_file = "/path/to/tests/file"
        api.Verification.verify(
            self.deployment_uuid, set_name="", regex=None,
            tests_file=tests_file, tempest_config=None, failing=False)

        self.tempest.verify.assert_called_once_with(
            set_name="", regex=None, tests_file=tests_file,
            tests_file_to_skip=None, expected_failures=None,
            concur=0, failing=False)

    @mock.patch("rally.api.objects.Deployment.get")
    @mock.patch("rally.api.objects.Verification")
    def test_verify_no_tempest_tree_exists(self, mock_verification,
                                           mock_deployment_get):
        mock_deployment_get.return_value = {"uuid": self.deployment_uuid}
        self.assertRaises(
            exceptions.NotFoundException, api.Verification.verify,
            self.deployment_uuid, set_name="smoke", regex=None,
            tests_file=None, tempest_config=None)

    @mock.patch("rally.common.objects.Deployment.get")
    @mock.patch("rally.api.objects.Verification")
    @mock.patch("rally.verification.tempest.tempest.Tempest")
    def test_import_results(self, mock_tempest, mock_verification,
                            mock_deployment_get):
        mock_deployment_get.return_value = {"uuid": self.deployment_uuid}

        mock_tempest.return_value = self.tempest
        self.tempest.is_installed.return_value = True
        api.Verification.import_results(
            self.deployment_uuid, "smoke", "log_file")

        self.tempest.import_results.assert_called_once_with(
            set_name="smoke", log_file="log_file")

    @mock.patch("rally.api.objects.Deployment.get")
    @mock.patch("rally.api.tempest.Tempest")
    def test_install_tempest(self, mock_tempest, mock_deployment_get):
        mock_tempest.return_value = self.tempest
        api.Verification.install_tempest(self.deployment_uuid)
        self.tempest.install.assert_called_once_with()

    @mock.patch("rally.api.objects.Deployment.get")
    @mock.patch("rally.api.tempest.Tempest")
    def test_uninstall_tempest(self, mock_tempest, mock_deployment_get):
        mock_tempest.return_value = self.tempest
        api.Verification.uninstall_tempest(self.deployment_uuid)
        self.tempest.uninstall.assert_called_once_with()

    @mock.patch("rally.api.objects.Deployment.get")
    @mock.patch("rally.api.tempest.Tempest")
    def test_reinstall_tempest(self, mock_tempest, mock_deployment_get):
        fake_source = "fake__source"
        mock_tempest.return_value = self.tempest
        api.Verification.reinstall_tempest(self.deployment_uuid,
                                           source=fake_source)
        self.tempest.uninstall.assert_called_once_with()
        self.tempest.install.assert_called_once_with()

    @mock.patch("os.path.exists", return_value=True)
    @mock.patch("rally.common.objects.Deployment.get")
    @mock.patch("rally.verification.tempest.tempest.Tempest")
    def test_install_tempest_plugin_from_url(
            self, mock_tempest, mock_deployment_get, mock_exists):
        mock_tempest.return_value = self.tempest
        api.Verification.install_tempest_plugin(self.deployment_uuid,
                                                "https://fake/plugin")
        self.tempest.install_plugin.assert_called_once_with()

    @mock.patch("os.path.exists", return_value=True)
    @mock.patch("rally.common.objects.Deployment.get")
    @mock.patch("rally.verification.tempest.tempest.Tempest")
    def test_install_tempest_plugin_from_path(
            self, mock_tempest, mock_deployment_get, mock_exists):
        mock_tempest.return_value = self.tempest
        api.Verification.install_tempest_plugin(self.deployment_uuid,
                                                "/tmp/fake/plugin")
        self.tempest.install_plugin.assert_called_once_with()

    @mock.patch("os.path.exists", return_value=True)
    @mock.patch("rally.common.objects.Deployment.get")
    @mock.patch("rally.verification.tempest.tempest.Tempest")
    def test_list_tempest_plugins(
            self, mock_tempest, mock_deployment_get, mock_exists):
        mock_tempest.return_value = self.tempest
        api.Verification.list_tempest_plugins(self.deployment_uuid)
        self.tempest.list_plugins.assert_called_once_with()

    @mock.patch("rally.common.objects.Deployment.get")
    @mock.patch("rally.verification.tempest.tempest.Tempest")
    def test_uninstall_tempest_plugin(self, mock_tempest, mock_deployment_get):
        mock_tempest.return_value = self.tempest
        api.Verification.uninstall_tempest_plugin(self.deployment_uuid,
                                                  "fake-plugin")
        self.tempest.uninstall_plugin.assert_called_once_with("fake-plugin")

    @mock.patch("os.path.exists", return_value=True)
    @mock.patch("rally.common.objects.Deployment.get")
    @mock.patch("rally.verification.tempest.tempest.Tempest")
    def test_discover_tests(
            self, mock_tempest, mock_deployment_get, mock_exists):
        mock_tempest.return_value = self.tempest
        api.Verification.discover_tests(self.deployment_uuid, "some_pattern")
        self.tempest.discover_tests.assert_called_once_with("some_pattern")

    @mock.patch("os.path.exists", return_value=True)
    @mock.patch("rally.common.objects.Deployment.get")
    @mock.patch("rally.verification.tempest.tempest.Tempest")
    def test_configure_tempest_when_tempest_tree_exists(
            self, mock_tempest, mock_deployment_get, mock_exists):
        mock_tempest.return_value = self.tempest
        api.Verification.configure_tempest(self.deployment_uuid)
        self.tempest.generate_config_file.assert_called_once_with(None, False)

    @mock.patch("os.path.exists", return_value=False)
    @mock.patch("rally.common.objects.Deployment.get")
    @mock.patch("rally.verification.tempest.tempest.Tempest")
    def test_configure_tempest_when_no_tempest_tree_exists(
            self, mock_tempest, mock_deployment_get, mock_exists):
        mock_tempest.return_value = self.tempest
        self.assertRaises(exceptions.NotFoundException,
                          api.Verification.configure_tempest,
                          self.deployment_uuid)
        self.assertEqual(0, self.tempest.generate_config_file.call_count)

    @mock.patch("six.moves.builtins.open", side_effect=mock.mock_open())
    @mock.patch("os.path.exists", return_value=True)
    @mock.patch("rally.common.objects.Deployment.get")
    @mock.patch("rally.verification.tempest.tempest.Tempest")
    def test_show_config_info_when_tempest_tree_and_config_exist(
            self, mock_tempest, mock_deployment_get, mock_exists, mock_open):
        self.tempest.is_configured.return_value = True
        self.tempest.config_file = "/path/to/fake/conf"
        mock_tempest.return_value = self.tempest
        api.Verification.show_config_info(self.deployment_uuid)
        mock_open.assert_called_once_with("/path/to/fake/conf", "rb")

    @mock.patch("six.moves.builtins.open", side_effect=mock.mock_open())
    @mock.patch("os.path.exists", return_value=True)
    @mock.patch("rally.common.objects.Deployment.get")
    @mock.patch("rally.verification.tempest.tempest.Tempest")
    def test_show_config_info_when_tempest_tree_exists_and_config_doesnt(
            self, mock_tempest, mock_deployment_get, mock_exists, mock_open):
        self.tempest.is_configured.return_value = False
        self.tempest.config_file = "/path/to/fake/conf"
        mock_tempest.return_value = self.tempest
        api.Verification.show_config_info(self.deployment_uuid)
        self.tempest.generate_config_file.assert_called_once_with()
        mock_open.assert_called_once_with("/path/to/fake/conf", "rb")

    @mock.patch("six.moves.builtins.open", side_effect=mock.mock_open())
    @mock.patch("os.path.exists", return_value=False)
    @mock.patch("rally.common.objects.Deployment.get")
    @mock.patch("rally.verification.tempest.tempest.Tempest")
    def test_show_config_info_when_no_tempest_tree_exists(
            self, mock_tempest, mock_deployment_get, mock_exists, mock_open):
        mock_tempest.return_value = self.tempest
        self.assertRaises(exceptions.NotFoundException,
                          api.Verification.show_config_info,
                          self.deployment_uuid)
        self.assertEqual(0, mock_open.call_count)

    @mock.patch("rally.common.objects.Verification.list")
    def test_list(self, mock_verification_list):
        retval = api.Verification.list()
        self.assertEqual(mock_verification_list.return_value, retval)
        mock_verification_list.assert_called_once_with(None)

    @mock.patch("rally.common.objects.Verification.get")
    def test_get(self, mock_verification_get):
        retval = api.Verification.get("fake_id")
        self.assertEqual(mock_verification_get.return_value, retval)
        mock_verification_get.assert_called_once_with("fake_id")

    @mock.patch("rally.common.objects.deploy.db.deployment_delete")
    @mock.patch("rally.common.objects.deploy.db.deployment_update")
    @mock.patch("rally.common.objects.deploy.db.deployment_get")
    def test_destroy_invalid_deployment_type(self, mock_deployment_get,
                                             mock_deployment_update,
                                             mock_deployment_delete):
        with mock.patch.dict(self.deployment["config"],
                             {"type": "InvalidDeploymentType"}):
            deployment = mock.Mock()
            deployment.update_status = lambda x: x
            deployment.__getitem__ = lambda _self, key: self.deployment[key]
            self.assertRaises(exceptions.PluginNotFound,
                              engine.Engine.get_engine,
                              self.deployment["config"]["type"],
                              deployment)
            mock_deployment_get.return_value = self.deployment
            mock_deployment_update.return_value = self.deployment
            api.Deployment.destroy(self.deployment_uuid)
            mock_deployment_get.assert_called_once_with(self.deployment_uuid)
            mock_deployment_delete.assert_called_once_with(
                self.deployment_uuid)
