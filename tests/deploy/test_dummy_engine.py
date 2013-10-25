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

import mock

from rally import deploy
from rally.deploy.engines import dummy_engine
from rally import test


class TestDummyDeployEngine(test.TestCase):

    def test_dummy_egnine_init(self):
        dummy_engine.DummyEngine(mock.MagicMock(), {})

    def test_dummy_engine_init_with_deploy_config(self):
        cloud_config = {'cloud_config': {'a': 1, 'b': 2}}
        dummy_engine.DummyEngine(mock.MagicMock(), cloud_config)

    def test_dummy_engine_deploy(self):
        cloud_config = {'cloud_config': {'a': 1, 'b': 2}}
        engine = dummy_engine.DummyEngine(mock.MagicMock(), cloud_config)
        self.assertEqual(engine.deploy(), cloud_config['cloud_config'])

    def test_dummy_engine_cleanup(self):
        dummy_engine.DummyEngine(mock.MagicMock(), {}).cleanup()

    def test_dummy_engine_is_in_factory(self):
        engine = deploy.EngineFactory.get_engine('DummyEngine',
                                                 mock.MagicMock(), {})
        self.assertIsInstance(engine, dummy_engine.DummyEngine)
