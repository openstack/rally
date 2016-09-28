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

"""Test ExistingCloud."""

import ddt
import jsonschema

from rally import consts
from rally.deployment import engine as deploy_engine
from rally.deployment.engines import existing
from tests.unit import test


@ddt.ddt
class TestExistingCloud(test.TestCase):
    def setUp(self):
        super(TestExistingCloud, self).setUp()
        self.deployments = {
            "v2.0": {
                "config": {
                    "type": "ExistingCloud",
                    "auth_url": "http://example.net:5000/v2.0/",
                    "region_name": "RegionOne",
                    "endpoint_type": consts.EndpointType.INTERNAL,
                    "https_insecure": False,
                    "https_cacert": "cacert",
                    "admin": {
                        "username": "admin",
                        "password": "myadminpass",
                        "tenant_name": "demo"
                    }
                }
            },
            "v3": {
                "config": {
                    "type": "ExistingCloud",
                    "auth_url": "http://example.net:5000/v3/",
                    "region_name": "RegionOne",
                    "endpoint_type": consts.EndpointType.INTERNAL,
                    "https_insecure": False,
                    "https_cacert": "cacert",
                    "admin": {
                        "username": "admin",
                        "password": "myadminpass",
                        "domain_name": "domain",
                        "project_name": "demo",
                        "project_domain_name": "Default",
                        "user_domain_name": "Default",
                    }
                }
            }
        }

    @ddt.data("v2.0", "v3")
    def test_init_and_valid_config(self, keystone_version):
        engine = existing.ExistingCloud(self.deployments[keystone_version])
        engine.validate()

    @ddt.data("v2.0", "v3")
    def test_invalid_config(self, keystone_version):
        deployment = self.deployments[keystone_version]
        deployment["config"]["admin"] = 42
        engine = existing.ExistingCloud(deployment)
        self.assertRaises(jsonschema.ValidationError,
                          engine.validate)

    @ddt.data("v2.0", "v3")
    def test_additional_vars(self, keystone_version):
        deployment = self.deployments[keystone_version]
        deployment["extra"] = {}
        existing.ExistingCloud(deployment).validate()

        deployment["extra"] = {"some_var": "some_value"}
        existing.ExistingCloud(deployment).validate()

        deployment["extra"] = ["item1", "item2"]
        existing.ExistingCloud(deployment).validate()

    @ddt.data("v2.0", "v3")
    def test_deploy(self, keystone_version):
        deployment = self.deployments[keystone_version]
        engine = existing.ExistingCloud(deployment)
        credentials = engine.deploy()
        admin_credential = deployment["config"].copy()
        admin_credential.pop("type")
        admin_credential["endpoint"] = None
        admin_credential.update(admin_credential.pop("admin"))

        actual_credentials = credentials["admin"].to_dict()

        if keystone_version == "v3":
            # NOTE(andreykurilin): credentials obj uses `tenant_name` for both
            #   keystone v2 and v3. It works perfectly for rally code (no
            #   contradictions and misunderstandings ), but in case of checking
            #   credentials.to_dict with data from database (where we use
            #   project_name for keystone v3 config and tenant_name for
            #   keystone v2), we need to transform vars.
            admin_credential["tenant_name"] = admin_credential.pop(
                "project_name")
        else:
            # NOTE(andreykurilin): there are no domain related variables in v2,
            #   so we need to pop them from credentials.to_dict()
            actual_credentials.pop("domain_name")
            actual_credentials.pop("user_domain_name")
            actual_credentials.pop("project_domain_name")

        self.assertEqual(admin_credential, actual_credentials)
        self.assertEqual([], credentials["users"])

    @ddt.data("v2.0", "v3")
    def test_cleanup(self, keystone_version):
        existing.ExistingCloud(self.deployments[keystone_version]).cleanup()

    @ddt.data("v2.0", "v3")
    def test_is_in_factory(self, keystone_version):
        name = self.deployments[keystone_version]["config"]["type"]
        engine = deploy_engine.Engine.get_engine(
            name, self.deployments[keystone_version])
        self.assertIsInstance(engine, existing.ExistingCloud)
