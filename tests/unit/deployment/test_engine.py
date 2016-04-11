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

from rally import consts
from rally.deployment import engine
from rally import exceptions
from tests.unit import test


def make_fake_deployment(**kwargs):
    values = dict({
        "uuid": "1359befb-8737-4f4e-bea9-492416106977",
        "config": {
            "name": "fake",
        },
        "status": consts.DeployStatus.DEPLOY_INIT,
    }, **kwargs)
    return FakeDeployment(values=values)


class FakeDeployment(object):

    def __init__(self, values=None):
        if values is None:
            values = {}
        self._values = values

    def __getitem__(self, name):
        return self._values[name]

    def update_status(self, status):
        self._values["status"] = status

    def set_started(self):
        pass

    def set_completed(self):
        pass

    def delete(self):
        pass


@engine.configure(name="FakeEngine")
class FakeEngine(engine.Engine):
    """Fake deployment engine.

    Used for tests.
    """
    deployed = False
    cleanuped = False

    def __init__(self, deployment):
        super(FakeEngine, self).__init__(deployment)
        self.deployment = deployment

    def deploy(self):
        self.deployed = True
        return self

    def cleanup(self):
        self.cleanuped = True


class EngineMixIn(object):
    def deploy(self):
        pass

    def cleanup(self):
        pass


class EngineTestCase(test.TestCase):

    def test_get_engine_not_found(self):
        deployment = make_fake_deployment()
        self.assertRaises(exceptions.PluginNotFound,
                          engine.Engine.get_engine,
                          "non_existing_engine", deployment)
        self.assertEqual(consts.DeployStatus.DEPLOY_FAILED,
                         deployment["status"])

    @mock.patch.object(FakeDeployment, "set_completed")
    @mock.patch.object(FakeDeployment, "set_started")
    def test_make_deploy(self, mock_fake_deployment_set_started,
                         mock_fake_deployment_set_completed):
        deployment = make_fake_deployment()
        engine = FakeEngine(deployment)
        credential = engine.make_deploy()
        self.assertEqual(engine, credential)
        self.assertTrue(credential.deployed)
        self.assertFalse(credential.cleanuped)
        mock_fake_deployment_set_completed.assert_called_once_with()
        mock_fake_deployment_set_started.assert_called_once_with()

    @mock.patch.object(FakeDeployment, "set_started")
    @mock.patch.object(FakeEngine, "deploy")
    def test_make_deploy_failed(self, mock_fake_engine_deploy,
                                mock_fake_deployment_set_started):
        class DeployFailed(Exception):
            pass

        deployment = make_fake_deployment()
        engine = FakeEngine(deployment)
        mock_fake_engine_deploy.side_effect = DeployFailed()
        self.assertRaises(DeployFailed, engine.make_deploy)
        mock_fake_deployment_set_started.assert_called_once_with()

    @mock.patch.object(FakeDeployment, "update_status")
    def test_make_cleanup(self, mock_fake_deployment_update_status):
        deployment = make_fake_deployment()
        engine = FakeEngine(deployment)
        engine.make_cleanup()
        self.assertTrue(engine.cleanuped)
        self.assertFalse(engine.deployed)
        mock_fake_deployment_update_status.assert_has_calls([
            mock.call(consts.DeployStatus.CLEANUP_STARTED),
            mock.call(consts.DeployStatus.CLEANUP_FINISHED),
        ])
        self.assertTrue(engine.cleanuped)

    @mock.patch.object(FakeDeployment, "update_status")
    @mock.patch.object(FakeEngine, "cleanup")
    def test_make_cleanup_failed(self, mock_fake_engine_cleanup,
                                 mock_fake_deployment_update_status):
        class CleanUpFailed(Exception):
            pass

        deployment = make_fake_deployment()
        engine = FakeEngine(deployment)
        mock_fake_engine_cleanup.side_effect = CleanUpFailed()
        self.assertRaises(CleanUpFailed, engine.make_cleanup)
        mock_fake_deployment_update_status.assert_has_calls([
            mock.call(consts.DeployStatus.CLEANUP_STARTED),
        ])
        self.assertFalse(engine.cleanuped)

    @mock.patch.object(FakeDeployment, "update_status")
    def test_with_statement(self, mock_fake_deployment_update_status):
        deployment = make_fake_deployment()
        engine = FakeEngine(deployment)
        with engine as deployer:
            self.assertEqual(engine, deployer)
        self.assertFalse(mock_fake_deployment_update_status.called)
        self.assertFalse(engine.cleanuped)
        self.assertFalse(engine.deployed)

    def test_with_statement_failed_on_init(self):
        self._assert_changed_status_on_error(
            consts.DeployStatus.DEPLOY_INIT,
            consts.DeployStatus.DEPLOY_FAILED)

    def test_with_statement_failed_on_started(self):
        self._assert_changed_status_on_error(
            consts.DeployStatus.DEPLOY_STARTED,
            consts.DeployStatus.DEPLOY_FAILED)

    def test_with_statement_failed_on_finished(self):
        self._assert_changed_status_on_error(
            consts.DeployStatus.DEPLOY_FINISHED,
            consts.DeployStatus.DEPLOY_INCONSISTENT)

    def test_with_statement_failed_on_cleanup(self):
        self._assert_changed_status_on_error(
            consts.DeployStatus.CLEANUP_STARTED,
            consts.DeployStatus.CLEANUP_FAILED)

    @mock.patch.object(FakeDeployment, "update_status")
    def _assert_changed_status_on_error(self, initial, final,
                                        mock_fake_deployment_update_status):

        class SomeError(Exception):
            pass

        def context_with_error(manager):
            with mock.patch("traceback.print_exception"):
                with manager:
                    raise SomeError()

        deployment = make_fake_deployment(status=initial)
        engine = FakeEngine(deployment)
        self.assertRaises(SomeError, context_with_error, engine)
        mock_fake_deployment_update_status.assert_called_once_with(final)
        self.assertFalse(engine.cleanuped)
        self.assertFalse(engine.deployed)

    def test_get_engine(self):
        deployment = make_fake_deployment()
        engine_inst = engine.Engine.get_engine("FakeEngine",
                                               deployment)
        self.assertIsInstance(engine_inst, FakeEngine)

    def test_engine_factory_is_abstract(self):
        self.assertRaises(TypeError, engine.Engine)
