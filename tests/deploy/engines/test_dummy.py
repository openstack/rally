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

"""Test dummy deploy engines."""

import jsonschema

from rally import deploy
from rally.deploy.engines import dummy
from tests import test


class TestDummyDeployEngine(test.TestCase):
    def setUp(self):
        self.deployment = {
            'config': {
                'name': 'DummyEngine',
                'endpoint': {
                    'auth_url': 'http://example.net:5000/v2.0/',
                    'username': 'admin',
                    'password': 'myadminpass',
                    'tenant_name': 'demo',
                },
            },
        }
        super(TestDummyDeployEngine, self).setUp()

    def test_init(self):
        dummy.DummyEngine(self.deployment)

    def test_init_invalid_config(self):
        self.deployment['config']['endpoint'] = 42
        self.assertRaises(jsonschema.ValidationError,
                          dummy.DummyEngine, self.deployment)

    def test_deploy(self):
        engine = dummy.DummyEngine(self.deployment)
        endpoints = engine.deploy()
        admin_endpoint = self.deployment['config']['endpoint'].copy()
        self.assertEqual(admin_endpoint, endpoints[0].to_dict())

    def test_cleanup(self):
        dummy.DummyEngine(self.deployment).cleanup()

    def test_is_in_factory(self):
        name = self.deployment['config']['name']
        engine = deploy.EngineFactory.get_engine(name,
                                                 self.deployment)
        self.assertIsInstance(engine, dummy.DummyEngine)
