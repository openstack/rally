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

import jsonschema
import mock

from rally import api
from rally import consts
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
    @mock.patch("rally.api.engine.BenchmarkEngine")
    def test_validate(self, mock_engine, mock_deployment_get, mock_task):
        api.Task.validate(mock_deployment_get.return_value["uuid"], "config")

        mock_engine.assert_has_calls([
            mock.call("config", mock_task.return_value,
                      admin=mock_deployment_get.return_value["admin"],
                      users=[]),
            mock.call().validate()
        ])

        mock_task.assert_called_once_with(
            fake=True,
            deployment_uuid=mock_deployment_get.return_value["uuid"])
        mock_deployment_get.assert_called_once_with(
            mock_deployment_get.return_value["uuid"])

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

    @mock.patch("rally.objects.Deployment.get",
                return_value={"uuid": "b0d9cd6c-2c94-4417-a238-35c7019d0257"})
    @mock.patch("rally.objects.Task")
    def test_create(self, mock_task, mock_d_get):
        tag = "a"
        api.Task.create(mock_d_get.return_value["uuid"], tag)
        mock_task.assert_called_once_with(
            deployment_uuid=mock_d_get.return_value["uuid"], tag=tag)

    @mock.patch("rally.api.objects.Task")
    @mock.patch("rally.api.objects.Deployment.get",
                return_value=fakes.FakeDeployment(uuid="deployment_uuid",
                                                  admin=mock.MagicMock(),
                                                  users=[]))
    @mock.patch("rally.api.engine.BenchmarkEngine")
    def test_start(self, mock_engine, mock_deployment_get, mock_task):
        api.Task.start(mock_deployment_get.return_value["uuid"], "config")

        mock_engine.assert_has_calls([
            mock.call("config", mock_task.return_value,
                      admin=mock_deployment_get.return_value["admin"],
                      users=[], abort_on_sla_failure=False),
            mock.call().validate(),
            mock.call().run()
        ])

        mock_task.assert_called_once_with(
            deployment_uuid=mock_deployment_get.return_value["uuid"])
        mock_deployment_get.assert_called_once_with(
            mock_deployment_get.return_value["uuid"])

    @mock.patch("rally.api.objects.Task")
    @mock.patch("rally.api.objects.Deployment.get")
    @mock.patch("rally.api.engine.BenchmarkEngine")
    def test_start_invalid_task_ignored(self, mock_engine,
                                        mock_deployment_get, mock_task):
        mock_engine().run.side_effect = (
            exceptions.InvalidTaskException())

        # check that it doesn't raise anything
        api.Task.start("deployment_uuid", "config")

    @mock.patch("rally.api.objects.Task")
    @mock.patch("rally.api.objects.Deployment.get")
    @mock.patch("rally.api.engine.BenchmarkEngine")
    def test_start_exception(self, mock_engine, mock_deployment_get,
                             mock_task):
        mock_engine().run.side_effect = TypeError
        self.assertRaises(TypeError, api.Task.start, "deployment_uuid",
                          "config")
        mock_deployment_get().update_status.assert_called_once_with(
            consts.DeployStatus.DEPLOY_INCONSISTENT)

    def test_abort(self):
        self.assertRaises(NotImplementedError, api.Task.abort, self.task_uuid)

    @mock.patch("rally.objects.task.db.task_delete")
    def test_delete(self, mock_delete):
        api.Task.delete(self.task_uuid)
        mock_delete.assert_called_once_with(
            self.task_uuid,
            status=consts.TaskStatus.FINISHED)

    @mock.patch("rally.objects.task.db.task_delete")
    def test_delete_force(self, mock_delete):
        api.Task.delete(self.task_uuid, force=True)
        mock_delete.assert_called_once_with(self.task_uuid, status=None)


class BaseDeploymentTestCase(test.TestCase):
    def setUp(self):
        super(BaseDeploymentTestCase, self).setUp()
        self.deployment_config = FAKE_DEPLOYMENT_CONFIG
        self.deployment_uuid = "599bdf1d-fe77-461a-a810-d59b1490f4e3"
        admin_endpoint = FAKE_DEPLOYMENT_CONFIG.copy()
        admin_endpoint.pop("type")
        admin_endpoint["endpoint"] = None
        admin_endpoint.update(admin_endpoint.pop("admin"))
        admin_endpoint["permission"] = consts.EndpointPermission.ADMIN
        admin_endpoint["https_insecure"] = False
        admin_endpoint["https_cacert"] = None
        self.endpoints = {"admin": admin_endpoint, "users": []}
        self.deployment = {
            "uuid": self.deployment_uuid,
            "name": "fake_name",
            "config": self.deployment_config,
            "admin": self.endpoints["admin"],
            "users": []
        }


