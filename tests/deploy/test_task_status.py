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

"""Test task status update."""

import mock
import uuid

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


class TaskStatusTestCase(test.NoDBTestCase):

    def test_task_status_basic_chain(self):
        task_uuid = str(uuid.uuid4())
        with mock.patch('rally.deploy.engine.db') as mock_obj:
            with get_engine('FakeEngine', task_uuid, {}):
                pass
        s = consts.TaskStatus
        expected = [
            mock.call.task_update(task_uuid, {'status': s.DEPLOY_STARTED}),
            mock.call.task_update(task_uuid, {'status': s.DEPLOY_FINISHED}),
            mock.call.task_update(task_uuid, {'status': s.CLEANUP}),
            mock.call.task_update(task_uuid, {'status': s.FINISHED}),
        ]
        self.assertEqual(mock_obj.mock_calls, expected)

    def _test_failure(self, task_uuid, engine, expected_calls):
        with mock.patch('rally.deploy.engine.db') as mock_obj:
            engine = get_engine(engine, task_uuid, {})
            try:
                with engine:
                    pass
            except FakeFailure:
                pass
        self.assertEqual(mock_obj.mock_calls, expected_calls)

    def test_task_status_failed_deploy(self):
        task_uuid = str(uuid.uuid4())
        s = consts.TaskStatus
        expected = [
            mock.call.task_update(task_uuid, {'status': s.DEPLOY_STARTED}),
        ]
        self._test_failure(task_uuid, 'EngineFailedDeploy', expected)

    def test_task_status_failed_cleanup(self):
        task_uuid = str(uuid.uuid4())
        s = consts.TaskStatus
        expected = [
            mock.call.task_update(task_uuid, {'status': s.DEPLOY_STARTED}),
            mock.call.task_update(task_uuid, {'status': s.DEPLOY_FINISHED}),
            mock.call.task_update(task_uuid, {'status': s.CLEANUP}),
        ]
        self._test_failure(task_uuid, 'EngineFailedCleanup', expected)
