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

import datetime as dt
from unittest import mock

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
            "platforms": {}
        }

    @mock.patch("rally.common.objects.deploy.env_mgr.EnvManager.create")
    def test_init(self, mock_env_manager_create):
        objects.Deployment(mock.MagicMock(data={"platforms": {}, "spec": {}}))
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

    @mock.patch("rally.common.objects.deploy.env_mgr.EnvManager.get")
    def test_get_validation_context(self, mock_env_manager_get):
        mock_env_manager_get.return_value = self.env
        deploy = objects.Deployment.get(self.env.data["uuid"])
        self.assertEqual(self.env.get_validation_context.return_value,
                         deploy.get_validation_context())

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

        self.env.data["platforms"] = {
            "openstack": {"platform_name": "openstack", "platform_data": {}},
            "foo": {"platform_name": "foo", "platform_data": {}}
        }

        deploy = objects.Deployment(deployment=self.env)

        self.assertEqual({"openstack", "foo"}, set(deploy.get_platforms()))

    def test_to_dict(self):
        env = mock.Mock(
            status=env_mgr.STATUS.READY,
            data={
                "created_at": dt.datetime(2017, 3, 10, 9, 5, 8, 0).isoformat(),
                "updated_at": dt.datetime(2017, 3, 10, 9, 5, 9, 0).isoformat(),
                "id": 1,
                "name": "foo_env_name",
                "uuid": "eeecf2c6-8b5d-4ed7-92e5-b7cdc335e885",
                "platforms": {},
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
                        "auth_url": "foo_auth_url"
                    }
                }
            }
        )
        deploy = objects.Deployment(deployment=env)
        config = {"openstack": env.data["spec"]["existing@openstack"]}
        self.assertEqual(
            {
                "created_at": "2017-03-10T09:05:08",
                "started_at": "2017-03-10T09:05:08",
                "updated_at": "2017-03-10T09:05:09",
                "completed_at": "n/a",
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
                    "platforms": {},
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

    @mock.patch("rally.common.objects.Deployment.get_all_credentials")
    def test_get_credentials_for(self, mock_get_all_credentials):
        mock_get_all_credentials.return_value = {
            "foo": ["bar"]
        }

        deploy = objects.Deployment(deployment=self.env)

        self.assertEqual("bar", deploy.get_credentials_for("foo"))

    def test_get_credentials_for_default(self):
        deploy = objects.Deployment(deployment=self.env)
        creds = deploy.get_credentials_for("default")
        self.assertEqual({"admin": None, "users": []}, creds)

    def test_get_credentials_error(self):
        deploy = objects.Deployment(deployment=self.env)
        self.assertRaises(exceptions.RallyException,
                          deploy.get_credentials_for, "bar")
