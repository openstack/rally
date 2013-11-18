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
import uuid

from rally import consts
from rally import deploy
from rally import exceptions
from rally import test


# XXX(akscram): The assertRaises of testtools can't be used as a
#               context manager:
#                   with self.assertRaises(SomeError):
#                       with engine as deployer:
#                           raise SomeError()
#               instead of:
#                   self.assertRaises(SomeError, engine_with_error,
#                                     engine, SomeError())
def engine_with_error(error, engine):
    with engine:
        raise error


class FakeDeployment(object):

    def __init__(self, values={}):
        self._values = values

    def __getitem__(self, name):
        return self._values[name]

    def update_status(self, status):
        pass

    def delete(self):
        pass


class FakeEngine(deploy.EngineFactory):
    deployed = False
    cleanuped = False

    def __init__(self, deployment):
        self.deployment = deployment

    def deploy(self):
        self.deployed = True
        return self

    def cleanup(self):
        self.cleanuped = True


class EngineFactoryTestCase(test.TestCase):
    def setUp(self):
        super(EngineFactoryTestCase, self).setUp()
        self.deployment = FakeDeployment({
            'uuid': uuid.uuid4(),
            'config': {
                'name': 'fake',
            },
        })

    @mock.patch.object(FakeDeployment, 'update_status')
    def test_make_deploy(self, mock_update_status):
        engine = FakeEngine(self.deployment)
        endpoint = engine.make_deploy()
        self.assertEqual(engine, endpoint)
        self.assertTrue(endpoint.deployed)
        self.assertFalse(endpoint.cleanuped)
        mock_update_status.assert_has_calls([
            mock.call(consts.DeployStatus.DEPLOY_STARTED),
            mock.call(consts.DeployStatus.DEPLOY_FINISHED),
        ])

    @mock.patch.object(FakeDeployment, 'update_status')
    def test_with_statement(self, mock_update_status):
        engine = FakeEngine(self.deployment)
        with engine as deployer:
            self.assertEqual(engine, deployer)
        self.assertFalse(mock_update_status.called)
        self.assertFalse(engine.cleanuped)
        self.assertFalse(engine.deployed)

    @mock.patch.object(FakeDeployment, 'update_status')
    def test_with_statement_failed(self, mock_update_status):
        class SomeError(Exception):
            pass

        engine = FakeEngine(self.deployment)
        self.assertRaises(SomeError, engine_with_error, SomeError(), engine)
        mock_update_status.assert_called_once_with(
            consts.DeployStatus.DEPLOY_INCONSISTENT)
        self.assertFalse(engine.cleanuped)
        self.assertFalse(engine.deployed)

    @mock.patch.object(FakeDeployment, 'update_status')
    @mock.patch.object(FakeEngine, 'deploy')
    def test_make_deploy_failed(self, mock_deploy, mock_update_status):
        class DeployFailed(Exception):
            pass

        engine = FakeEngine(self.deployment)
        mock_deploy.side_effect = DeployFailed()
        self.assertRaises(DeployFailed, engine.make_deploy)
        mock_update_status.assert_has_calls([
            mock.call(consts.DeployStatus.DEPLOY_STARTED),
            mock.call(consts.DeployStatus.DEPLOY_FAILED),
        ])

    @mock.patch.object(FakeDeployment, 'update_status')
    def test_make_cleanup(self, mock_update_status):
        engine = FakeEngine(self.deployment)
        engine.make_cleanup()
        self.assertTrue(engine.cleanuped)
        self.assertFalse(engine.deployed)
        mock_update_status.assert_has_calls([
            mock.call(consts.DeployStatus.CLEANUP_STARTED),
            mock.call(consts.DeployStatus.CLEANUP_FINISHED),
        ])
        self.assertTrue(engine.cleanuped)

    @mock.patch.object(FakeDeployment, 'update_status')
    @mock.patch.object(FakeEngine, 'cleanup')
    def test_make_cleanup_failed(self, mock_cleanup, mock_update_status):
        class CleanUpFailed(Exception):
            pass

        engine = FakeEngine(self.deployment)
        mock_cleanup.side_effect = CleanUpFailed()
        self.assertRaises(CleanUpFailed, engine.make_cleanup)
        mock_update_status.assert_has_calls([
            mock.call(consts.DeployStatus.CLEANUP_STARTED),
            mock.call(consts.DeployStatus.CLEANUP_FAILED),
        ])
        self.assertFalse(engine.cleanuped)

    @mock.patch.object(FakeDeployment, 'update_status')
    def test_get_engine_not_found(self, mock_update_status):
        self.assertRaises(exceptions.NoSuchEngine,
                          deploy.EngineFactory.get_engine,
                          "non_existing_engine", self.deployment)
        mock_update_status.assert_called_once_with(
            consts.DeployStatus.DEPLOY_FAILED)

    def _create_fake_engines(self):
        class EngineMixIn(object):
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
                                                          self.deployment)
            # TODO(boris-42): make it work through assertIsInstance
            self.assertEqual(str(type(engine_inst)), str(e))

    def test_get_available_engines(self):
        engines = set([e.__name__ for e in self._create_fake_engines()])
        real_engines = set(deploy.EngineFactory.get_available_engines())
        self.assertEqual(engines & real_engines, engines)

    def test_engine_factory_is_abstract(self):
        self.assertRaises(TypeError, deploy.EngineFactory)
