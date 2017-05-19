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

"""Test for api."""

import copy
import os

import ddt
import jsonschema
import mock
from oslo_config import cfg

from rally import api
from rally.common import objects
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
        "profiler_hmac_key": None
    },
    "region_name": "RegionOne",
    "endpoint_type": consts.EndpointType.INTERNAL,
}


@ddt.ddt
class TaskAPITestCase(test.TestCase):
    def setUp(self):
        super(TaskAPITestCase, self).setUp()
        self.task_uuid = "b0d9cd6c-2c94-4417-a238-35c7019d0257"
        self.task = {"uuid": self.task_uuid}
        self.task_inst = api._Task(mock.Mock())

    @mock.patch("rally.api.objects.Task")
    @mock.patch("rally.api.objects.Deployment.get")
    @mock.patch("rally.api.engine.TaskEngine")
    def test_validate(self, mock_task_engine, mock_deployment_get, mock_task):
        fake_deployment = fakes.FakeDeployment(
            uuid="deployment_uuid_1", admin="fake_admin", users=["fake_user"])
        mock_deployment_get.return_value = fake_deployment

        #######################################################################
        # The case #1 -- create temporary task
        #######################################################################
        self.task_inst.validate(fake_deployment["uuid"], "config")

        mock_task_engine.assert_called_once_with(
            "config", mock_task.return_value, fake_deployment),
        mock_task_engine.return_value.validate.assert_called_once_with()

        mock_task.assert_called_once_with(
            temporary=True, deployment_uuid=fake_deployment["uuid"])
        mock_deployment_get.assert_called_once_with(fake_deployment["uuid"])
        self.assertFalse(mock_task.get.called)

        #######################################################################
        # The case #2 -- validate pre-created task
        #######################################################################
        mock_task_engine.reset_mock()
        mock_task.reset_mock()
        mock_deployment_get.reset_mock()

        fake_task = fakes.FakeTask(deployment_uuid="deployment_uuid_2")
        mock_task.get.return_value = fake_task

        task_uuid = "task-id"

        self.task_inst.validate(fake_deployment["uuid"], "config",
                                task=task_uuid)

        mock_task_engine.assert_called_once_with("config", fake_task,
                                                 fake_deployment)
        mock_task_engine.return_value.validate.assert_called_once_with()

        self.assertFalse(mock_task.called)
        # check that deployment uuid is taken from task
        mock_deployment_get.assert_called_once_with(
            fake_task["deployment_uuid"])

        mock_task.get.assert_called_once_with(task_uuid)

        #######################################################################
        # The case #3 -- validate deprecated way for pre-created task
        #######################################################################
        mock_task_engine.reset_mock()
        mock_task.reset_mock()
        mock_deployment_get.reset_mock()

        task_instance = fakes.FakeTask(uuid="task-id")

        self.task_inst.validate(fake_deployment["uuid"], "config",
                                task_instance=task_instance)

        mock_task_engine.assert_called_once_with("config", fake_task,
                                                 fake_deployment)
        mock_task_engine.return_value.validate.assert_called_once_with()

        self.assertFalse(mock_task.called)
        # check that deployment uuid is taken from task
        mock_deployment_get.assert_called_once_with(
            fake_task["deployment_uuid"])

        mock_task.get.assert_called_once_with(task_instance["uuid"])

    @mock.patch("rally.api.objects.Task")
    @mock.patch("rally.api.objects.Deployment",
                return_value=fakes.FakeDeployment(uuid="deployment_uuid"))
    @mock.patch("rally.api.engine.TaskEngine")
    def test_validate_engine_exception(self, mock_task_engine,
                                       mock_deployment, mock_task):
        excpt = exceptions.InvalidTaskException()
        mock_task_engine.return_value.validate.side_effect = excpt
        self.assertRaises(exceptions.InvalidTaskException,
                          self.task_inst.validate,
                          mock_deployment.return_value["uuid"], "config")

    def test_render_template(self):
        self.assertEqual(
            "3 = 3",
            self.task_inst.render_template(
                "{{a + b}} = {{c}}", a=1, b=2, c=3))

    def test_render_template_default_values(self):
        template = "{% set a = a or 1 %}{{a + b}} = {{c}}"

        self.assertEqual("3 = 3",
                         self.task_inst.render_template(template, b=2, c=3))

        self.assertEqual("5 = 5",
                         self.task_inst.render_template(
                             template, a=2, b=3, c=5))

    def test_render_template_default_filter(self):
        template = "{{ c | default(3) }}"

        self.assertEqual("3", self.task_inst.render_template(template))
        self.assertEqual("5", self.task_inst.render_template(template, c=5))

    def test_render_template_builtin(self):
        template = "{% for i in range(4) %}{{i}}{% endfor %}"

        self.assertEqual("0123", self.task_inst.render_template(template))

    def test_render_template_missing_args(self):

        self.assertRaises(TypeError, self.task_inst.render_template, "{{a}}")

    def test_render_template_include_other_template(self):
        other_template_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "samples/tasks/scenarios/nova/boot.json")
        template = "{%% include \"%s\" %%}" % os.path.basename(
            other_template_path)
        with open(other_template_path) as f:
            other_template = f.read()
        expect = self.task_inst.render_template(other_template)
        actual = self.task_inst.render_template(
            template, os.path.dirname(other_template_path))
        self.assertEqual(expect, actual)

    def test_render_template_min(self):
        template = "{{ min(1, 2)}}"
        self.assertEqual("1", self.task_inst.render_template(template))

    def test_render_template_max(self):
        template = "{{ max(1, 2)}}"
        self.assertEqual("2", self.task_inst.render_template(template))

    def test_render_template_ceil(self):
        template = "{{ ceil(2.2)}}"
        self.assertEqual("3", self.task_inst.render_template(template))

    def test_render_template_round(self):
        template = "{{ round(2.2)}}"
        self.assertEqual("2", self.task_inst.render_template(template))

    @mock.patch("rally.common.objects.Deployment.get",
                return_value={
                    "uuid": "b0d9cd6c-2c94-4417-a238-35c7019d0257",
                    "status": consts.DeployStatus.DEPLOY_FINISHED})
    @mock.patch("rally.common.objects.Task")
    def test_create(self, mock_task, mock_deployment_get):
        tag = "a"
        self.task_inst.create(mock_deployment_get.return_value["uuid"], tag)
        mock_task.assert_called_once_with(
            deployment_uuid=mock_deployment_get.return_value["uuid"], tag=tag)

    @mock.patch("rally.common.objects.Deployment.get",
                return_value={
                    "name": "xxx_name",
                    "uuid": "u_id",
                    "status": consts.DeployStatus.DEPLOY_INIT})
    def test_create_on_unfinished_deployment(self, mock_deployment_get):
        deployment_id = mock_deployment_get.return_value["uuid"]
        tag = "a"
        self.assertRaises(exceptions.DeploymentNotFinishedStatus,
                          self.task_inst.create, deployment_id, tag)

    @mock.patch("rally.api.objects.Task")
    @mock.patch("rally.api.objects.Deployment.get")
    @mock.patch("rally.api.engine.TaskEngine")
    def test_start(self, mock_task_engine, mock_deployment_get,
                   mock_task):
        fake_task = fakes.FakeTask(uuid="some_uuid")
        fake_task.get_status = mock.Mock()
        mock_task.return_value = fake_task
        mock_deployment_get.return_value = fakes.FakeDeployment(
            uuid="deployment_uuid", admin="fake_admin", users=["fake_user"],
            status=consts.DeployStatus.DEPLOY_FINISHED)

        self.assertEqual(
            (fake_task["uuid"], fake_task.get_status.return_value),
            self.task_inst.start(
                mock_deployment_get.return_value["uuid"], "config")
        )

        mock_task_engine.assert_has_calls([
            mock.call("config", mock_task.return_value,
                      mock_deployment_get.return_value,
                      abort_on_sla_failure=False),
            mock.call().run(),
        ])

        mock_task.assert_called_once_with(
            deployment_uuid=mock_deployment_get.return_value["uuid"])

        mock_deployment_get.assert_called_once_with(
            mock_deployment_get.return_value["uuid"])

    @mock.patch("rally.api.objects.Deployment.get")
    def test_start_temporary_task(self, mock_deployment_get):
        fake_deployment = fakes.FakeDeployment(
            uuid="deployment_uuid", admin="fake_admin", users=["fake_user"],
            status=consts.DeployStatus.DEPLOY_FINISHED,
            name="foo")
        mock_deployment_get.return_value = fake_deployment
        fake_task = objects.Task(task={"deployment_uuid": "deployment_uuid",
                                       "uuid": "some_uuid"}, temporary=True)

        self.assertRaises(ValueError, self.task_inst.start,
                          fake_deployment, "config", task=fake_task)

    @mock.patch("rally.api.objects.task.db.task_get")
    @mock.patch("rally.api.objects.Deployment.get")
    def test_start_with_inconsistent_deployment(self, mock_deployment_get,
                                                mock_task_get):
        deployment_uuid = "deployment_uuid"
        fake_deployment = fakes.FakeDeployment(
            uuid=deployment_uuid, admin="fake_admin", users=["fake_user"],
            status=consts.DeployStatus.DEPLOY_INCONSISTENT,
            name="foo")
        mock_deployment_get.return_value = fake_deployment
        fake_task_dict = {"deployment_uuid": deployment_uuid,
                          "uuid": "some_uuid"}
        fake_task = objects.Task(task=fake_task_dict)
        mock_task_get.return_value = fake_task_dict

        self.assertRaises(exceptions.DeploymentNotFinishedStatus,
                          self.task_inst.start, deployment_uuid, "config",
                          task=fake_task)

    @mock.patch("rally.api.objects.Task")
    @mock.patch("rally.api.objects.Deployment.get")
    @mock.patch("rally.api.engine.TaskEngine")
    @mock.patch("rally.api.CONF", spec=cfg.CONF)
    def test_start_exception(self, mock_conf, mock_task_engine,
                             mock_deployment_get, mock_task):
        fake_deployment = fakes.FakeDeployment(
            status=consts.DeployStatus.DEPLOY_FINISHED,
            name="foo", uuid="deployment_uuid")
        mock_deployment_get.return_value = fake_deployment
        mock_task.return_value.is_temporary = False
        mock_task_engine.return_value.run.side_effect = TypeError
        self.assertRaises(TypeError, self.task_inst.start,
                          "deployment_uuid", "config")
        fake_deployment.update_status.assert_called_once_with(
            consts.DeployStatus.DEPLOY_INCONSISTENT)

    @ddt.data(True, False)
    @mock.patch("rally.api.time")
    @mock.patch("rally.api.objects.Task")
    def test_abort_sync(self, soft, mock_task, mock_time):
        mock_task.get_status.side_effect = (
            consts.TaskStatus.INIT,
            consts.TaskStatus.VALIDATING,
            consts.TaskStatus.RUNNING,
            consts.TaskStatus.ABORTING,
            consts.TaskStatus.SOFT_ABORTING,
            consts.TaskStatus.ABORTED)

        some_uuid = "ca441749-0eb9-4fcc-b2f6-76d314c55404"

        self.task_inst.abort(some_uuid, soft=soft, async=False)

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

        self.task_inst.abort(some_uuid, soft=soft, async=True)

        mock_task.get.assert_called_once_with(some_uuid)
        mock_task.get.return_value.abort.assert_called_once_with(soft=soft)
        self.assertFalse(mock_task.get_status.called)
        self.assertFalse(mock_time.sleep.called)

    @ddt.data({"task_status": "strange value",
               "expected_status": consts.TaskStatus.FINISHED},
              {"task_status": consts.TaskStatus.INIT,
               "expected_status": consts.TaskStatus.FINISHED},
              {"task_status": consts.TaskStatus.VALIDATING,
               "expected_status": consts.TaskStatus.FINISHED},
              {"task_status": consts.TaskStatus.ABORTING,
               "expected_status": consts.TaskStatus.FINISHED},
              {"task_status": consts.TaskStatus.SOFT_ABORTING,
               "expected_status": consts.TaskStatus.FINISHED},
              {"task_status": consts.TaskStatus.RUNNING,
               "expected_status": consts.TaskStatus.FINISHED},
              {"task_status": consts.TaskStatus.ABORTED,
               "expected_status": None},
              {"task_status": consts.TaskStatus.FINISHED,
               "expected_status": None},
              {"task_status": consts.TaskStatus.CRASHED,
               "expected_status": None},
              {"task_status": "strange value",
               "force": True, "expected_status": None},
              {"task_status": consts.TaskStatus.INIT,
               "force": True, "expected_status": None},
              {"task_status": consts.TaskStatus.VALIDATING,
               "force": True, "expected_status": None},
              {"task_status": consts.TaskStatus.RUNNING,
               "force": True, "expected_status": None},
              {"task_status": consts.TaskStatus.ABORTING,
               "force": True, "expected_status": None},
              {"task_status": consts.TaskStatus.SOFT_ABORTING,
               "force": True, "expected_status": None},
              {"task_status": consts.TaskStatus.ABORTED,
               "force": True, "expected_status": None},
              {"task_status": consts.TaskStatus.FINISHED,
               "force": True, "expected_status": None},
              {"task_status": consts.TaskStatus.CRASHED,
               "force": True, "expected_status": None})
    @ddt.unpack
    @mock.patch("rally.api.objects.Task.get_status")
    @mock.patch("rally.api.objects.Task.delete_by_uuid")
    def test_delete(self, mock_task_delete_by_uuid, mock_task_get_status,
                    task_status, expected_status, force=False, raises=None):
        mock_task_get_status.return_value = task_status
        self.task_inst.delete(self.task_uuid, force=force)
        if force:
            self.assertFalse(mock_task_get_status.called)
        else:
            mock_task_get_status.assert_called_once_with(self.task_uuid)
        mock_task_delete_by_uuid.assert_called_once_with(
            self.task_uuid,
            status=expected_status)

    @mock.patch("rally.api.objects.Task")
    def test_get_detailed(self, mock_task):
        mock_task.get_detailed.return_value = "detailed_task_data"
        self.assertEqual("detailed_task_data",
                         self.task_inst.get_detailed("task_uuid"))
        mock_task.get_detailed.assert_called_once_with("task_uuid")

    @mock.patch("rally.api.objects.Task")
    def test_list(self, mock_task):
        task = mock.Mock()
        task.to_dict.return_value = self.task
        mock_task.list.return_value = [task]
        tasks = self.task_inst.list()
        self.assertEqual([self.task], tasks)

    @mock.patch("rally.api.objects.Task")
    def test_get_detailed_with_extended_results(self, mock_task):
        mock_task.get_detailed.return_value = (("uuid", "foo_uuid"),
                                               ("results", "raw_results"))
        mock_task.extend_results.return_value = "extended_results"

        self.assertEqual({"uuid": "foo_uuid", "results": "extended_results"},
                         self.task_inst.get_detailed("foo_uuid",
                                                     extended_results=True))
        mock_task.get_detailed.assert_called_once_with("foo_uuid")
        mock_task.extend_results.assert_called_once_with("raw_results")


