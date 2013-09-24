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

"""Test for deploy engines."""

import mock

from rally import deploy
from rally import exceptions
from rally import test


class EngineFactoryTestCase(test.NoDBTestCase):

    def test_get_engine_not_found(self):
        self.assertRaises(exceptions.NoSuchEngine,
                          deploy.EngineFactory.get_engine, mock.Mock(),
                          "non_existing_engine", None)

    def _create_fake_engines(self):
        class EngineMixIn(object):

            def __init__(self, config):
                pass

            def deploy(self):
                pass

            def cleanup(self):
                pass

        class EngineFake1(EngineMixIn, deploy.EngineFactory):
            pass

        class EngineFake2(EngineMixIn, deploy.EngineFactory):
            pass

        class EngineFake3(EngineFake2):
            pass

        return [EngineFake1, EngineFake2, EngineFake3]

    def test_get_engine(self):
        engines = self._create_fake_engines()
        for e in engines:
            engine_inst = deploy.EngineFactory.get_engine(e.__name__,
                                                          mock.Mock(),
                                                          {})
            # TODO(boris-42): make it work through assertIsInstance
            self.assertEqual(str(type(engine_inst)), str(e))

    def test_get_available_engines(self):
        engines = set([e.__name__ for e in self._create_fake_engines()])
        real_engines = set(deploy.EngineFactory.get_available_engines())
        self.assertEqual(engines & real_engines, engines)

    def test_engine_factory_is_abstract(self):
        self.assertRaises(TypeError, deploy.EngineFactory)

    def test_with_statement(self):

        class A(deploy.EngineFactory):

            def __init__(self, config):
                pass

            def deploy(self):
                self.deployed = True
                return self

            def cleanup(self):
                self.cleanuped = True

        with deploy.EngineFactory.get_engine('A', mock.Mock(),
                                             None) as deployer:
            endpoints = deployer.make()
            self.assertTrue(endpoints.deployed)

        self.assertTrue(endpoints.cleanuped)
