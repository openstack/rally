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
from rally.deploy.engines import dummy_engine
from rally import test


class TestDummyDeployEngine(test.TestCase):
    def setUp(self):
        self.deployment = {
            'config': {
                'name': 'DummyEngine',
                'cloud_config': {
                    'identity': {
                        'url': 'http://example.net/',
                        'uri': 'http://example.net:5000/v2.0/',
                        'admin_username': 'admin',
                        'admin_password': 'myadminpass',
                        'admin_tenant_name': 'demo',
                    },
                },
            },
        }
        super(TestDummyDeployEngine, self).setUp()

    def test_dummy_egnine_init(self):
        dummy_engine.DummyEngine(self.deployment)

    def test_dummy_engine_deploy(self):
        engine = dummy_engine.DummyEngine(self.deployment)
        endpoint = engine.deploy()
        self.assertEqual(endpoint, self.deployment['config']['cloud_config'])

    def test_dummy_engine_cleanup(self):
        dummy_engine.DummyEngine(self.deployment).cleanup()

    def test_dummy_engine_is_in_factory(self):
        name = self.deployment['config']['name']
        engine = deploy.EngineFactory.get_engine(name,
                                                 self.deployment)
        self.assertIsInstance(engine, dummy_engine.DummyEngine)

    def test_init_invalid_config(self):
        self.deployment['config']['cloud_config']['identity'] = 42
        self.assertRaises(jsonschema.ValidationError,
                          dummy_engine.DummyEngine, self.deployment)

    def test_deploy(self):
        engine = dummy_engine.DummyEngine(self.deployment)
        self.assertEqual(self.deployment['config']['cloud_config'],
                         engine.deploy())
