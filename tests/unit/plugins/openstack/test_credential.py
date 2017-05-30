# Copyright 2017: Mirantis Inc.
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

import jsonschema
import mock

from rally import consts
from rally.deployment import credential
from tests.unit import test


class OpenStackCredentialTestCase(test.TestCase):

    def setUp(self):
        super(OpenStackCredentialTestCase, self).setUp()
        cred_cls = credential.get("openstack")
        self.credential = cred_cls(
            "foo_url", "foo_user", "foo_password",
            tenant_name="foo_tenant",
            permission=consts.EndpointPermission.ADMIN)

    def test_to_dict(self):
        self.assertEqual({"auth_url": "foo_url",
                          "username": "foo_user",
                          "password": "foo_password",
                          "tenant_name": "foo_tenant",
                          "region_name": None,
                          "domain_name": None,
                          "endpoint": None,
                          "permission": consts.EndpointPermission.ADMIN,
                          "endpoint_type": None,
                          "https_insecure": False,
                          "https_cacert": None,
                          "project_domain_name": None,
                          "user_domain_name": None,
                          "profiler_hmac_key": None},
                         self.credential.to_dict())

    @mock.patch("rally.osclients.Clients")
    def test_verify_connection_admin(self, mock_clients):
        self.credential.verify_connection()
        mock_clients.assert_called_once_with(
            self.credential, api_info=None, cache={})
        mock_clients.return_value.verified_keystone.assert_called_once_with()

    @mock.patch("rally.osclients.Clients")
    def test_verify_connection_user(self, mock_clients):
        self.credential.permission = consts.EndpointPermission.USER
        self.credential.verify_connection()
        mock_clients.assert_called_once_with(
            self.credential, api_info=None, cache={})
        mock_clients.return_value.keystone.assert_called_once_with()

    @mock.patch("rally.osclients.Clients")
    def test_list_services(self, mock_clients):
        mock_clients.return_value.services.return_value = {"compute": "nova",
                                                           "volume": "cinder"}
        result = self.credential.list_services()
        mock_clients.assert_called_once_with(
            self.credential, api_info=None, cache={})
        mock_clients.return_value.services.assert_called_once_with()
        self.assertEqual([{"name": "cinder", "type": "volume"},
                          {"name": "nova", "type": "compute"}], result)

    @mock.patch("rally.osclients.Clients")
    def test_clients(self, mock_clients):
        clients = self.credential.clients(api_info="fake_info")
        mock_clients.assert_called_once_with(
            self.credential, api_info="fake_info", cache={})
        self.assertIs(mock_clients.return_value, clients)


class OpenStackCredentialBuilderTestCase(test.TestCase):

    def setUp(self):
        super(OpenStackCredentialBuilderTestCase, self).setUp()
        self.config = {
            "auth_url": "http://example.net:5000/v2.0/",
            "region_name": "RegionOne",
            "endpoint_type": consts.EndpointType.INTERNAL,
            "https_insecure": False,
            "https_cacert": "cacert",
            "admin": {
                "username": "admin",
                "password": "myadminpass",
                "tenant_name": "demo"
            },
            "users": [
                {
                    "username": "user1",
                    "password": "userpass",
                    "tenant_name": "demo"
                }
            ]
        }
        self.cred_builder_cls = credential.get_builder("openstack")

    def test_validate(self):
        self.cred_builder_cls.validate(self.config)

    def test_validate_error(self):
        self.assertRaises(jsonschema.ValidationError,
                          self.cred_builder_cls.validate,
                          {"foo": "bar"})

    def test_build_credentials(self):
        creds_builder = self.cred_builder_cls(self.config)
        creds = creds_builder.build_credentials()
        self.assertEqual({
            "admin": {
                "auth_url": "http://example.net:5000/v2.0/",
                "username": "admin",
                "password": "myadminpass",
                "permission": consts.EndpointPermission.ADMIN,
                "domain_name": None,
                "endpoint": None,
                "endpoint_type": consts.EndpointType.INTERNAL,
                "https_cacert": "cacert",
                "https_insecure": False,
                "profiler_hmac_key": None,
                "project_domain_name": None,
                "region_name": "RegionOne",
                "tenant_name": "demo",
                "user_domain_name": None,
            },
            "users": [
                {
                    "auth_url": "http://example.net:5000/v2.0/",
                    "username": "user1",
                    "password": "userpass",
                    "permission": consts.EndpointPermission.USER,
                    "domain_name": None,
                    "endpoint": None,
                    "endpoint_type": consts.EndpointType.INTERNAL,
                    "https_cacert": "cacert",
                    "https_insecure": False,
                    "profiler_hmac_key": None,
                    "project_domain_name": None,
                    "region_name": "RegionOne",
                    "tenant_name": "demo",
                    "user_domain_name": None,
                }
            ]
        }, creds)
