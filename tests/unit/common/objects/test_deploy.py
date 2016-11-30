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

"""Tests for db.deploy layer."""


import mock

from rally.common import objects
from rally import consts
from tests.unit import test


class DeploymentTestCase(test.TestCase):
    def setUp(self):
        super(DeploymentTestCase, self).setUp()
        self.deployment = {
            "uuid": "baa1bfb6-0c38-4f6c-9bd0-45968890e4f4",
            "name": "",
            "config": {},
            "endpoint": {},
            "status": consts.DeployStatus.DEPLOY_INIT,
        }
        self.resource = {
            "id": 42,
            "deployment_uuid": self.deployment["uuid"],
            "provider_name": "provider",
            "type": "some",
            "info": {"key": "value"},
        }

    @mock.patch("rally.common.objects.deploy.db.deployment_create")
    def test_init_with_create(self, mock_deployment_create):
        mock_deployment_create.return_value = self.deployment
        deploy = objects.Deployment()
        mock_deployment_create.assert_called_once_with({})
        self.assertEqual(deploy["uuid"], self.deployment["uuid"])

    @mock.patch("rally.common.objects.deploy.db.deployment_create")
    def test_init_without_create(self, mock_deployment_create):
        deploy = objects.Deployment(deployment=self.deployment)
        self.assertFalse(mock_deployment_create.called)
        self.assertEqual(deploy["uuid"], self.deployment["uuid"])

    @mock.patch("rally.common.objects.deploy.db.deployment_get")
    def test_get(self, mock_deployment_get):
        mock_deployment_get.return_value = self.deployment
        deploy = objects.Deployment.get(self.deployment["uuid"])
        mock_deployment_get.assert_called_once_with(self.deployment["uuid"])
        self.assertEqual(deploy["uuid"], self.deployment["uuid"])

    @mock.patch("rally.common.objects.deploy.db.deployment_delete")
    @mock.patch("rally.common.objects.deploy.db.deployment_create")
    def test_create_and_delete(self, mock_deployment_create,
                               mock_deployment_delete):
        mock_deployment_create.return_value = self.deployment
        deploy = objects.Deployment()
        deploy.delete()
        mock_deployment_delete.assert_called_once_with(self.deployment["uuid"])

    @mock.patch("rally.common.objects.deploy.db.deployment_delete")
    def test_delete_by_uuid(self, mock_deployment_delete):
        objects.Deployment.delete_by_uuid(self.deployment["uuid"])
        mock_deployment_delete.assert_called_once_with(self.deployment["uuid"])

    @mock.patch("rally.common.objects.deploy.db.deployment_update")
    @mock.patch("rally.common.objects.deploy.db.deployment_create")
    def test_update(self, mock_deployment_create, mock_deployment_update):
        mock_deployment_create.return_value = self.deployment
        mock_deployment_update.return_value = {"opt": "val2"}
        deploy = objects.Deployment(opt="val1")
        deploy._update({"opt": "val2"})
        mock_deployment_update.assert_called_once_with(
            self.deployment["uuid"], {"opt": "val2"})
        self.assertEqual(deploy["opt"], "val2")

    @mock.patch("rally.common.objects.deploy.db.deployment_update")
    def test_update_status(self, mock_deployment_update):
        mock_deployment_update.return_value = self.deployment
        deploy = objects.Deployment(deployment=self.deployment)
        deploy.update_status(consts.DeployStatus.DEPLOY_FAILED)
        mock_deployment_update.assert_called_once_with(
            self.deployment["uuid"],
            {"status": consts.DeployStatus.DEPLOY_FAILED},
        )

    @mock.patch("rally.common.objects.deploy.db.deployment_update")
    def test_update_name(self, mock_deployment_update):
        mock_deployment_update.return_value = self.deployment
        deploy = objects.Deployment(deployment=self.deployment)
        deploy.update_name("new_name")
        mock_deployment_update.assert_called_once_with(
            self.deployment["uuid"],
            {"name": "new_name"},
        )

    @mock.patch("rally.common.objects.deploy.db.deployment_update")
    def test_update_config(self, mock_deployment_update):
        mock_deployment_update.return_value = self.deployment
        deploy = objects.Deployment(deployment=self.deployment)
        deploy.update_config({"opt": "val"})
        mock_deployment_update.assert_called_once_with(
            self.deployment["uuid"],
            {"config": {"opt": "val"}},
        )

    @mock.patch("rally.common.objects.deploy.db.deployment_update")
    def test_update_credentials(self, mock_deployment_update):
        mock_deployment_update.return_value = self.deployment
        deploy = objects.Deployment(deployment=self.deployment)
        credentials = {
            "admin": objects.Credential("url", "user", "pwd", "tenant",
                                        consts.EndpointPermission.ADMIN),
            "users": [
                objects.Credential("url1", "user1", "pwd1", "tenant1",
                                   consts.EndpointPermission.USER),
                objects.Credential("url2", "user2", "pwd2", "tenant2",
                                   consts.EndpointPermission.USER),
            ]
        }

        expected_users = [u.to_dict(include_permission=True)
                          for u in credentials["users"]]
        expected_admin = credentials["admin"].to_dict(include_permission=True)
        deploy.update_credentials(credentials)
        mock_deployment_update.assert_called_once_with(
            self.deployment["uuid"],
            {
                "credentials": [["openstack", {"admin": expected_admin,
                                               "users": expected_users}]]
            })

    @mock.patch("rally.common.objects.deploy.db.deployment_update")
    def test_update_empty_credentials(self, mock_deployment_update):
        mock_deployment_update.return_value = self.deployment
        deploy = objects.Deployment(deployment=self.deployment)
        deploy.update_credentials({})
        mock_deployment_update.assert_called_once_with(
            self.deployment["uuid"], {
                "credentials": [["openstack", {"admin": {}, "users": []}]]
            })

    @mock.patch("rally.common.objects.deploy.db.resource_create")
    def test_add_resource(self, mock_resource_create):
        mock_resource_create.return_value = self.resource
        deploy = objects.Deployment(deployment=self.deployment)
        resource = deploy.add_resource("provider", type="some",
                                       info={"key": "value"})
        self.assertEqual(resource["id"], self.resource["id"])
        mock_resource_create.assert_called_once_with({
            "deployment_uuid": self.deployment["uuid"],
            "provider_name": "provider",
            "type": "some",
            "info": {"key": "value"},
        })

    @mock.patch("rally.common.objects.task.db.resource_delete")
    def test_delete(self, mock_resource_delete):
        objects.Deployment.delete_resource(42)
        mock_resource_delete.assert_called_once_with(42)

    @mock.patch("rally.common.objects.task.db.resource_get_all")
    def test_get_resources(self, mock_resource_get_all):
        mock_resource_get_all.return_value = [self.resource]
        deploy = objects.Deployment(deployment=self.deployment)
        resources = deploy.get_resources(provider_name="provider", type="some")
        self.assertEqual(len(resources), 1)
        self.assertEqual(resources[0]["id"], self.resource["id"])

    @mock.patch("rally.common.objects.deploy.dt.datetime")
    @mock.patch("rally.common.objects.deploy.db.deployment_update")
    def test_update_set_started(self, mock_deployment_update, mock_datetime):
        mock_datetime.now = mock.Mock(return_value="fake_time")
        mock_deployment_update.return_value = self.deployment
        deploy = objects.Deployment(deployment=self.deployment)
        deploy.set_started()
        mock_deployment_update.assert_called_once_with(
            self.deployment["uuid"],
            {"started_at": "fake_time",
             "status": consts.DeployStatus.DEPLOY_STARTED}
        )

    @mock.patch("rally.common.objects.deploy.dt.datetime")
    @mock.patch("rally.common.objects.deploy.db.deployment_update")
    def test_update_set_completed(self, mock_deployment_update, mock_datetime):
        mock_datetime.now = mock.Mock(return_value="fake_time")
        mock_deployment_update.return_value = self.deployment
        deploy = objects.Deployment(deployment=self.deployment)
        deploy.set_completed()
        mock_deployment_update.assert_called_once_with(
            self.deployment["uuid"],
            {"completed_at": "fake_time",
             "status": consts.DeployStatus.DEPLOY_FINISHED}
        )
