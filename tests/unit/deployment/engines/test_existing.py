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

import jsonschema

from rally import consts
from rally.deployment import engine as deploy_engine
from rally.deployment.engines import existing
from tests.unit import test


class TestExistingCloud(test.TestCase):
    def setUp(self):
        super(TestExistingCloud, self).setUp()
        self.deployment = {
            "config": {
                "type": "ExistingCloud",
                "auth_url": "http://example.net:5000/v2.0/",
                "region_name": "RegionOne",
                "endpoint_type": consts.EndpointType.INTERNAL,
                "https_insecure": False,
                "https_cacert": None,
                "admin": {
                    "username": "admin",
                    "password": "myadminpass",
                    "tenant_name": "demo",
                    "domain_name": None,
                    "project_domain_name": "Default",
                    "user_domain_name": "Default",
                    "admin_domain_name": "Default",
                }
            }
        }

    def test_init(self):
        existing.ExistingCloud(self.deployment)

    def test_invalid_config(self):
        self.deployment["config"]["admin"] = 42
        engine = existing.ExistingCloud(self.deployment)
        self.assertRaises(jsonschema.ValidationError,
                          engine.validate)

    def test_deploy(self):
        engine = existing.ExistingCloud(self.deployment)
        credentials = engine.deploy()
        admin_credential = self.deployment["config"].copy()
        admin_credential.pop("type")
        admin_credential["endpoint"] = None
        admin_credential.update(admin_credential.pop("admin"))
        self.assertEqual(admin_credential, credentials["admin"].to_dict())
        self.assertEqual([], credentials["users"])

    def test_cleanup(self):
        existing.ExistingCloud(self.deployment).cleanup()

    def test_is_in_factory(self):
        name = self.deployment["config"]["type"]
        engine = deploy_engine.Engine.get_engine(name,
                                                 self.deployment)
        self.assertIsInstance(engine, existing.ExistingCloud)
