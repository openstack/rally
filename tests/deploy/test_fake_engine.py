# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

"""Test fake deploy engines."""

import mock
import uuid

from rally import deploy
from rally.deploy.engines import fake_engine
from rally import test


class TestFakeDeployEngine(test.NoDBTestCase):

    def test_fake_egnine_init(self):
        fake_engine.FakeEngine({})

    def test_fake_engine_init_with_deploy_config(self):
        cloud_config = {'cloud_config': {'a': 1, 'b': 2}}
        fake_engine.FakeEngine(cloud_config)

    def test_fake_engine_deploy(self):
        cloud_config = {'cloud_config': {'a': 1, 'b': 2}}
        engine = fake_engine.FakeEngine(cloud_config)
        self.assertEqual(engine.deploy(), cloud_config['cloud_config'])

    def test_fake_engine_cleanup(self):
        fake_engine.FakeEngine({}).cleanup()

    def test_fake_engine_is_in_factory(self):
        with mock.patch('rally.db'):
            engine = deploy.EngineFactory.get_engine('FakeEngine',
                                                     uuid.uuid4(), {})
            self.assertIsInstance(engine, fake_engine.FakeEngine)