class DeploymentAPITestCase(BaseDeploymentTestCase):
    @mock.patch("rally.objects.deploy.db.deployment_update")
    @mock.patch("rally.objects.deploy.db.deployment_create")
    @mock.patch("rally.deploy.engine.EngineFactory.validate")
    def test_create(self, mock_validate, mock_create, mock_update):
        mock_create.return_value = self.deployment
        mock_update.return_value = self.deployment
        api.Deployment.create(self.deployment_config, "fake_deployment")
        mock_create.assert_called_once_with({
            "name": "fake_deployment",
            "config": self.deployment_config,
        })
        mock_validate.assert_called_with()
        mock_update.assert_has_calls([
            mock.call(self.deployment_uuid, self.endpoints)
        ])

    @mock.patch("rally.objects.deploy.db.deployment_update")
    @mock.patch("rally.objects.deploy.db.deployment_create")
    @mock.patch("rally.deploy.engine.EngineFactory.validate",
                side_effect=jsonschema.ValidationError("ValidationError"))
    def test_create_validation_error(self, mock_validate, mock_create,
                                     mock_update):
        mock_create.return_value = self.deployment
        self.assertRaises(jsonschema.ValidationError,
                          api.Deployment.create,
                          self.deployment_config, "fake_deployment")
        mock_update.assert_called_once_with(
            self.deployment_uuid,
            {"status": consts.DeployStatus.DEPLOY_FAILED})

    @mock.patch("rally.api.LOG")
    @mock.patch("rally.objects.deploy.db.deployment_create",
                side_effect=exceptions.DeploymentNameExists(
                    deployment="fake_deploy"))
    def test_create_duplication_error(self, mock_d_create, mock_log):
        self.assertRaises(exceptions.DeploymentNameExists,
                          api.Deployment.create, self.deployment_config,
                          "fake_deployment")

    @mock.patch("rally.objects.deploy.db.deployment_delete")
    @mock.patch("rally.objects.deploy.db.deployment_update")
    @mock.patch("rally.objects.deploy.db.deployment_get")
    def test_destroy(self, mock_get, mock_update, mock_delete):
        mock_get.return_value = self.deployment
        mock_update.return_value = self.deployment
        api.Deployment.destroy(self.deployment_uuid)
        mock_get.assert_called_once_with(self.deployment_uuid)
        mock_delete.assert_called_once_with(self.deployment_uuid)

    @mock.patch("rally.objects.deploy.db.deployment_update")
    @mock.patch("rally.objects.deploy.db.deployment_get")
    def test_recreate(self, mock_get, mock_update):
        mock_get.return_value = self.deployment
        mock_update.return_value = self.deployment
        api.Deployment.recreate(self.deployment_uuid)
        mock_get.assert_called_once_with(self.deployment_uuid)
        mock_update.assert_has_calls([
            mock.call(self.deployment_uuid, self.endpoints)
        ])


