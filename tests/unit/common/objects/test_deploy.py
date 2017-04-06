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

import collections
import datetime as dt
import mock

from rally.common import objects
from rally import consts
from rally import exceptions
from tests.unit import test


class DeploymentTestCase(test.TestCase):
    TIME_FORMAT = consts.TimeFormat.ISO8601

    def setUp(self):
        super(DeploymentTestCase, self).setUp()
        self.deployment = {
            "uuid": "baa1bfb6-0c38-4f6c-9bd0-45968890e4f4",
            "name": "",
            "config": {},
            "credentials": {},
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

    @mock.patch("rally.deployment.credential.get")
    @mock.patch("rally.common.objects.deploy.db.deployment_update")
    def test_update_credentials(self, mock_deployment_update,
                                mock_credential_get):
        mock_deployment_update.return_value = self.deployment
        deploy = objects.Deployment(deployment=self.deployment)
        credentials = {"foo": [{"admin": {"fake_admin": True},
                                "users": [{"fake_user": True}]}]}

        deploy.update_credentials(credentials)
        mock_deployment_update.assert_called_once_with(
            self.deployment["uuid"],
            {
                "credentials": {"foo": [{"admin": {"fake_admin": True},
                                         "users": [{"fake_user": True}]}]}
            })

    def test_get_platforms(self):
        self.deployment["credentials"] = {"foo": {"admin": None, "users": []},
                                          "bar": {"admin": None, "users": []}}
        deploy = objects.Deployment(deployment=self.deployment)
        self.assertEqual({"foo", "bar"}, set(deploy.get_platforms()))

    def test_get_platforms_empty(self):
        deploy = objects.Deployment(deployment=self.deployment)
        self.assertEqual([], list(deploy.get_platforms()))

    @mock.patch("rally.deployment.credential.get")
    def test_get_credentials_for(self, mock_credential_get):
        credential_cls = mock_credential_get.return_value
        credential_inst = credential_cls.return_value
        credentials = {"foo": [{"admin": {"fake_admin": True},
                                "users": [{"fake_user": True}]}]}
        self.deployment["credentials"] = credentials
        deploy = objects.Deployment(deployment=self.deployment)
        creds = deploy.get_credentials_for("foo")

        mock_credential_get.assert_called_once_with("foo")
        credential_cls.assert_has_calls((
            mock.call(fake_admin=True),
            mock.call(fake_user=True),
        ))

        self.assertEqual({"admin": credential_inst,
                          "users": [credential_inst]}, creds)

    def test_get_credentials_for_default(self):
        deploy = objects.Deployment(deployment=self.deployment)
        creds = deploy.get_credentials_for("default")
        self.assertEqual({"admin": None, "users": []}, creds)

    @mock.patch("rally.common.objects.deploy.credential")
    def test_get_all_credentials(self, mock_credential):

        openstack_admin = {"openstack": "admin"}
        openstack_user_1 = {"openstack": "user1"}
        openstack_user_2 = {"openstack": "user2"}
        foo_admin = {"foo": "admin"}
        bar_user_1 = {"bar": "user1"}

        openstack_cred = mock.Mock()
        foo_cred = mock.Mock()
        bar_cred = mock.Mock()

        def credential_get(platform):
            return {"openstack": openstack_cred, "foo": foo_cred,
                    "bar": bar_cred}[platform]

        mock_credential.get.side_effect = credential_get

        self.deployment["credentials"] = collections.OrderedDict([
            # the case when both admin and users are specified
            ("openstack", [{"admin": openstack_admin,
                            "users": [openstack_user_1, openstack_user_2]}]),
            # the case when only admin is specified
            ("foo", [{"admin": foo_admin, "users": []}]),
            # the case when only users are specified
            ("bar", [{"admin": None, "users": [bar_user_1]}])])

        deploy = objects.Deployment(deployment=self.deployment)
        self.assertEqual({"openstack": [
            {"admin": openstack_cred.return_value,
             "users": [openstack_cred.return_value,
                       openstack_cred.return_value]}],
            "foo": [{"admin": foo_cred.return_value, "users": []}],
            "bar": [{"admin": None, "users": [bar_cred.return_value]}]
        }, deploy.get_all_credentials())

        self.assertEqual([mock.call(**openstack_admin),
                          mock.call(**openstack_user_1),
                          mock.call(**openstack_user_2)],
                         openstack_cred.call_args_list)
        foo_cred.assert_called_once_with(**foo_admin)
        bar_cred.assert_called_once_with(**bar_user_1)
        self.assertEqual([mock.call(p)
                          for p in self.deployment["credentials"].keys()],
                         mock_credential.get.call_args_list)

    @mock.patch("rally.deployment.credential.get")
    def test_get_deprecated(self, mock_credential_get):
        credential_cls = mock_credential_get.return_value
        credential_inst = credential_cls.return_value

        credentials = {"openstack": [{"admin": {"fake_admin": True},
                                      "users": [{"fake_user": True}]}]}
        self.deployment["credentials"] = credentials

        deploy = objects.Deployment(deployment=self.deployment)

        self.assertEqual(credential_inst, deploy["admin"])
        self.assertEqual([credential_inst], deploy["users"])

    @mock.patch("rally.common.objects.deploy.db.deployment_update")
    def test_update_empty_credentials(self, mock_deployment_update):
        deploy = objects.Deployment(deployment=self.deployment)
        deploy.update_credentials({})
        mock_deployment_update.assert_called_once_with(
            self.deployment["uuid"], {"credentials": {}})

    def test_get_credentials_error(self):
        deploy = objects.Deployment(deployment=self.deployment)
        self.assertRaises(exceptions.RallyException,
                          deploy.get_credentials_for, "bar")

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

    def test_to_dict(self):
        self.deployment = {
            "status": "deploy->finished",
            "parent_uuid": None,
            "updated_at": dt.datetime(2017, 3, 10, 9, 5, 9, 117427),
            "completed_at": dt.datetime(2017, 3, 10, 12, 5, 9, 94981),
            "credentials":
                {"openstack":
                    [{"admin":
                        {"username": "foo_admin_name",
                         "endpoint": None,
                         "region_name": "FooRegionOne",
                         "https_insecure": False,
                         "permission": "foo_perm",
                         "tenant_name": "foo_tenant",
                         "user_domain_name": "Default",
                         "https_cacert": "",
                         "domain_name": None,
                         "endpoint_type": None,
                         "auth_url": "foo_auth_url",
                         "password": "admin",
                         "project_domain_name": "Default"},
                      "users": []}]},
            "started_at": dt.datetime(2017, 3, 10, 12, 5, 9, 78779),
            "id": 1,
            "name": "foo_deployment_name",
            "uuid": "eeecf2c6-8b5d-4ed7-92e5-b7cdc335e885",
            "created_at": dt.datetime(2017, 3, 10, 9, 5, 9, 68652),
            "config": {
                "endpoint": None,
                "region_name": "FooRegionOne",
                "https_insecure": False,
                "admin": {
                    "username": "foo_admin_name",
                    "password": "foo_admin_pwd",
                    "user_domain_name": "Default",
                    "project_name": "foo_prj_name",
                    "project_domain_name": "Default"},
                "https_cacert": "",
                "endpoint_type": None,
                "auth_url": "foo_auth_url",
                "type": "ExistingCloud"}}
        deploy = objects.Deployment(deployment=self.deployment)
        expected_result = deploy.to_dict()
        for field in ["created_at", "completed_at",
                      "started_at", "updated_at"]:
            self.deployment[field] = self.deployment[field].strftime(
                self.TIME_FORMAT)
        self.assertEqual(expected_result, self.deployment)