class BaseDeploymentTestCase(test.TestCase):
    def setUp(self):
        super(BaseDeploymentTestCase, self).setUp()
        self.deployment_inst = api._Deployment(mock.Mock())
        self.deployment_config = copy.deepcopy(FAKE_DEPLOYMENT_CONFIG)
        self.deployment_uuid = "599bdf1d-fe77-461a-a810-d59b1490f4e3"
        admin_credential = copy.deepcopy(FAKE_DEPLOYMENT_CONFIG)
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
            "credentials": {"openstack": [self.credentials]}
        }


class DeploymentAPITestCase(BaseDeploymentTestCase):
    @mock.patch("rally.common.objects.deploy.db.deployment_update")
    @mock.patch("rally.common.objects.deploy.db.deployment_create")
    @mock.patch("rally.deployment.engines.existing.ExistingCloud.validate")
    def test_create(self, mock_existing_cloud_validate,
                    mock_deployment_create, mock_deployment_update):
        mock_deployment_create.return_value = self.deployment
        mock_deployment_update.return_value = self.deployment
        dep = self.deployment_inst.create(self.deployment_config,
                                          "fake_deployment")
        self.assertIsInstance(dep, dict)
        mock_deployment_create.assert_called_once_with({
            "name": "fake_deployment",
            "config": self.deployment_config,
        })
        mock_existing_cloud_validate.assert_called_once_with()
        mock_deployment_update.assert_has_calls([
            mock.call(self.deployment_uuid,
                      {"credentials": {"openstack": [self.credentials]}})
        ])

    @mock.patch("rally.common.objects.deploy.db.deployment_update")
    @mock.patch("rally.common.objects.deploy.db.deployment_create")
    @mock.patch("rally.deployment.engines.existing.ExistingCloud.validate",
                side_effect=jsonschema.ValidationError("ValidationError"))
    def test_create_validation_error(
            self, mock_existing_cloud_validate, mock_deployment_create,
            mock_deployment_update):
        mock_deployment_create.return_value = self.deployment
        self.assertRaises(jsonschema.ValidationError,
                          self.deployment_inst.create,
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
                          self.deployment_inst.create, self.deployment_config,
                          "fake_deployment")

    @mock.patch("rally.common.objects.deploy.db.deployment_delete")
    @mock.patch("rally.common.objects.deploy.db.deployment_update")
    @mock.patch("rally.common.objects.deploy.db.deployment_get")
    def test_destroy(self, mock_deployment_get, mock_deployment_update,
                     mock_deployment_delete):
        mock_deployment_get.return_value = self.deployment
        mock_deployment_update.return_value = self.deployment

        list_verifiers = [mock.Mock(), mock.Mock()]
        self.deployment_inst.api.verifier.list.return_value = list_verifiers

        self.deployment_inst.destroy(self.deployment_uuid)

        mock_deployment_get.assert_called_once_with(self.deployment_uuid)
        mock_deployment_delete.assert_called_once_with(self.deployment_uuid)
        self.deployment_inst.api.verifier.list.assert_called_once_with()
        self.assertEqual(
            [mock.call(m.name, self.deployment["name"], force=True)
             for m in list_verifiers],
            self.deployment_inst.api.verifier.delete.call_args_list)

    @mock.patch("rally.common.objects.deploy.db.deployment_update")
    @mock.patch("rally.common.objects.deploy.db.deployment_get")
    def test_recreate(self, mock_deployment_get, mock_deployment_update):
        mock_deployment_get.return_value = self.deployment
        mock_deployment_update.return_value = self.deployment
        self.deployment_inst.recreate(self.deployment_uuid)
        mock_deployment_get.assert_called_once_with(self.deployment_uuid)
        mock_deployment_update.assert_has_calls([
            mock.call(
                self.deployment_uuid,
                {"credentials":
                    {"openstack": [{"admin": self.credentials["admin"],
                                    "users": self.credentials["users"]}]}})
        ])

    @mock.patch("rally.common.objects.deploy.db.deployment_update")
    @mock.patch("rally.common.objects.deploy.db.deployment_get")
    def test_recreate_config(self, mock_deployment_get,
                             mock_deployment_update):
        mock_deployment_get.return_value = self.deployment
        mock_deployment_update.return_value = self.deployment
        config = copy.deepcopy(self.deployment_config)
        config["admin"] = {"username": "admin",
                           "password": "pass1",
                           "tenant_name": "demo"}
        config["users"] = [{"username": "user1",
                            "password": "pass2",
                            "tenant_name": "demo"}]

        self.deployment_inst.recreate(self.deployment_uuid, config)
        mock_deployment_get.assert_called_once_with(self.deployment_uuid)
        mock_deployment_update.assert_has_calls([
            mock.call(self.deployment_uuid, {"config": config}),
        ])

    @mock.patch("rally.common.objects.deploy.db.deployment_update")
    @mock.patch("rally.common.objects.deploy.db.deployment_get")
    def test_recreate_config_invalid(self, mock_deployment_get,
                                     mock_deployment_update):
        mock_deployment_get.return_value = self.deployment
        mock_deployment_update.return_value = self.deployment
        config = copy.deepcopy(self.deployment_config)
        config["admin"] = {"foo": "bar"}

        self.assertRaises(jsonschema.ValidationError,
                          self.deployment_inst.recreate,
                          self.deployment_uuid, config)

    @mock.patch("rally.common.objects.deploy.db.deployment_update")
    @mock.patch("rally.common.objects.deploy.db.deployment_get")
    def test_recreate_config_wrong_type(self, mock_deployment_get,
                                        mock_deployment_update):
        mock_deployment_get.return_value = self.deployment
        mock_deployment_update.return_value = self.deployment
        config = copy.deepcopy(self.deployment_config)
        config["type"] = "foo"

        self.assertRaises(exceptions.RallyException,
                          self.deployment_inst.recreate,
                          self.deployment_uuid, config)

    @mock.patch("rally.common.objects.deploy.db.deployment_get")
    def test_get(self, mock_deployment_get):
        deployment_id = "aaaa-bbbb-cccc-dddd"
        mock_deployment_get.return_value = self.deployment
        ret = self.deployment_inst.get(deployment_id)
        for key in self.deployment:
            self.assertEqual(ret[key], self.deployment[key])

    @mock.patch("rally.common.objects.Deployment.list")
    def test_list(self, mock_deployment_list):
        mock_deployment_list.return_value = self.deployment
        ret = self.deployment_inst.list()
        for key in self.deployment:
            self.assertEqual(ret[key], self.deployment[key])

    @mock.patch("rally.common.objects.Deployment.get")
    def test_deployment_check(self, mock_deployment_get):
        fake_credential1 = fakes.fake_credential()
        fake_credential2 = fakes.fake_credential()

        mock_deployment_get.return_value.get_all_credentials.return_value = {
            "openstack": [{"admin": fake_credential1,
                           "users": [fake_credential2]}]}

        self.assertEqual(
            {"openstack": [
                {"services": fake_credential1.list_services.return_value}]},
            self.deployment_inst.check("uuid"))

        fake_credential1.verify_connection.assert_called_once_with()
        fake_credential2.verify_connection.assert_called_once_with()

    @mock.patch("rally.common.objects.Deployment.get")
    def test_deployment_check_list_services_via_admin(self,
                                                      mock_deployment_get):
        fake_credential1 = fakes.fake_credential()
        fake_credential2 = fakes.fake_credential()

        mock_deployment_get.return_value.get_all_credentials.return_value = {
            "openstack": [{"admin": fake_credential1,
                           "users": [fake_credential2]}]}

        self.assertEqual(
            {"openstack": [
                {"services": fake_credential1.list_services.return_value}]},
            self.deployment_inst.check("uuid"))

        fake_credential1.verify_connection.assert_called_once_with()
        fake_credential1.list_services.assert_called_once_with()
        fake_credential2.verify_connection.assert_called_once_with()
        self.assertFalse(fake_credential2.list_services.called)

    @mock.patch("rally.common.objects.Deployment.get")
    def test_deployment_check_list_services_via_user(self,
                                                     mock_deployment_get):
        fake_credential1 = fakes.fake_credential()
        fake_credential2 = fakes.fake_credential()

        mock_deployment_get.return_value.get_all_credentials.return_value = {
            "openstack": [{"admin": None,
                           "users": [fake_credential2, fake_credential1]}]}

        self.assertEqual(
            {"openstack": [
                {"services": fake_credential2.list_services.return_value}]},
            self.deployment_inst.check("uuid"))

        fake_credential2.verify_connection.assert_called_once_with()
        fake_credential2.list_services.assert_called_once_with()
        fake_credential1.verify_connection.assert_called_once_with()
        self.assertFalse(fake_credential1.list_services.called)

    @mock.patch("rally.api.traceback")
    @mock.patch("rally.common.objects.Deployment.get")
    def test_deployment_check_fails(self, mock_deployment_get, mock_traceback):
        mock_traceback.format_exc.side_effect = ("Trace1", "Trace2")
        fake_credential1 = fakes.fake_credential()
        fake_credential2 = fakes.fake_credential()

        fake_credential1.verify_connection.side_effect = KeyError("oops")
        fake_credential2.verify_connection.side_effect = TypeError("ooooops")

        mock_deployment_get.return_value.get_all_credentials.return_value = {
            "openstack": [{"admin": fake_credential1,
                           "users": [fake_credential2]}]}

        self.assertEqual(
            {"openstack": [
                {"services": [],
                 "admin_error": {
                     "etype": "KeyError", "msg": "'oops'",
                     "trace": "Trace1"},
                 "user_error": {
                     "etype": "TypeError", "msg": "ooooops",
                     "trace": "Trace2"}}]},
            self.deployment_inst.check("uuid"))

        fake_credential1.verify_connection.assert_called_once_with()
        fake_credential2.verify_connection.assert_called_once_with()
        self.assertFalse(fake_credential1.list_services.called)
        self.assertFalse(fake_credential2.list_services.called)

    def test_service_list(self):
        fake_credential = fakes.fake_credential()
        deployment = mock.Mock(spec=objects.Deployment)
        deployment.get_credentials_for.return_value = {
            "admin": fake_credential, "users": []}
        result = self.deployment_inst.service_list(deployment)
        self.assertEqual(fake_credential.list_services.return_value, result)


