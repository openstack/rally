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

import json

import mock

from rally.env import platform
from rally.plugins.openstack.platforms import existing
from tests.unit.env import test_platform


class ExistingPlatformTestCase(test_platform.PlatformBaseTestCase):

    def test_validate_spec_schema(self):
        spec = {
            "existing@openstack": {
                "auth_url": "url",
                "admin": {
                    "username": "admin",
                    "password": "password123",
                    "tenant_name": "admin"
                },
                "users": [{
                    "username": "admin",
                    "password": "password123",
                    "tenant_name": "admin"
                }]
            }
        }
        result = platform.Platform.validate("existing@openstack", {},
                                            spec, spec["existing@openstack"])
        self.assertEqual([], result)

    def test_validate_invalid_spec(self):
        spec = {
            "existing@openstack": {
                "something_wrong": {
                    "username": "not_an_admin",
                    "password": "password123",
                    "project_name": "not_an_admin"
                }
            }
        }
        result = platform.Platform.validate("existing@openstack", {},
                                            spec, spec["existing@openstack"])
        self.assertNotEqual([], result)

    def test_create_users_only(self):

        spec = {
            "auth_url": "https://best",
            "endpoint": "check_that_its_poped",
            "users": [
                {"project_name": "a", "username": "a", "password": "a"},
                {"project_name": "b", "username": "b", "password": "b"}
            ]
        }

        self.assertEqual(
            ({
                "admin": None,
                "users": [
                    {
                        "auth_url": "https://best", "endpoint_type": None,
                        "region_name": None,
                        "domain_name": None,
                        "user_domain_name": "default",
                        "project_domain_name": "default",
                        "https_insecure": False, "https_cacert": None,
                        "tenant_name": "a", "username": "a", "password": "a"
                    },
                    {
                        "auth_url": "https://best", "endpoint_type": None,
                        "region_name": None,
                        "domain_name": None,
                        "user_domain_name": "default",
                        "project_domain_name": "default",
                        "https_insecure": False, "https_cacert": None,
                        "tenant_name": "b", "username": "b", "password": "b"
                    }
                ]
            }, {}),
            existing.OpenStack(spec).create())

    def test_create_admin_only(self):
        spec = {
            "auth_url": "https://best",
            "endpoint_type": "public",
            "https_insecure": True,
            "https_cacert": "/my.ca",
            "profiler_hmac_key": "key",
            "profiler_conn_str": "http://prof",
            "admin": {
                "domain_name": "d", "user_domain_name": "d",
                "project_domain_name": "d", "project_name": "d",
                "username": "d", "password": "d"
            }
        }
        self.assertEqual(
            (
                {
                    "admin": {
                        "auth_url": "https://best",
                        "endpoint_type": "public",
                        "https_insecure": True, "https_cacert": "/my.ca",
                        "profiler_hmac_key": "key",
                        "profiler_conn_str": "http://prof",
                        "region_name": None, "domain_name": "d",
                        "user_domain_name": "d", "project_domain_name": "d",
                        "tenant_name": "d", "username": "d", "password": "d"
                    },
                    "users": []
                },
                {}
            ),
            existing.OpenStack(spec).create())

    def test_destroy(self):
        self.assertIsNone(existing.OpenStack({}).destroy())

    def test_cleanup(self):
        result1 = existing.OpenStack({}).cleanup()
        result2 = existing.OpenStack({}).cleanup(task_uuid="any")
        self.assertEqual(result1, result2)
        self.assertEqual(
            {
                "message": "Coming soon!",
                "discovered": 0,
                "deleted": 0,
                "failed": 0,
                "resources": {},
                "errors": []
            },
            result1
        )
        self._check_cleanup_schema(result1)

    @mock.patch("rally.plugins.openstack.osclients.Clients")
    def test_check_health(self, mock_clients):
        pdata = {
            "admin": mock.MagicMock(),
            "users": [mock.MagicMock(), mock.MagicMock()]
        }
        result = existing.OpenStack({}, platform_data=pdata).check_health()
        self._check_health_schema(result)
        self.assertEqual({"available": True}, result)
        mock_clients.assert_has_calls(
            [mock.call(pdata["admin"]), mock.call().verified_keystone(),
             mock.call(pdata["users"][0]), mock.call().keystone(),
             mock.call(pdata["users"][1]), mock.call().keystone()])

    @mock.patch("rally.plugins.openstack.osclients.Clients")
    def test_check_failed_admin(self, mock_clients):
        mock_clients.return_value.verified_keystone.side_effect = Exception
        pdata = {"admin": {"username": "balbab", "password": "12345"}}
        result = existing.OpenStack({}, platform_data=pdata).check_health()
        self._check_health_schema(result)
        self.assertEqual(
            {"available": False,
             "message":
                "Bad admin creds: \n%s"
                % json.dumps({"username": "balbab", "password": "***"},
                             indent=2, sort_keys=True),
             "traceback": mock.ANY},
            result)
        self.assertIn("Traceback (most recent call last)", result["traceback"])

    @mock.patch("rally.plugins.openstack.osclients.Clients")
    def test_check_failed_users(self, mock_clients):
        mock_clients.return_value.keystone.side_effect = Exception
        pdata = {"admin": None,
                 "users": [{"username": "balbab", "password": "12345"}]}
        result = existing.OpenStack({}, platform_data=pdata).check_health()
        self._check_health_schema(result)
        self.assertEqual(
            {"available": False,
             "message":
                "Bad user creds: \n%s"
                % json.dumps({"username": "balbab", "password": "***"},
                             indent=2, sort_keys=True),
             "traceback": mock.ANY},
            result)
        self.assertIn("Traceback (most recent call last)", result["traceback"])

    @mock.patch("rally.plugins.openstack.osclients.Clients")
    def test_info(self, mock_clients):
        mock_clients.return_value.services.return_value = {
            "foo": "bar",
            "volumev4": "__unknown__"}
        platform_data = {
            "admin": None,
            "users": [{"username": "u1", "password": "123"}]
        }
        p = existing.OpenStack({}, platform_data=platform_data)

        result = p.info()
        mock_clients.assert_called_once_with(platform_data["users"][0])
        mock_clients.return_value.services.assert_called_once_with()
        self.assertEqual(
            {
                "info": {
                    "services": [{"type": "foo", "name": "bar"},
                                 {"type": "volumev4"}]}},
            result)
        self._check_info_schema(result)
