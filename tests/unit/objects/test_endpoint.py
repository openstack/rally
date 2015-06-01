# Copyright 2014: Mirantis Inc.
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

from rally import consts
from rally import objects
from tests.unit import test


class EndpointTestCase(test.TestCase):

    def test_to_dict(self):
        endpoint = objects.Endpoint("foo_url", "foo_user", "foo_password",
                                    tenant_name="foo_tenant",
                                    permission=consts.EndpointPermission.ADMIN)
        self.assertEqual(endpoint.to_dict(),
                         {"auth_url": "foo_url",
                          "username": "foo_user",
                          "password": "foo_password",
                          "tenant_name": "foo_tenant",
                          "region_name": None,
                          "domain_name": None,
                          "endpoint": None,
                          "endpoint_type": consts.EndpointType.PUBLIC,
                          "https_insecure": None,
                          "https_cacert": None,
                          "project_domain_name": "Default",
                          "user_domain_name": "Default",
                          "admin_domain_name": "Default"})

    def test_to_dict_with_include_permission(self):
        endpoint = objects.Endpoint("foo_url", "foo_user", "foo_password",
                                    tenant_name="foo_tenant",
                                    permission=consts.EndpointPermission.ADMIN)
        self.assertEqual(endpoint.to_dict(include_permission=True),
                         {"auth_url": "foo_url",
                          "username": "foo_user",
                          "password": "foo_password",
                          "tenant_name": "foo_tenant",
                          "region_name": None,
                          "domain_name": None,
                          "endpoint": None,
                          "permission": consts.EndpointPermission.ADMIN,
                          "endpoint_type": consts.EndpointType.PUBLIC,
                          "https_insecure": None,
                          "https_cacert": None,
                          "project_domain_name": "Default",
                          "user_domain_name": "Default",
                          "admin_domain_name": "Default"})

    def test_to_dict_with_kwarg_endpoint(self):
        endpoint = objects.Endpoint("foo_url", "foo_user", "foo_password",
                                    tenant_name="foo_tenant",
                                    permission=consts.EndpointPermission.ADMIN,
                                    endpoint="foo_endpoint")
        self.assertEqual(endpoint.to_dict(),
                         {"auth_url": "foo_url",
                          "username": "foo_user",
                          "password": "foo_password",
                          "tenant_name": "foo_tenant",
                          "region_name": None,
                          "domain_name": None,
                          "endpoint": "foo_endpoint",
                          "endpoint_type": consts.EndpointType.PUBLIC,
                          "https_insecure": None,
                          "https_cacert": None,
                          "project_domain_name": "Default",
                          "user_domain_name": "Default",
                          "admin_domain_name": "Default"})