class APITestCase(test.TestCase):

    @mock.patch("os.path.isfile", return_value=False)
    @mock.patch("rally.common.version.database_revision",
                return_value={"revision": "foobar", "current_head": "foobar"})
    @mock.patch("rally.common.version.version_string", return_value="0.0.0")
    @mock.patch("rally.api.CONF", spec=cfg.CONF)
    def test_init_config_args(self, mock_conf, mock_version_string,
                              mock_database_revision, mock_isfile):
        api_ = api.API(config_args=["foo", "bar", "baz"])
        mock_conf.assert_called_once_with(
            ["foo", "bar", "baz"], default_config_files=None,
            project="rally", version="0.0.0")

        self.assertIsInstance(api_._deployment, api._Deployment)
        self.assertIsInstance(api_._task, api._Task)

    @mock.patch("os.path.isfile", return_value=False)
    @mock.patch("rally.common.version.database_revision",
                return_value={"revision": "foobar", "current_head": "foobar"})
    @mock.patch("rally.common.version.version_string", return_value="0.0.0")
    @mock.patch("rally.api.CONF", spec=cfg.CONF)
    def test_init_config_file(self, mock_conf, mock_version_string,
                              mock_database_revision, mock_isfile):
        api_ = api.API(config_file="myfile.conf")
        mock_conf.assert_called_once_with(
            [], default_config_files=["myfile.conf"],
            project="rally", version="0.0.0")

        self.assertIsInstance(api_._deployment, api._Deployment)
        self.assertIsInstance(api_._task, api._Task)

    @mock.patch("os.path.isfile", return_value=False)
    @mock.patch("rally.common.version.database_revision",
                return_value={"revision": "foobar", "current_head": "foobar"})
    @mock.patch("rally.common.version.version_string", return_value="0.0.0")
    @mock.patch("rally.api.CONF", spec=cfg.CONF)
    def test_init_no_default_config_file(self, mock_conf, mock_version_string,
                                         mock_database_revision, mock_isfile):
        api.API(skip_db_check=True)
        mock_conf.assert_called_once_with(
            [], default_config_files=None, project="rally", version="0.0.0")

    @mock.patch("os.path.isfile")
    @mock.patch("rally.common.version.database_revision",
                return_value={"revision": "foobar", "current_head": "foobar"})
    @mock.patch("rally.common.version.version_string", return_value="0.0.0")
    @mock.patch("rally.api.CONF", spec=cfg.CONF)
    def test_init_default_config_file(self, mock_conf, mock_version_string,
                                      mock_database_revision, mock_isfile):
        mock_isfile.side_effect = lambda f: f == "/etc/rally/rally.conf"
        api.API(skip_db_check=True)
        mock_conf.assert_called_once_with(
            [], default_config_files=["/etc/rally/rally.conf"],
            project="rally", version="0.0.0")

    @mock.patch("os.path.isfile", return_value=False)
    @mock.patch("rally.common.version.version_string", return_value="0.0.0")
    @mock.patch("rally.api.CONF", spec=cfg.CONF)
    def test_init_exception(self, mock_conf, mock_version_string, mock_isfile):
        mock_conf.side_effect = cfg.ConfigFilesNotFoundError(["file1",
                                                              "file2"])
        self.assertRaises(exceptions.RallyException, api.API)
        mock_conf.assert_called_once_with(
            [], default_config_files=None, project="rally", version="0.0.0")

    @mock.patch("os.path.isfile", return_value=False)
    @mock.patch("rally.common.plugin.discover.load_plugins")
    @mock.patch("rally.common.version.database_revision",
                return_value={"revision": "foobar", "current_head": "foobar"})
    @mock.patch("rally.common.version.version_string", return_value="0.0.0")
    @mock.patch("rally.api.CONF", spec=cfg.CONF)
    def test_init_plugin_path(self, mock_conf, mock_version_string,
                              mock_database_revision, mock_load_plugins,
                              mock_isfile):
        mock_conf.__contains__.return_value = True
        mock_conf.get.side_effect = (
            lambda a: ["/path/from/args"] if a == "plugin_paths" else None)
        api.API(plugin_paths=["/my/path"])
        mock_conf.assert_called_once_with([], default_config_files=None,
                                          project="rally", version="0.0.0")
        mock_load_plugins.assert_has_calls([
            mock.call("/my/path"),
            mock.call("/path/from/args"),
        ])

    @mock.patch("os.path.isfile", return_value=False)
    @mock.patch("rally.common.version.database_revision",
                return_value={"revision": "spam", "current_head": "foobar"})
    @mock.patch("rally.common.version.version_string", return_value="0.0.0")
    @mock.patch("rally.api.CONF", spec=cfg.CONF)
    def test_init_check_revision_exception(self, mock_conf,
                                           mock_version_string,
                                           mock_database_revision,
                                           mock_isfile):
        exc = self.assertRaises(exceptions.RallyException, api.API)
        self.assertIn("rally-manage db upgrade", str(exc))
        mock_conf.assert_called_once_with(
            [], default_config_files=None, project="rally", version="0.0.0")

    @mock.patch("os.path.isfile", return_value=False)
    @mock.patch("rally.common.version.database_revision",
                return_value={"revision": None, "current_head": "foobar"})
    @mock.patch("rally.common.version.version_string", return_value="0.0.0")
    @mock.patch("rally.api.CONF", spec=cfg.CONF)
    def test_init_check_revision_exception_no_db(self, mock_conf,
                                                 mock_version_string,
                                                 mock_database_revision,
                                                 mock_isfile):
        exc = self.assertRaises(exceptions.RallyException, api.API)
        self.assertIn("rally-manage db create", str(exc))
        mock_conf.assert_called_once_with(
            [], default_config_files=None, project="rally", version="0.0.0")

    def test_init_rally_endpoint(self):
        self.assertRaises(NotImplementedError, api.API, rally_endpoint="foo")


