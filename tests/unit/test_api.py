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
    @mock.patch("rally.api.engine.BenchmarkEngine")
    def test_validate(
            self, mock_benchmark_engine, mock_deployment_get, mock_task):
        api.Task.validate(mock_deployment_get.return_value["uuid"], "config")

        mock_benchmark_engine.assert_has_calls([
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
    @mock.patch("rally.api.engine.BenchmarkEngine")
    def test_validate_engine_exception(self, mock_benchmark_engine,
                                       mock_deployment, mock_task):

        excpt = exceptions.InvalidTaskException()
        mock_benchmark_engine.return_value.validate.side_effect = excpt
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
    @mock.patch("rally.api.engine.BenchmarkEngine")
    def test_start(self, mock_benchmark_engine, mock_deployment_get,
                   mock_task):
        api.Task.start(mock_deployment_get.return_value["uuid"], "config")

        mock_benchmark_engine.assert_has_calls([
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
    @mock.patch("rally.api.engine.BenchmarkEngine")
    def test_start_exception(self, mock_benchmark_engine, mock_deployment_get,
                             mock_task):
        mock_task.return_value.is_temporary = False
        mock_benchmark_engine.return_value.run.side_effect = TypeError
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
            mock.call(self.deployment_uuid, self.endpoints)
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
            mock.call(self.deployment_uuid, self.endpoints)
        ])

    @mock.patch("rally.common.objects.deploy.db.deployment_get")
    def test_get(self, mock_deployment_get):
        deployment_id = "aaaa-bbbb-cccc-dddd"
        mock_deployment_get.return_value = self.deployment
        ret = api.Deployment.get(deployment_id)
        for key in self.deployment:
            self.assertEqual(ret[key], self.deployment[key])


class VerificationAPITestCase(BaseDeploymentTestCase):
    def setUp(self):
        super(VerificationAPITestCase, self).setUp()
        self.tempest = mock.Mock()

    @mock.patch("rally.common.objects.Deployment.get")
    @mock.patch("rally.api.objects.Verification")
    @mock.patch("rally.verification.tempest.tempest.Tempest")
    def test_verify(self, mock_tempest, mock_verification,
                    mock_deployment_get):
        mock_deployment_get.return_value = {"uuid": self.deployment_uuid}

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
                                          mock_verification,
                                          mock_deployment_get):
        mock_deployment_get.return_value = {"uuid": self.deployment_uuid}
        mock_tempest.return_value = self.tempest
        self.tempest.is_installed.return_value = False
        api.Verification.verify(self.deployment_uuid, "smoke", None, None)

        self.tempest.is_installed.assert_called_once_with()
        self.tempest.install.assert_called_once_with()
        self.tempest.verify.assert_called_once_with(set_name="smoke",
                                                    regex=None)

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

    @mock.patch("tempfile.gettempdir")
    @mock.patch("shutil.move")
    @mock.patch("shutil.copy2")
    @mock.patch("rally.api.objects.Deployment.get")
    @mock.patch("rally.api.tempest.Tempest")
    def test_reinstall_tempest(self, mock_tempest, mock_deployment_get,
                               mock_copy2, mock_move, mock_gettempdir):

        fake_source = "fake__source"
        fake_conf = "/path/to/fake_conf"
        fake_tmpdir = "/fake/tmp/path/to/dir"
        tmp_file = os.path.join(fake_tmpdir, "fake_conf")
        self.tempest.config_file = fake_conf
        mock_tempest.return_value = self.tempest
        mock_gettempdir.return_value = fake_tmpdir
        api.Verification.reinstall_tempest(self.deployment_uuid,
                                           source=fake_source)
        self.tempest.uninstall.assert_called_once_with()
        mock_copy2.assert_called_once_with(fake_conf, tmp_file)
        self.tempest.install.assert_called_once_with()
        mock_move.assert_called_once_with(tmp_file, fake_conf)

    @mock.patch("rally.common.objects.Deployment.get")
    @mock.patch("rally.verification.tempest.tempest.Tempest")
    def test_configure_tempest(self, mock_tempest, mock_deployment_get):
        mock_tempest.return_value = self.tempest
        api.Verification.configure_tempest(self.deployment_uuid)
        self.tempest.generate_config_file.assert_called_once_with(False)
