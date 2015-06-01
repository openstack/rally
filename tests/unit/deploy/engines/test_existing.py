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
from rally import deploy
from rally.deploy.engines import existing
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
        endpoints = engine.deploy()
        admin_endpoint = self.deployment["config"].copy()
        admin_endpoint.pop("type")
        admin_endpoint["endpoint"] = None
        admin_endpoint.update(admin_endpoint.pop("admin"))
        self.assertEqual(admin_endpoint, endpoints["admin"].to_dict())
        self.assertEqual([], endpoints["users"])

    def test_cleanup(self):
        existing.ExistingCloud(self.deployment).cleanup()

    def test_is_in_factory(self):
        name = self.deployment["config"]["type"]
        engine = deploy.EngineFactory.get_engine(name,
                                                 self.deployment)
        self.assertIsInstance(engine, existing.ExistingCloud)
