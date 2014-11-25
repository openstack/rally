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

""" Test for orchestrator. """


import jsonschema
import mock

from rally import consts
from rally import exceptions
from rally.orchestrator import api
from tests.unit import fakes
from tests.unit import test


FAKE_DEPLOY_CONFIG = {
    # TODO(akscram): A fake engine is more suitable for that.
    "type": "ExistingCloud",
    "auth_url": "http://example.net:5000/v2.0/",
    "admin": {
        "username": "admin",
        "password": "myadminpass",
        "tenant_name": "demo",
        "domain_name": None,
        "project_domain_name": "Default",
        "user_domain_name": "Default"
    },
    "region_name": "RegionOne",
    "endpoint_type": consts.EndpointType.INTERNAL,
    "admin_port": 35357
}


class APITestCase(test.TestCase):

    def setUp(self):
        super(APITestCase, self).setUp()
        self.deploy_config = FAKE_DEPLOY_CONFIG
        self.deploy_uuid = "599bdf1d-fe77-461a-a810-d59b1490f4e3"
        admin_endpoint = FAKE_DEPLOY_CONFIG.copy()
        admin_endpoint.pop("type")
        admin_endpoint.update(admin_endpoint.pop("admin"))
        admin_endpoint["permission"] = consts.EndpointPermission.ADMIN
        self.endpoints = {"admin": admin_endpoint, "users": []}

        self.task_uuid = "b0d9cd6c-2c94-4417-a238-35c7019d0257"
        self.task = {
            "uuid": self.task_uuid,
        }
        self.deployment = {
            "uuid": self.deploy_uuid,
            "name": "fake_name",
            "config": self.deploy_config,
            "admin": self.endpoints["admin"],
            "users": []
        }
        self.tempest = mock.Mock()

    @mock.patch("rally.orchestrator.api.objects.Task")
    @mock.patch("rally.orchestrator.api.objects.Deployment.get",
                return_value=fakes.FakeDeployment(uuid="deploy_uuid",
                                                  admin=mock.MagicMock(),
                                                  users=[]))
    @mock.patch("rally.orchestrator.api.engine.BenchmarkEngine")
    def test_task_validate(self, mock_engine, mock_deployment_get, mock_task):
        api.task_validate(mock_deployment_get.return_value["uuid"], "config")

        mock_engine.assert_has_calls([
            mock.call("config", mock_task.return_value,
                      admin=mock_deployment_get.return_value["admin"],
                      users=[]),
            mock.call().validate()
        ])

        mock_task.assert_called_once_with(
            deployment_uuid=mock_deployment_get.return_value["uuid"])
        mock_deployment_get.assert_called_once_with(
            mock_deployment_get.return_value["uuid"])

    @mock.patch("rally.objects.Deployment.get",
                return_value={'uuid': 'b0d9cd6c-2c94-4417-a238-35c7019d0257'})
    @mock.patch("rally.objects.Task")
    def test_create_task(self, mock_task, mock_d_get):
        tag = "a"
        api.create_task(mock_d_get.return_value["uuid"], tag)
        mock_task.assert_called_once_with(
            deployment_uuid=mock_d_get.return_value["uuid"], tag=tag)

    @mock.patch("rally.orchestrator.api.objects.Task")
    @mock.patch("rally.orchestrator.api.objects.Deployment.get",
                return_value=fakes.FakeDeployment(uuid="deploy_uuid",
                                                  admin=mock.MagicMock(),
                                                  users=[]))
    @mock.patch("rally.orchestrator.api.engine.BenchmarkEngine")
    def test_start_task(self, mock_engine, mock_deployment_get, mock_task):

        api.start_task(mock_deployment_get.return_value["uuid"], "config")

        mock_engine.assert_has_calls([
            mock.call("config", mock_task.return_value,
                      admin=mock_deployment_get.return_value["admin"],
                      users=[]),
            mock.call().validate(),
            mock.call().run(),
        ])

        mock_task.assert_called_once_with(
            deployment_uuid=mock_deployment_get.return_value["uuid"])
        mock_deployment_get.assert_called_once_with(
            mock_deployment_get.return_value["uuid"])

    @mock.patch("rally.orchestrator.api.objects.Task")
    @mock.patch("rally.orchestrator.api.objects.Deployment.get")
    @mock.patch("rally.orchestrator.api.engine.BenchmarkEngine")
    def test_start_task_invalid_task_ignored(self, mock_engine,
                                             mock_deployment_get, mock_task):

        mock_engine().run.side_effect = (
            exceptions.InvalidTaskException())

        # check that it doesn't raise anything
        api.start_task("deploy_uuid", "config")

    @mock.patch("rally.orchestrator.api.objects.Task")
    @mock.patch("rally.orchestrator.api.objects.Deployment.get")
    @mock.patch("rally.orchestrator.api.engine.BenchmarkEngine")
    def test_start_task_exception(self, mock_engine, mock_deployment_get,
                                  mock_task):

        mock_engine().run.side_effect = TypeError
        self.assertRaises(TypeError, api.start_task, "deploy_uuid", "config")
        mock_deployment_get().update_status.assert_called_once_with(
            consts.DeployStatus.DEPLOY_INCONSISTENT)

    def test_abort_task(self):
        self.assertRaises(NotImplementedError, api.abort_task,
                          self.task_uuid)

    @mock.patch("rally.objects.task.db.task_delete")
    def test_delete_task(self, mock_delete):
        api.delete_task(self.task_uuid)
        mock_delete.assert_called_once_with(
            self.task_uuid,
            status=consts.TaskStatus.FINISHED)

    @mock.patch("rally.objects.task.db.task_delete")
    def test_delete_task_force(self, mock_delete):
        api.delete_task(self.task_uuid, force=True)
        mock_delete.assert_called_once_with(self.task_uuid, status=None)

    @mock.patch("rally.objects.deploy.db.deployment_update")
    @mock.patch("rally.objects.deploy.db.deployment_create")
    @mock.patch("rally.deploy.engine.EngineFactory.validate")
    def test_create_deploy(self, mock_validate, mock_create, mock_update):
        mock_create.return_value = self.deployment
        mock_update.return_value = self.deployment
        api.create_deploy(self.deploy_config, "fake_deploy")
        mock_create.assert_called_once_with({
            "name": "fake_deploy",
            "config": self.deploy_config,
        })
        mock_validate.assert_called_with()
        mock_update.assert_has_calls([
            mock.call(self.deploy_uuid, self.endpoints)
        ])

    @mock.patch("rally.objects.deploy.db.deployment_update")
    @mock.patch("rally.objects.deploy.db.deployment_create")
    @mock.patch("rally.deploy.engine.EngineFactory.validate",
                side_effect=jsonschema.ValidationError('ValidationError'))
    def test_create_deploy_validation_error(self, mock_validate, mock_create,
                                            mock_update):
        mock_create.return_value = self.deployment
        self.assertRaises(jsonschema.ValidationError,
                          api.create_deploy,
                          self.deploy_config, "fake_deploy")
        mock_update.assert_called_once_with(
            self.deploy_uuid,
            {'status': consts.DeployStatus.DEPLOY_FAILED})

    @mock.patch("rally.orchestrator.api.LOG")
    @mock.patch("rally.objects.deploy.db.deployment_create",
                side_effect=exceptions.DeploymentNameExists(
                    deployment='fake_deploy'))
    def test_create_deploy_duplication_error(self, mock_d_create,
                                             mock_log):

        self.assertRaises(exceptions.DeploymentNameExists,
                          api.create_deploy, self.deploy_config, "fake_deploy")

    @mock.patch("rally.objects.deploy.db.deployment_delete")
    @mock.patch("rally.objects.deploy.db.deployment_update")
    @mock.patch("rally.objects.deploy.db.deployment_get")
    def test_destroy_deploy(self, mock_get, mock_update, mock_delete):
        mock_get.return_value = self.deployment
        mock_update.return_value = self.deployment
        api.destroy_deploy(self.deploy_uuid)
        mock_get.assert_called_once_with(self.deploy_uuid)
        mock_delete.assert_called_once_with(self.deploy_uuid)

    @mock.patch("rally.objects.deploy.db.deployment_update")
    @mock.patch("rally.objects.deploy.db.deployment_get")
    def test_recreate_deploy(self, mock_get, mock_update):
        mock_get.return_value = self.deployment
        mock_update.return_value = self.deployment
        api.recreate_deploy(self.deploy_uuid)
        mock_get.assert_called_once_with(self.deploy_uuid)
        mock_update.assert_has_calls([
            mock.call(self.deploy_uuid, self.endpoints)
        ])

    @mock.patch("rally.objects.Deployment.get")
    @mock.patch("rally.orchestrator.api.objects.Verification")
    @mock.patch("rally.verification.verifiers.tempest.tempest.Tempest")
    def test_verify(self, mock_tempest, mock_verification, mock_d_get):
        mock_d_get.return_value = {"uuid": self.deploy_uuid}

        mock_tempest.return_value = self.tempest
        self.tempest.is_installed.return_value = True
        api.verify(self.deploy_uuid, "smoke", None, None)

        self.tempest.is_installed.assert_called_once_with()
        self.tempest.verify.assert_called_once_with(set_name="smoke",
                                                    regex=None)

    @mock.patch("rally.orchestrator.api.objects.Deployment.get")
    @mock.patch("rally.orchestrator.api.objects.Verification")
    @mock.patch("rally.verification.verifiers.tempest.tempest.Tempest")
    def test_verify_tempest_not_installed(self, mock_tempest,
                                          mock_verification, mock_d_get):
        mock_d_get.return_value = {"uuid": self.deploy_uuid}
        mock_tempest.return_value = self.tempest
        self.tempest.is_installed.return_value = False
        api.verify(self.deploy_uuid, "smoke", None, None)

        self.tempest.is_installed.assert_called_once_with()
        self.tempest.install.assert_called_once_with()
        self.tempest.verify.assert_called_once_with(set_name="smoke",
                                                    regex=None)
