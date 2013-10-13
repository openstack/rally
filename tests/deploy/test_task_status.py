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

"""Test task status update."""

import mock

from rally import consts
from rally import deploy
from rally import test


class FakeFailure(Exception):
    pass


class EngineFailedDeploy(deploy.engines.fake_engine.FakeEngine):

    def deploy(self):
        raise FakeFailure('fake deploy failed')


class EngineFailedCleanup(deploy.engines.fake_engine.FakeEngine):

    def cleanup(self):
        raise FakeFailure('fake deploy failed')


get_engine = deploy.EngineFactory.get_engine


class DeployEngineTaskStatusTestCase(test.NoDBTestCase):

    def test_task_status_basic_chain(self):
        fake_task = mock.MagicMock()
        with get_engine('FakeEngine', fake_task, {}) as deployer:
            deployer.make()
        s = consts.TaskStatus
        expected = [
            mock.call.update_status(s.DEPLOY_STARTED),
            mock.call.update_status(s.DEPLOY_FINISHED),
            mock.call.update_status(s.CLEANUP),
            mock.call.update_status(s.FINISHED),
        ]
        # NOTE(msdubov): Ignore task['uuid'] calls which are used for logging
        mock_calls = filter(lambda call: '__getitem__' not in call[0],
                            fake_task.mock_calls)
        self.assertEqual(expected, mock_calls)

    def _test_failure(self, engine, expected_calls):
        fake_task = mock.MagicMock()
        try:
            with get_engine(engine, fake_task, {}) as deployer:
                deployer.make()
        except FakeFailure:
            pass
        # NOTE(msdubov): Ignore task['uuid'] calls which are used for logging
        mock_calls = filter(lambda call: '__getitem__' not in call[0],
                            fake_task.mock_calls)
        self.assertEqual(expected_calls, mock_calls)

    def test_task_status_failed_deploy(self):
        s = consts.TaskStatus
        expected = [
            mock.call.update_status(s.DEPLOY_STARTED),
            mock.call.set_failed(),
            mock.call.update_status(s.CLEANUP),
            mock.call.update_status(s.FINISHED),
        ]
        self._test_failure('EngineFailedDeploy', expected)

    def test_task_status_failed_cleanup(self):
        s = consts.TaskStatus
        expected = [
            mock.call.update_status(s.DEPLOY_STARTED),
            mock.call.update_status(s.DEPLOY_FINISHED),
            mock.call.update_status(s.CLEANUP),
            mock.call.set_failed(),
            mock.call.update_status(s.FINISHED),
        ]
        self._test_failure('EngineFailedCleanup', expected)