class FakeVerifierManager(object):
    NAME = "fake_verifier"
    NAMESPACE = "tests"
    TITLE = "Fake verifier which is used only for testing purpose"

    @classmethod
    def get_name(cls):
        return cls.NAME

    @classmethod
    def get_namespace(cls):
        return cls.NAMESPACE

    @classmethod
    def get_info(cls):
        return {"title": cls.TITLE}


class VerifierAPITestCase(test.TestCase):

    def setUp(self):
        super(VerifierAPITestCase, self).setUp()
        self.verifier_inst = api._Verifier(mock.Mock())

    @mock.patch("rally.api.vmanager.VerifierManager.get_all")
    def test_list_plugins(self, mock_verifier_manager_get_all):
        mock_verifier_manager_get_all.return_value = [FakeVerifierManager]
        namespace = "some"

        self.assertEqual(
            [{"name": FakeVerifierManager.NAME,
              "namespace": FakeVerifierManager.NAMESPACE,
              "description": FakeVerifierManager.TITLE,
              "location": "%s.%s" % (FakeVerifierManager.__module__,
                                     FakeVerifierManager.__name__)}],
            self.verifier_inst.list_plugins(namespace))
        mock_verifier_manager_get_all.assert_called_once_with(
            namespace=namespace)

    @mock.patch("rally.api.objects.Verifier.get")
    def test_get(self, mock_verifier_get):
        uuid = "some"

        self.assertEqual(mock_verifier_get.return_value.to_dict(),
                         self.verifier_inst.get(uuid))

        mock_verifier_get.assert_called_once_with(uuid)

    @mock.patch("rally.api.objects.Verifier.list")
    def test_list(self, mock_verifier_list):
        status = "some_special_status"
        mock_verifier_list.return_value = [mock.Mock()]

        self.assertEqual(
            [i.to_dict() for i in mock_verifier_list.return_value],
            self.verifier_inst.list(status))

        mock_verifier_list.assert_called_once_with(status)

    @mock.patch("rally.api.objects.Verifier.create")
    @mock.patch("rally.api._Verifier._get")
    @mock.patch("rally.api.vmanager.VerifierManager.get")
    def test_create(self, mock_verifier_manager_get, mock___verifier__get,
                    mock_verifier_create):
        mock___verifier__get.side_effect = exceptions.ResourceNotFound(id="1")

        name = "SomeVerifier"
        vtype = "fake_verifier"
        namespace = "tests"
        source = "https://example.com"
        version = "3.1415"
        system_wide = True
        extra_settings = {"verifier_specific_option": "value_for_it"}

        verifier_obj = mock_verifier_create.return_value
        verifier_obj.manager._meta_get.side_effect = [namespace, source]

        verifier_uuid = self.verifier_inst.create(
            name, vtype=vtype, version=version, system_wide=system_wide,
            extra_settings=extra_settings)

        mock_verifier_manager_get.assert_called_once_with(vtype,
                                                          namespace=None)
        mock___verifier__get.assert_called_once_with(name)
        mock_verifier_create.assert_called_once_with(
            name=name, source=None, system_wide=system_wide, version=version,
            vtype=vtype, namespace=None, extra_settings=extra_settings)

        self.assertEqual(verifier_obj.uuid, verifier_uuid)
        verifier_obj.update_properties.assert_called_once_with(
            namespace=namespace, source=source)
        self.assertEqual([mock.call(consts.VerifierStatus.INSTALLING),
                          mock.call(consts.VerifierStatus.INSTALLED)],
                         verifier_obj.update_status.call_args_list)
        verifier_obj.manager.install.assert_called_once_with()

    @mock.patch("rally.api.objects.Verifier.create")
    @mock.patch("rally.api._Verifier._get")
    @mock.patch("rally.api.vmanager.VerifierManager.get")
    def test_create_fails_on_existing_verifier(
            self, mock_verifier_manager_get, mock___verifier__get,
            mock_verifier_create):
        name = "SomeVerifier"
        vtype = "fake_verifier"
        namespace = "tests"
        source = "https://example.com"
        version = "3.1415"
        system_wide = True
        extra_settings = {"verifier_specific_option": "value_for_it"}

        self.assertRaises(exceptions.RallyException,
                          self.verifier_inst.create,
                          name=name, vtype=vtype, namespace=namespace,
                          source=source, version=version,
                          system_wide=system_wide,
                          extra_settings=extra_settings)

        mock_verifier_manager_get.assert_called_once_with(vtype,
                                                          namespace=namespace)
        mock___verifier__get.assert_called_once_with(name)
        self.assertFalse(mock_verifier_create.called)

    @mock.patch("rally.api.objects.Verifier.create")
    @mock.patch("rally.api._Verifier._get")
    @mock.patch("rally.api.vmanager.VerifierManager.get")
    def test_create_fails_on_install_step(
            self, mock_verifier_manager_get, mock___verifier__get,
            mock_verifier_create):
        mock___verifier__get.side_effect = exceptions.ResourceNotFound(id="1")
        verifier_obj = mock_verifier_create.return_value
        verifier_obj.manager.install.side_effect = RuntimeError

        name = "SomeVerifier"
        vtype = "fake_verifier"
        namespace = "tests"
        source = "https://example.com"
        version = "3.1415"
        system_wide = True
        extra_settings = {"verifier_specific_option": "value_for_it"}

        self.assertRaises(RuntimeError, self.verifier_inst.create,
                          name=name, vtype=vtype, namespace=namespace,
                          source=source, version=version,
                          system_wide=system_wide,
                          extra_settings=extra_settings)

        mock_verifier_manager_get.assert_called_once_with(vtype,
                                                          namespace=namespace)
        mock___verifier__get.assert_called_once_with(name)
        mock_verifier_create.assert_called_once_with(
            name=name, source=source, system_wide=system_wide, version=version,
            vtype=vtype, namespace=namespace, extra_settings=extra_settings)

        self.assertEqual([mock.call(consts.VerifierStatus.INSTALLING),
                          mock.call(consts.VerifierStatus.FAILED)],
                         verifier_obj.update_status.call_args_list)
        verifier_obj.manager.install.assert_called_once_with()

    @mock.patch("rally.api.objects.Verifier.delete")
    @mock.patch("rally.common.objects.Verifier.get")
    def test_delete_no_verifications(self, mock_verifier_get,
                                     mock_verifier_delete):
        self.verifier_inst.api.verification.list
        self.verifier_inst.api.verification.list.return_value = []
        verifier_obj = mock_verifier_get.return_value

        verifier_id = "uuuiiiddd"
        deployment_id = "deployment"

        # remove just deployment specific data
        self.verifier_inst.delete(verifier_id, deployment_id=deployment_id)

        self.assertFalse(mock_verifier_delete.called)
        self.verifier_inst.api.verification.list.assert_called_once_with(
            verifier_id, deployment_id)
        verifier_obj.set_deployment.assert_called_once_with(deployment_id)
        verifier_obj.manager.uninstall.assert_called_once_with()

        verifier_obj.set_deployment.reset_mock()
        verifier_obj.manager.uninstall.reset_mock()

        self.verifier_inst.api.verification.list.reset_mock()

        # remove the whole verifier
        self.verifier_inst.delete(verifier_id)

        self.verifier_inst.api.verification.list.assert_called_once_with(
            verifier_id, None)
        self.assertFalse(verifier_obj.set_deployment.called)
        verifier_obj.manager.uninstall.assert_called_once_with(full=True)
        mock_verifier_delete.assert_called_once_with(verifier_id)

    @mock.patch("rally.common.objects.Verifier.get")
    @mock.patch("rally.api.objects.Verifier.delete")
    def test_delete_with_verifications(self,
                                       mock_verifier_delete,
                                       mock_verifier_get):
        verifications = [{"uuid": "uuid_1"}, {"uuid": "uuid_2"}]
        verifier_id = "uuuiiiddd"

        self.assertRaises(exceptions.RallyException,
                          self.verifier_inst.delete,
                          verifier_id)

        self.verifier_inst.api.verification.list.assert_called_once_with(
            verifier_id, None)
        self.assertFalse(self.verifier_inst.api.verification.delete.called)

        self.verifier_inst.api.reset_mock()
        self.verifier_inst.api.verification.list.return_value = verifications

        self.verifier_inst.delete(verifier_id, force=True)
        self.verifier_inst.api.verification.list.assert_called_once_with(
            verifier_id, None)
        self.assertEqual(
            [mock.call(v["uuid"]) for v in verifications],
            self.verifier_inst.api.verification.delete.call_args_list)

    @mock.patch("rally.api.utils.BackupHelper")
    @mock.patch("rally.api._Verifier._get")
    def test_update_failed(self, mock___verifier__get, mock_backup_helper):
        verifier_obj = mock___verifier__get.return_value
        verifier_obj.system_wide = False
        uuid = "uuuuiiiidddd"
        e = self.assertRaises(exceptions.RallyException,
                              self.verifier_inst.update,
                              uuid)
        self.assertIn("At least one of the following parameters should be",
                      "%s" % e)
        for status in consts.VerifierStatus:
            if status != consts.VerifierStatus.INSTALLED:
                verifier_obj.status = status
                e = self.assertRaises(exceptions.RallyException,
                                      self.verifier_inst.update,
                                      uuid, system_wide=True)
                self.assertIn("because verifier is in '%s' status" % status,
                              "%s" % e)

        verifier_obj.status = consts.VerifierStatus.INSTALLED
        msg = "It is impossible to update the virtual environment for verifier"
        e = self.assertRaises(exceptions.RallyException,
                              self.verifier_inst.update,
                              uuid, system_wide=True, update_venv=True)
        self.assertIn(msg, "%s" % e)
        verifier_obj.system_wide = True
        e = self.assertRaises(exceptions.RallyException,
                              self.verifier_inst.update,
                              uuid, update_venv=True)
        self.assertIn(msg, "%s" % e)

    @mock.patch("rally.api.utils.BackupHelper")
    @mock.patch("rally.api._Verifier._get")
    def test_update(self, mock___verifier__get, mock_backup_helper):
        verifier_obj = mock___verifier__get.return_value
        verifier_obj.system_wide = False
        verifier_obj.status = consts.VerifierStatus.INSTALLED
        uuid = "uuuuiiiidddd"
        version = "3.1415"

        # check updating just version
        self.verifier_inst.update(uuid, version=version)
        verifier_obj.manager.checkout.assert_called_once_with(version)
        self.assertFalse(verifier_obj.manager.check_system_wide.called)
        verifier_obj.update_properties.assert_called_once_with(
            status=verifier_obj.status, version=version)
        verifier_obj.update_status.assert_called_once_with(
            consts.VerifierStatus.UPDATING)
        self.assertFalse(verifier_obj.manager.install_venv.called)

        verifier_obj.manager.checkout.reset_mock()
        verifier_obj.manager.check_system_wide.reset_mock()
        verifier_obj.update_properties.reset_mock()
        verifier_obj.update_status.reset_mock()

        # check system_wide
        self.verifier_inst.update(uuid, version=version, system_wide=True)

        verifier_obj.manager.checkout.assert_called_once_with(version)
        verifier_obj.manager.check_system_wide.assert_called_once_with()
        verifier_obj.update_properties.assert_called_once_with(
            status=verifier_obj.status, version=version, system_wide=True)
        verifier_obj.update_status.assert_called_once_with(
            consts.VerifierStatus.UPDATING)
        self.assertFalse(verifier_obj.manager.install_venv.called)

        verifier_obj.manager.checkout.reset_mock()
        verifier_obj.manager.check_system_wide.reset_mock()
        verifier_obj.update_properties.reset_mock()
        verifier_obj.update_status.reset_mock()

        # check switching from system-wide to virtual environment
        verifier_obj.system_wide = True

        self.verifier_inst.update(uuid, system_wide=False)
        verifier_obj.manager.install_venv.assert_called_once_with()
        self.assertFalse(verifier_obj.manager.check_system_wide.called)
        verifier_obj.update_status.assert_called_once_with(
            consts.VerifierStatus.UPDATING)
        verifier_obj.update_properties.assert_called_once_with(
            status=verifier_obj.status, system_wide=False)

        verifier_obj.manager.check_system_wide.reset_mock()
        verifier_obj.update_properties.reset_mock()
        verifier_obj.update_status.reset_mock()
        verifier_obj.manager.install_venv.reset_mock()

        # check updating virtual environment
        verifier_obj.system_wide = False

        self.verifier_inst.update(uuid, update_venv=True)
        verifier_obj.manager.install_venv.assert_called_once_with()
        self.assertFalse(verifier_obj.manager.check_system_wide.called)
        verifier_obj.update_status.assert_called_once_with(
            consts.VerifierStatus.UPDATING)
        verifier_obj.update_properties.assert_called_once_with(
            status=verifier_obj.status)

        verifier_obj.manager.check_system_wide.reset_mock()
        verifier_obj.update_properties.reset_mock()
        verifier_obj.update_status.reset_mock()
        verifier_obj.manager.install_venv.reset_mock()

        # check switching from virtual environment to system-wide
        verifier_obj.system_wide = False

        self.verifier_inst.update(uuid, system_wide=True)
        self.assertFalse(verifier_obj.manager.install_venv.called)
        verifier_obj.manager.check_system_wide.assert_called_once_with()
        verifier_obj.update_status.assert_called_once_with(
            consts.VerifierStatus.UPDATING)
        verifier_obj.update_properties.assert_called_once_with(
            status=verifier_obj.status, system_wide=True)

        # check switching from system-wide to system-wide
        verifier_obj.system_wide = True
        expected_calls = len(verifier_obj.update_status.call_args())
        self.verifier_inst.update(uuid, system_wide=True)
        self.assertTrue(expected_calls,
                        len(verifier_obj.update_status.call_args()))
        self.assertFalse(verifier_obj.manager.install_venv.called)

    @mock.patch("rally.api._Verifier._get")
    def test_configure_with_wrong_state_of_verifier(self,
                                                    mock___verifier__get):
        verifier_obj = mock___verifier__get.return_value
        verifier_id = "uuiiiidd"
        deployment_id = "deployment"
        for status in consts.VerifierStatus:
            if status != consts.VerifierStatus.INSTALLED:
                verifier_obj.status = status
                e = self.assertRaises(exceptions.RallyException,
                                      self.verifier_inst.configure,
                                      verifier_id, deployment_id)
                self.assertIn("because verifier is in '%s' status" % status,
                              "%s" % e)

    @mock.patch("rally.cli.commands.verify.logging.is_debug",
                return_value=False)
    @mock.patch("rally.plugins.openstack.verification.tempest.manager."
                "os.path.exists")
    @mock.patch("rally.api._Verifier._get")
    def test_configure_when_it_is_already_configured(self,
                                                     mock___verifier__get,
                                                     mock_exists,
                                                     mock_is_debug):
        verifier_obj = mock___verifier__get.return_value
        verifier_id = "uuiiiidd"
        deployment_id = "deployment"
        extra = {"key": "value"}
        verifier_obj.status = consts.VerifierStatus.INSTALLED

        # no recreate and no extra options
        self.assertEqual(verifier_obj.manager.get_configuration.return_value,
                         self.verifier_inst.configure(
                             verifier_id, deployment_id, reconfigure=False))
        self.assertFalse(verifier_obj.manager.extend_configuration.called)
        self.assertFalse(verifier_obj.manager.configure.called)
        self.assertFalse(verifier_obj.update_status.called)

        # no recreate, just extend existing configuration
        self.assertEqual(verifier_obj.manager.get_configuration.return_value,
                         self.verifier_inst.configure(
                             verifier_id, deployment_id, reconfigure=False,
                             extra_options=extra))
        verifier_obj.manager.extend_configuration.assert_called_once_with(
            extra)
        self.assertFalse(verifier_obj.manager.configure.called)

        verifier_obj.update_status.reset_mock()
        verifier_obj.manager.extend_configuration.reset_mock()

        # recreate with extra options
        self.assertEqual(verifier_obj.manager.configure.return_value,
                         self.verifier_inst.configure(
                             verifier_id, deployment_id,
                             reconfigure=True,
                             extra_options=extra))
        self.assertFalse(verifier_obj.manager.extend_configuration.called)
        verifier_obj.manager.configure.asset_called_once_with(
            extra_options=extra)

        verifier_obj.update_status.reset_mock()
        verifier_obj.manager.extend_configuration.reset_mock()

    @mock.patch("rally.cli.commands.verify.logging.is_debug",
                return_value=True)
    @mock.patch("rally.plugins.openstack.verification.tempest.manager."
                "os.path.exists")
    @mock.patch("rally.api._Verifier._get")
    def test_configure_when_it_is_already_configured_with_logging(
            self, mock___verifier__get, mock_exists, mock_is_debug):
        verifier_obj = mock___verifier__get.return_value
        verifier_id = "uuiiiidd"
        deployment_id = "deployment"
        extra = {"key": "value"}
        verifier_obj.status = consts.VerifierStatus.INSTALLED

        # no recreate and no extra options
        self.assertEqual(verifier_obj.manager.get_configuration.return_value,
                         self.verifier_inst.configure(
                             verifier_id, deployment_id, reconfigure=False))
        self.assertFalse(verifier_obj.manager.extend_configuration.called)
        self.assertFalse(verifier_obj.manager.configure.called)
        self.assertFalse(verifier_obj.update_status.called)

        # no recreate, just extend existing configuration
        self.assertEqual(verifier_obj.manager.get_configuration.return_value,
                         self.verifier_inst.configure(
                             verifier_id, deployment_id,
                             reconfigure=False,
                             extra_options=extra))
        verifier_obj.manager.extend_configuration.assert_called_once_with(
            extra)
        self.assertFalse(verifier_obj.manager.configure.called)

        verifier_obj.update_status.reset_mock()
        verifier_obj.manager.extend_configuration.reset_mock()

        # recreate with extra options
        self.assertEqual(verifier_obj.manager.configure.return_value,
                         self.verifier_inst.configure(
                             verifier_id, deployment_id,
                             reconfigure=True,
                             extra_options=extra))
        self.assertFalse(verifier_obj.manager.extend_configuration.called)
        verifier_obj.manager.configure.asset_called_once_with(
            extra_options=extra)

        verifier_obj.update_status.reset_mock()
        verifier_obj.manager.extend_configuration.reset_mock()

    @mock.patch("rally.api._Verifier._get")
    def test_override_config_with_wrong_state_of_verifier(
            self, mock___verifier__get):
        verifier_obj = mock___verifier__get.return_value
        verifier_id = "uuiiiidd"
        deployment_id = "deployment"
        new_content = {}

        for status in consts.VerifierStatus:
            if status != consts.VerifierStatus.INSTALLED:
                verifier_obj.status = status
                e = self.assertRaises(
                    exceptions.RallyException,
                    self.verifier_inst.override_configuration,
                    verifier_id, deployment_id, new_content)
                self.assertIn("because verifier %s is in '%s' status"
                              % (verifier_obj, status), "%s" % e)

    @mock.patch("rally.plugins.openstack.verification.tempest.manager."
                "os.path.exists")
    @mock.patch("rally.api._Verifier._get")
    def test_override_config_when_it_is_already_configured(
            self, mock___verifier__get, mock_exists):
        verifier_obj = mock___verifier__get.return_value
        verifier_id = "uuiiiidd"
        deployment_id = "deployment"
        new_config = {"key": "value"}
        verifier_obj.status = consts.VerifierStatus.INSTALLED
        self.verifier_inst.override_configuration(
            verifier_id, deployment_id, new_configuration=new_config)
        verifier_obj.manager.override_configuration.assert_called_once_with(
            new_config)

    @mock.patch("rally.api._Verifier._get")
    def test_list_tests(self, mock___verifier__get):
        verifier_obj = mock___verifier__get.return_value
        verifier_id = "uuiiiidd"
        pattern = "some"
        verifier_obj.status = consts.VerifierStatus.INIT

        e = self.assertRaises(exceptions.RallyException,
                              self.verifier_inst.list_tests,
                              verifier_id,
                              pattern=pattern)
        self.assertIn("because verifier %s is in '%s' status"
                      % (verifier_obj, verifier_obj.status), "%s" % e)
        self.assertFalse(verifier_obj.manager.list_tests.called)

        verifier_obj.status = consts.VerifierStatus.INSTALLED
        self.assertEqual(
            verifier_obj.manager.list_tests.return_value,
            self.verifier_inst.list_tests(verifier_id, pattern))
        verifier_obj.manager.list_tests.assert_called_once_with(pattern)

    @mock.patch("rally.api._Verifier._get")
    def test_add_extension(self, mock___verifier__get):
        verifier_obj = mock___verifier__get.return_value
        verifier_id = "uuiiiidd"
        source = "example.com"
        version = 3.14159
        extra_settings = {}

        for status in consts.VerifierStatus:
            if status != consts.VerifierStatus.INSTALLED:
                verifier_obj.status = status
                e = self.assertRaises(exceptions.RallyException,
                                      self.verifier_inst.add_extension,
                                      verifier_id, source, version=version,
                                      extra_settings=extra_settings)
                self.assertIn("because verifier %s is in '%s' status"
                              % (verifier_obj, status), "%s" % e)

        verifier_obj.status = consts.VerifierStatus.INSTALLED
        self.verifier_inst.add_extension(
            verifier_id, source, version=version,
            extra_settings=extra_settings)
        verifier_obj.manager.install_extension.assert_called_once_with(
            source, version=version, extra_settings=extra_settings)
        self.assertEqual([mock.call(consts.VerifierStatus.EXTENDING),
                          mock.call(verifier_obj.status)],
                         verifier_obj.update_status.call_args_list)

        # check status will be updated in case of failure at installation step
        verifier_obj.update_status.reset_mock()

        verifier_obj.manager.install_extension.side_effect = RuntimeError
        self.assertRaises(RuntimeError,
                          self.verifier_inst.add_extension,
                          verifier_id, source, version=version,
                          extra_settings=extra_settings)
        self.assertEqual([mock.call(consts.VerifierStatus.EXTENDING),
                          mock.call(verifier_obj.status)],
                         verifier_obj.update_status.call_args_list)

    @mock.patch("rally.api._Verifier._get")
    def test_list_extensions(self, mock___verifier__get):
        verifier_obj = mock___verifier__get.return_value
        verifier_id = "uuiiiidd"

        for status in consts.VerifierStatus:
            if status != consts.VerifierStatus.INSTALLED:
                verifier_obj.status = status
                e = self.assertRaises(exceptions.RallyException,
                                      self.verifier_inst.list_extensions,
                                      verifier_id)
                self.assertIn("because verifier %s is in '%s' status"
                              % (verifier_obj, status), "%s" % e)
                self.assertFalse(verifier_obj.manager.list_extensions.called)

        verifier_obj.status = consts.VerifierStatus.INSTALLED
        self.assertEqual(verifier_obj.manager.list_extensions.return_value,
                         self.verifier_inst.list_extensions(verifier_id))
        verifier_obj.manager.list_extensions.assert_called_once_with()

    @mock.patch("rally.api._Verifier._get")
    def test_delete_extension(self, mock___verifier__get):
        verifier_obj = mock___verifier__get.return_value
        verifier_id = "uuiiiidd"
        name = "some"

        for status in consts.VerifierStatus:
            if status != consts.VerifierStatus.INSTALLED:
                verifier_obj.status = status
                e = self.assertRaises(exceptions.RallyException,
                                      self.verifier_inst.delete_extension,
                                      verifier_id, name)
                self.assertIn("because verifier %s is in '%s' status"
                              % (verifier_obj, status), "%s" % e)
                self.assertFalse(verifier_obj.manager.list_tests.called)

        verifier_obj.status = consts.VerifierStatus.INSTALLED
        self.verifier_inst.delete_extension(verifier_id, name)
        verifier_obj.manager.uninstall_extension.assert_called_once_with(name)