class VerificationAPITestCase(BaseDeploymentTestCase):
    def setUp(self):
        super(VerificationAPITestCase, self).setUp()
        self.tempest = mock.Mock()

    @mock.patch("rally.objects.Deployment.get")
    @mock.patch("rally.api.objects.Verification")
    @mock.patch("rally.verification.tempest.tempest.Tempest")
    def test_verify(self, mock_tempest, mock_verification, mock_d_get):
        mock_d_get.return_value = {"uuid": self.deployment_uuid}

        mock_tempest.return_value = self.tempest
        self.tempest.is_installed.return_value = True
        api.Verification.verify(self.deployment_uuid, "smoke", None, None)

        self.tempest.is_installed.assert_called_once_with()
        self.tempest.verify.assert_called_once_with(set_name="smoke",
                                                    regex=None)

    @mock.patch("rally.api.objects.Deployment.get")
    @mock.patch("rally.api.objects.Verification")
    @mock.patch("rally.verification.tempest.tempest.Tempest")
    def test_verify_tempest_not_installed(self, mock_tempest,
                                          mock_verification, mock_d_get):
        mock_d_get.return_value = {"uuid": self.deployment_uuid}
        mock_tempest.return_value = self.tempest
        self.tempest.is_installed.return_value = False
        api.Verification.verify(self.deployment_uuid, "smoke", None, None)

        self.tempest.is_installed.assert_called_once_with()
        self.tempest.install.assert_called_once_with()
        self.tempest.verify.assert_called_once_with(set_name="smoke",
                                                    regex=None)

    @mock.patch("rally.api.objects.Deployment.get")
    @mock.patch("rally.api.tempest.Tempest")
    def test_install_tempest(self, mock_tempest, mock_d_get):
        mock_tempest.return_value = self.tempest
        api.Verification.install_tempest(self.deployment_uuid)
        self.tempest.install.assert_called_once_with()

    @mock.patch("rally.api.objects.Deployment.get")
    @mock.patch("rally.api.tempest.Tempest")
    def test_uninstall_tempest(self, mock_tempest, mock_d_get):
        mock_tempest.return_value = self.tempest
        api.Verification.uninstall_tempest(self.deployment_uuid)
        self.tempest.uninstall.assert_called_once_with()

    @mock.patch("tempfile.gettempdir")
    @mock.patch("shutil.move")
    @mock.patch("shutil.copy2")
    @mock.patch("rally.api.objects.Deployment.get")
    @mock.patch("rally.api.tempest.Tempest")
    def test_reinstall_tempest(self, mock_tempest, mock_d_get,
                               mock_copy, mock_move, mock_tmp):

        fake_source = "fake__source"
        fake_conf = "/path/to/fake_conf"
        fake_tmpdir = "/fake/tmp/path/to/dir"
        tmp_file = os.path.join(fake_tmpdir, "fake_conf")
        self.tempest.config_file = fake_conf
        mock_tempest.return_value = self.tempest
        mock_tmp.return_value = fake_tmpdir
        api.Verification.reinstall_tempest(self.deployment_uuid,
                                           source=fake_source)
        self.tempest.uninstall.assert_called_once_with()
        mock_copy.assert_called_once_with(fake_conf,
                                          tmp_file)
        self.tempest.install.assert_called_once_with()
        mock_move.assert_called_once_with(tmp_file, fake_conf)


class DeprecatedAPITestCase(test.TestCase):
    @mock.patch("rally.api.Deployment.create",
                return_value="created_deployment")
    def test_create_deploy(self, mock_deployment_create):
        deployment = api.create_deploy(FAKE_DEPLOYMENT_CONFIG, "deployment")
        mock_deployment_create.assert_called_once_with(FAKE_DEPLOYMENT_CONFIG,
                                                       "deployment")
        self.assertEqual("created_deployment", deployment)

    @mock.patch("rally.api.Deployment.destroy")
    def test_destroy_deploy(self, mock_deployment_destroy):
        api.destroy_deploy("deployment")
        mock_deployment_destroy.assert_called_once_with("deployment")

    @mock.patch("rally.api.Deployment.recreate")
    def test_recreate_deploy(self, mock_deployment_recreate):
        api.recreate_deploy("deployment")
        mock_deployment_recreate.assert_called_once_with("deployment")

    @mock.patch("rally.api.Task.render_template",
                return_value="rendered_template")
    def test_task_template_render(self, mock_task_template_render):
        result = api.task_template_render("template", a=2, b=3)
        mock_task_template_render.assert_called_once_with("template", a=2, b=3)
        self.assertEqual("rendered_template", result)

    @mock.patch("rally.api.Task.create", return_value="created_task")
    def test_create_task(self, mock_task_create):
        task = api.create_task("deployment", "tag")
        mock_task_create.assert_called_once_with("deployment", "tag")
        self.assertEqual("created_task", task)

    @mock.patch("rally.api.Task.validate")
    def test_task_validate(self, mock_task_validate):
        api.task_validate("deployment", "config")
        mock_task_validate.assert_called_once_with("deployment", "config")

    @mock.patch("rally.api.Task.start")
    def test_start_task(self, mock_task_start):
        api.start_task("deployment", "config", "task")
        mock_task_start.assert_called_once_with("deployment", "config", "task")

    @mock.patch("rally.api.Task.abort")
    def test_abort_task(self, mock_task_abort):
        api.abort_task("task_uuid")
        mock_task_abort.assert_called_once_with("task_uuid")

    @mock.patch("rally.api.Task.delete")
    def test_delete_task(self, mock_task_delete):
        api.delete_task("task_uuid", force=True)
        mock_task_delete.assert_called_once_with("task_uuid", True)

    @mock.patch("rally.api.Verification.verify")
    def test_verify(self, mock_verification_verify):
        api.verify("deployment", "set", "regex", "tempest_config")
        mock_verification_verify.assert_called_once_with(
            "deployment", "set", "regex", "tempest_config")

    @mock.patch("rally.api.Verification.install_tempest")
    def test_install_tempest(self, mock_verification_install_tempest):
        api.install_tempest("deployment", "source")
        mock_verification_install_tempest.assert_called_once_with(
            "deployment", "source")
