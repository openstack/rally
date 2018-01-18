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
from rally.env import env_mgr
from rally import exceptions
from tests.unit import test


class DeploymentTestCase(test.TestCase):
    TIME_FORMAT = consts.TimeFormat.ISO8601

    def setUp(self):
        super(DeploymentTestCase, self).setUp()
        self.env = mock.MagicMock()
        self.env.data = {
            "id": 1,
            "uuid": "baa1bfb6-0c38-4f6c-9bd0-45968890e4f4",
            "created_at": None,
            "updated_at": None,
            "name": "",
            "description": "",
            "status": env_mgr.STATUS.INIT,
            "spec": {},
            "extras": {},
            "platforms": []
        }

    @mock.patch("rally.common.objects.deploy.env_mgr.EnvManager.create")
    def test_init(self, mock_env_manager_create):
        objects.Deployment(mock.MagicMock(data={"platforms": [], "spec": {}}))
        self.assertFalse(mock_env_manager_create.called)
        deploy = objects.Deployment()
        mock_env_manager_create.assert_called_once_with(
            name=None, description="", spec={}, extras={}
        )
        self.assertEqual(mock_env_manager_create.return_value.uuid,
                         deploy["uuid"])

    @mock.patch("rally.common.objects.deploy.env_mgr.EnvManager.get")
    def test_get(self, mock_env_manager_get):
        mock_env_manager_get.return_value = self.env
        deploy = objects.Deployment.get(self.env.data["uuid"])
        mock_env_manager_get.assert_called_once_with(self.env.data["uuid"])
        self.assertEqual(self.env.uuid, deploy["uuid"])

    @mock.patch("rally.deployment.credential.get")
    def test_get_validation_context(self, mock_credential_get):
        credential_cls = mock_credential_get.return_value
        credential_cls.get_validation_context.side_effect = [
            {"foo_test": "test"}, {"boo_test": "boo"}
        ]
        deploy = objects.Deployment(deployment=self.env)
        deploy._all_credentials = {"foo": [], "boo": []}

        self.assertEqual({"foo_test": "test", "boo_test": "boo"},
                         deploy.get_validation_context())

        mock_credential_get.assert_has_calls(
            [mock.call("foo"), mock.call("boo")],
            any_order=True)

    def test_verify_connections(self):
        deploy = objects.Deployment(deployment=self.env)

        self.env.check_health.return_value = {"foo": {"available": True}}
        deploy.verify_connections()
        self.env.check_health.assert_called_once_with()

        self.env.check_health.return_value = {"foo": {"available": False,
                                                      "message": "Ooops"}}
        e = self.assertRaises(exceptions.RallyException,
                              deploy.verify_connections)
        self.assertEqual("Platform foo is not available: Ooops.", "%s" % e)

    def test_get_platforms(self):
        deploy = objects.Deployment(deployment=self.env)
        self.assertEqual([], list(deploy.get_platforms()))

        self.env.data["platforms"] = [
            {"plugin_name": "existing@openstack", "platform_data": {}},
            {"plugin_name": "foo", "platform_data": {}}
        ]

        deploy = objects.Deployment(deployment=self.env)

        self.assertEqual({"openstack", "foo"}, set(deploy.get_platforms()))

    @mock.patch("rally.deployment.credential.get")
    def test_get_credentials_for(self, mock_credential_get):
        credential_cls = mock_credential_get.return_value
        credential_inst = credential_cls.return_value
        deploy = objects.Deployment(deployment=self.env)
        deploy._all_credentials = {"foo": [{"admin": {"fake_admin": True},
                                            "users": [{"fake_user": True}]}]}

        creds = deploy.get_credentials_for("foo")

        mock_credential_get.assert_called_once_with("foo")
        credential_cls.assert_has_calls((
            mock.call(fake_admin=True),
            mock.call(fake_user=True),
        ))

        self.assertEqual({"admin": credential_inst,
                          "users": [credential_inst]}, creds)

    def test_get_credentials_for_default(self):
        deploy = objects.Deployment(deployment=self.env)
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

        deploy = objects.Deployment(deployment=self.env)
        deploy._all_credentials = collections.OrderedDict([
            # the case when both admin and users are specified
            ("openstack", [{"admin": openstack_admin,
                            "users": [openstack_user_1, openstack_user_2]}]),
            # the case when only admin is specified
            ("foo", [{"admin": foo_admin, "users": []}]),
            # the case when only users are specified
            ("bar", [{"admin": None, "users": [bar_user_1]}])])

        self.assertEqual({"openstack": [
            {"admin": openstack_cred.return_value,
             "users": [openstack_cred.return_value,
                       openstack_cred.return_value]}],
            "foo": [{"admin": foo_cred.return_value, "users": []}],
            "bar": [{"admin": None, "users": [bar_cred.return_value]}]
        }, deploy.get_all_credentials())

        self.assertEqual([mock.call(permission=consts.EndpointPermission.ADMIN,
                                    **openstack_admin),
                          mock.call(**openstack_user_1),
                          mock.call(**openstack_user_2)],
                         openstack_cred.call_args_list)
        foo_cred.assert_called_once_with(
            permission=consts.EndpointPermission.ADMIN,
            **foo_admin)
        bar_cred.assert_called_once_with(**bar_user_1)
        self.assertEqual([mock.call(p)
                          for p in deploy._all_credentials.keys()],
                         mock_credential.get.call_args_list)

    @mock.patch("rally.deployment.credential.get")
    def test_get_deprecated(self, mock_credential_get):
        credential_cls = mock_credential_get.return_value
        credential_inst = credential_cls.return_value

        deploy = objects.Deployment(deployment=self.env)
        deploy._all_credentials = {
            "openstack": [{"admin": {"fake_admin": True},
                           "users": [{"fake_user": True}]}]}

        self.assertEqual(credential_inst, deploy["admin"])
        self.assertEqual([credential_inst], deploy["users"])

    def test_get_credentials_error(self):
        deploy = objects.Deployment(deployment=self.env)
        self.assertRaises(exceptions.RallyException,
                          deploy.get_credentials_for, "bar")

    def test_to_dict(self):
        env = mock.Mock(
            status=env_mgr.STATUS.READY,
            data={
                "created_at": dt.datetime(2017, 3, 10, 9, 5, 9, 68652),
                "updated_at": dt.datetime(2017, 3, 10, 9, 5, 10, 117427),
                "id": 1,
                "name": "foo_env_name",
                "uuid": "eeecf2c6-8b5d-4ed7-92e5-b7cdc335e885",
                "platforms": [],
                "spec": {
                    "existing@openstack": {
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
                        "auth_url": "foo_auth_url"}
                }})
        deploy = objects.Deployment(deployment=env)
        config = {"openstack": env.data["spec"]["existing@openstack"]}
        self.assertEqual(
            {
                "created_at": "2017-03-10T09:05:09",
                "started_at": "2017-03-10T09:05:09",
                "updated_at": "2017-03-10T09:05:10",
                "completed_at": "n/a",
                "id": 1,
                "uuid": "eeecf2c6-8b5d-4ed7-92e5-b7cdc335e885",
                "name": "foo_env_name",
                "parent_uuid": None,
                "status": "deploy->finished",
                "config": config,
                "credentials": {}},
            deploy.to_dict())

    def test_getitem(self):

        class FakeEnvManager(object):
            @property
            def status(self):
                return env_mgr.STATUS.READY

            @property
            def data(self):
                return {
                    "created_at": dt.datetime(2017, 3, 10, 9, 5, 9, 68652),
                    "updated_at": dt.datetime(2017, 3, 10, 9, 5, 10, 117427),
                    "id": 1,
                    "name": "foo_env_name",
                    "uuid": "eeecf2c6-8b5d-4ed7-92e5-b7cdc335e885",
                    "platforms": [],
                    "extras": {"foo": "bar"},
                    "spec": {
                        "existing@openstack": {
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
                            "auth_url": "foo_auth_url"}
                    }
                }

        deploy = objects.Deployment(deployment=FakeEnvManager())

        self.assertEqual("deploy->finished", deploy["status"])

        self.assertEqual({"foo": "bar"}, deploy["extra"])
        self.assertEqual(
            {
                "openstack": {
                    "admin": {
                        "password": "foo_admin_pwd",
                        "project_domain_name": "Default",
                        "project_name": "foo_prj_name",
                        "user_domain_name": "Default",
                        "username": "foo_admin_name"},
                    "auth_url": "foo_auth_url",
                    "endpoint": None,
                    "endpoint_type": None,
                    "https_cacert": "",
                    "https_insecure": False,
                    "region_name": "FooRegionOne"}},
            deploy["config"])