class VerificationAPITestCase(test.TestCase):

    results_data = {
        "totals": {"tests_count": 2,
                   "tests_duration": 4,
                   "success": 2,
                   "skipped": 0,
                   "expected_failures": 0,
                   "unexpected_success": 0,
                   "failures": 0},
        "tests": {
            "test_1": {
                "name": "test_1",
                "status": "success",
                "duration": 2,
                "tags": []}
        }
    }

    def setUp(self):
        super(VerificationAPITestCase, self).setUp()
        self.verification_inst = api._Verification(mock.Mock())

    @mock.patch("rally.api.objects.Verification.get")
    def test_get(self, mock_verification_get):
        verification_uuid = "uuiiiidd"
        self.assertEqual(mock_verification_get.return_value.to_dict(),
                         self.verification_inst.get(verification_uuid))
        mock_verification_get.assert_called_once_with(verification_uuid)

    @mock.patch("rally.api.objects.Verification.get")
    def test_delete(self, mock_verification_get):
        verification_uuid = "uuiiiidd"
        self.verification_inst.delete(verification_uuid)
        mock_verification_get.assert_called_once_with(verification_uuid)
        mock_verification_get.return_value.delete.assert_called_once_with()

    @mock.patch("rally.api.objects.Verification.list")
    def test_list(self, mock_verification_list):
        verifier_id = "vuuuiiddd"
        deployment_id = "duuuiidd"
        tags = ["foo", "bar"]
        status = "some_status"

        mock_verification_list.return_value = [mock.Mock()]
        self.assertEqual(
            [i.to_dict() for i in mock_verification_list.return_value],
            self.verification_inst.list(
                verifier_id, deployment_id=deployment_id,
                tags=tags, status=status))
        mock_verification_list.assert_called_once_with(
            verifier_id, deployment_id=deployment_id, tags=tags, status=status)

    @mock.patch("rally.api.vreporter.VerificationReporter")
    @mock.patch("rally.api.objects.Verification.get")
    def test_report(self, mock_verification_get, mock_verification_reporter):
        verifications = ["uuid-1", "uuid-2"]
        output_type = mock.Mock()
        output_dest = mock.Mock()

        reporter = mock_verification_reporter.get.return_value

        self.assertEqual(mock_verification_reporter.make.return_value,
                         self.verification_inst.report(
                             verifications, output_type=output_type,
                             output_dest=output_dest))
        mock_verification_reporter.get.assert_called_once_with(output_type)

        reporter.validate.assert_called_once_with(output_dest)

        mock_verification_reporter.make.assert_called_once_with(
            reporter, [mock_verification_get.return_value,
                       mock_verification_get.return_value],
            output_dest)
        self.assertEqual([mock.call(u) for u in verifications],
                         mock_verification_get.call_args_list)

    @mock.patch("rally.api.objects.Verification.create")
    @mock.patch("rally.api._Verifier._get")
    def test_import_results(self, mock___verifier__get,
                            mock_verification_create):
        verifier_id = "vuuuiiddd"
        deployment_id = "duuuiidd"
        data = "contest of file with results"
        run_args = {"set_name": "compute"}

        # verifier_obj = mock___verifier__get.return_value
        verifier_obj = self.verification_inst.api.verifier._get.return_value
        verifier_obj.deployment = {
            "name": "deployment_name",
            "uuid": deployment_id}

        results = self.verification_inst.import_results(
            verifier_id, deployment_id=deployment_id, data=data, **run_args)

        verification = mock_verification_create.return_value

        self.assertEqual(verification.to_dict(), results["verification"])
        self.assertEqual(
            verifier_obj.manager.parse_results.return_value.totals,
            results["totals"])
        self.verification_inst.api.verifier._get.assert_called_once_with(
            verifier_id)
        verifier_obj.set_deployment.assert_called_once_with(deployment_id)
        verifier_obj.manager.validate_args.assert_called_once_with(run_args)
        mock_verification_create.assert_called_once_with(
            verifier_id, deployment_id=deployment_id, run_args=run_args)
        verification.update_status.assert_called_once_with(
            consts.VerificationStatus.RUNNING)
        verifier_obj.manager.parse_results.assert_called_once_with(data)
        verification.finish.assert_called_once_with(results["totals"],
                                                    results["tests"])

        # check setting failed
        verification.finish.reset_mock()

        verifier_obj.manager.parse_results.side_effect = RuntimeError
        self.assertRaises(RuntimeError, self.verification_inst.import_results,
                          verifier_id, deployment_id=deployment_id, data=data,
                          **run_args)
        self.assertFalse(verification.finish.called)
        self.assertTrue(verification.set_failed.called)

    @mock.patch("rally.api._Verifier._get")
    @mock.patch("rally.api.objects.Deployment.get",
                return_value=fakes.FakeDeployment(
                    uuid="deployment_uuid",
                    status=consts.DeployStatus.DEPLOY_FINISHED))
    def test_start_failed_due_to_wrong_status_of_verifier(
            self, mock_deployment_get, mock___verifier__get):
        verifier_id = "vuuuiiddd"
        deployment_id = "duuuiidd"
        verifier_obj = self.verification_inst.api.verifier._get.return_value

        for status in consts.VerifierStatus:
            if status != consts.VerifierStatus.INSTALLED:
                verifier_obj.status = status
                e = self.assertRaises(exceptions.RallyException,
                                      self.verification_inst.start,
                                      verifier_id, deployment_id)
                self.assertIn(
                    "Failed to start verification because verifier %s is in "
                    "'%s' status" % (verifier_obj, verifier_obj.status),
                    "%s" % e)

    @mock.patch("rally.api.objects.Verification.create")
    @mock.patch("rally.api.objects.Deployment.get",
                return_value=fakes.FakeDeployment(
                    uuid="deployment_uuid",
                    status=consts.DeployStatus.DEPLOY_FINISHED))
    def test_start_with_configuring(self, mock_deployment_get,
                                    mock_verification_create):
        verifier_id = "vuuuiiddd"
        deployment_id = "duuuiidd"
        verifier_obj = self.verification_inst.api.verifier._get.return_value
        verifier_obj.status = consts.VerifierStatus.INSTALLED
        verifier_obj.deployment = {
            "name": "deployment_name",
            "uuid": "deployment_uuid",
            "status": consts.DeployStatus.DEPLOY_FINISHED}
        verifier_manager = mock.Mock()
        verifier_obj.manager = verifier_manager
        verifier_manager._meta_get.return_value = {}

        self.verification_inst.start(verifier_id, deployment_id)
        mock_deployment_get.assert_called_once_with(deployment_id)
        verifier_obj.set_deployment.assert_called_once_with(deployment_id)

    @mock.patch("rally.api.objects.Verification.create")
    @mock.patch("rally.api._Verifier.configure")
    @mock.patch("rally.api.objects.Deployment.get",
                return_value=fakes.FakeDeployment(
                    uuid="deployment_uuid",
                    status=consts.DeployStatus.DEPLOY_FINISHED))
    def test_start(self, mock_deployment_get, mock_configure,
                   mock_verification_create):
        verifier_id = "vuuuiiddd"
        deployment_id = "duuuiidd"
        tags = ["foo", "bar"]
        run_args = {"arg": "value"}
        verifier_obj = self.verification_inst.api.verifier._get.return_value
        verifier_obj.status = consts.VerifierStatus.INSTALLED
        verification_obj = mock_verification_create.return_value
        verifier_obj.deployment = {"name": "deployment_name",
                                   "uuid": deployment_id}
        verifier_obj.manager._meta_get.return_value = {}

        self.verification_inst.start(verifier_id, deployment_id, tags=tags,
                                     **run_args)

        mock_deployment_get.assert_called_once_with(deployment_id)
        verifier_obj.set_deployment.assert_called_once_with(deployment_id)
        verifier_obj.manager.validate.assert_called_once_with(run_args)

        mock_verification_create.assert_called_once_with(
            verifier_id=verifier_id, deployment_id=deployment_id, tags=tags,
            run_args=run_args)
        verification_obj.update_status.assert_called_once_with(
            consts.VerificationStatus.RUNNING)

        context = {"config": verifier_obj.manager._meta_get.return_value,
                   "run_args": run_args,
                   "verification": verification_obj,
                   "verifier": verifier_obj}
        verifier_obj.manager.run.assert_called_once_with(context)

        results = verifier_obj.manager.run.return_value
        verification_obj.finish.assert_called_once_with(results.totals,
                                                        results.tests)

        self.assertFalse(mock_configure.called)

    @mock.patch("rally.api.objects.Deployment.get",
                return_value=fakes.FakeDeployment(
                    name="xxx_name",
                    uuid="deployment_uuid",
                    status=consts.DeployStatus.DEPLOY_INIT))
    def test_start_on_unfinished_deployment(self, mock_deployment_get):
        verifier_id = "v_id"
        deployment_id = mock_deployment_get.return_value["uuid"]
        tags = ["foo", "bar"]
        run_args = {"arg": "value"}
        self.assertRaises(exceptions.DeploymentNotFinishedStatus,
                          self.verification_inst.start, verifier_id,
                          deployment_id, tags=tags, **run_args)

    @mock.patch("rally.api.objects.Verification.create")
    @mock.patch("rally.api.objects.Deployment.get",
                return_value=fakes.FakeDeployment(
                    uuid="deployment_uuid",
                    status=consts.DeployStatus.DEPLOY_FINISHED))
    def test_start_failed_to_run(self, mock_deployment_get,
                                 mock_verification_create):
        verifier_id = "vuuuiiddd"
        deployment_id = "duuuiidd"
        tags = ["foo", "bar"]
        run_args = {"arg": "value"}
        verifier_obj = self.verification_inst.api.verifier._get.return_value
        verifier_obj.deployment = {"name": "deployment_name",
                                   "uuid": deployment_id}
        verifier_obj.status = consts.VerifierStatus.INSTALLED
        verification_obj = mock_verification_create.return_value
        verifier_manager = mock.Mock()
        verifier_obj.manager = verifier_manager
        verifier_manager._meta_get.return_value = {}
        verifier_obj.manager.run.side_effect = RuntimeError

        self.assertRaises(RuntimeError, self.verification_inst.start,
                          verifier_id, deployment_id, tags=tags, **run_args)

        verifier_obj.set_deployment.assert_called_once_with(deployment_id)
        verifier_obj.manager.validate.assert_called_once_with(run_args)
        mock_verification_create.assert_called_once_with(
            verifier_id=verifier_id, deployment_id=deployment_id, tags=tags,
            run_args=run_args)
        verification_obj.update_status.assert_called_once_with(
            consts.VerificationStatus.RUNNING)

        context = {"config": verifier_obj.manager._meta_get.return_value,
                   "run_args": run_args,
                   "verification": verification_obj,
                   "verifier": verifier_obj}
        verifier_obj.manager.run.assert_called_once_with(context)

        self.assertFalse(verification_obj.finish.called)

        self.assertFalse(
            self.verification_inst.api.verifier.configure.called)

    @mock.patch("rally.api._Verification.start")
    @mock.patch("rally.api._Deployment.get")
    @mock.patch("rally.api._Verification._get")
    def test_rerun(self, mock___verification__get, mock___deployment_get,
                   mock_start):

        tests = {"test_1": {"status": "success"},
                 "test_2": {"status": "fail"}}
        mock___verification__get.return_value = mock.Mock(
            uuid="uuid", verifier_uuid="v_uuid", deployment_uuid="d_uuid",
            tests=tests)
        self.verification_inst.api.deployment.get.return_value = {
            "name": "d_name",
            "uuid": "d_uuid"}
        mock___deployment_get.return_value = {"name": "d_name",
                                              "uuid": "d_uuid"}
        mock_start.return_value = (
            mock___verification__get.return_value,
            mock.Mock(totals=self.results_data["totals"],
                      tests=self.results_data["tests"]))

        self.verification_inst.rerun("uuid", concurrency=1)
        mock_start.assert_called_once_with(
            "v_uuid", "d_uuid", load_list=tests.keys(),
            tags=None, concurrency=1)

    @mock.patch("rally.api._Verification.start")
    @mock.patch("rally.api.objects.Verification.create")
    @mock.patch("rally.common.objects.Verification.get")
    def test_rerun_failed_tests(self,
                                mock_verification_get,
                                mock_verification_create,
                                mock_start):
        tests = {"test_1": {"status": "success"},
                 "test_2": {"status": "fail"},
                 "test_3": {"status": "fail"}}
        mock_verification_get.return_value = mock.Mock(
            uuid="uuid", verifier_uuid="v_uuid", deployment_uuid="d_uuid",
            tests=tests)
        self.verification_inst.return_value = mock.Mock()
        self.verification_inst.api.deployment.get.return_value = {
            "name": "deployment_name",
            "uuid": "deployment_uuid",
        }
        expected_tests = [t for t, r in tests.items() if r["status"] == "fail"]
        self.verification_inst.rerun("uuid", failed=True)
        mock_start.assert_called_once_with(
            "v_uuid", "deployment_uuid", load_list=expected_tests, tags=None)

    @mock.patch("rally.api._Verification._get")
    def test_rerun_failed_tests_raise_exc(
            self, mock___verification__get):
        tests = {"test_1": {"status": "success"},
                 "test_2": {"status": "success"},
                 "test_3": {"status": "skip"}}
        mock___verification__get.return_value = mock.Mock(
            uuid="uuid", verifier_uuid="v_uuid", deployment_uuid="d_uuid",
            tests=tests)

        e = self.assertRaises(exceptions.RallyException,
                              self.verification_inst.rerun, "uuid",
                              failed=True)
        self.assertEqual("There are no failed tests from verification "
                         "(UUID=uuid).", "%s" % e)
