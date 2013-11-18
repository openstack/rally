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

"""Tests for db.task layer."""

import mock
import uuid

from rally import consts
from rally import objects
from rally import test


class TaskTestCase(test.TestCase):
    def setUp(self):
        super(TaskTestCase, self).setUp()
        self.task = {
            'uuid': str(uuid.uuid4()),
            'status': consts.TaskStatus.INIT,
            'failed': False,
            'verification_log': '',
        }

    @mock.patch('rally.objects.task.db.task_create')
    def test_init_with_create(self, mock_create):
        mock_create.return_value = self.task
        task = objects.Task(failed=True)
        mock_create.assert_called_once_with({'failed': True})
        self.assertEqual(task['uuid'], self.task['uuid'])

    @mock.patch('rally.objects.task.db.task_create')
    def test_init_without_create(self, mock_create):
        task = objects.Task(task=self.task)
        self.assertFalse(mock_create.called)
        self.assertEqual(task['uuid'], self.task['uuid'])

    @mock.patch('rally.objects.task.db.task_get')
    def test_get(self, mock_get):
        mock_get.return_value = self.task
        task = objects.Task.get(self.task['uuid'])
        mock_get.assert_called_once_with(self.task['uuid'])
        self.assertEqual(task['uuid'], self.task['uuid'])

    @mock.patch('rally.objects.task.db.task_delete')
    @mock.patch('rally.objects.task.db.task_create')
    def test_create_and_delete(self, mock_create, mock_delete):
        mock_create.return_value = self.task
        task = objects.Task()
        task.delete()
        mock_delete.assert_called_once_with(self.task['uuid'], status=None)

    @mock.patch('rally.objects.task.db.task_delete')
    @mock.patch('rally.objects.task.db.task_create')
    def test_create_and_delete_status(self, mock_create, mock_delete):
        mock_create.return_value = self.task
        task = objects.Task()
        task.delete(status=consts.TaskStatus.FINISHED)
        mock_delete.assert_called_once_with(self.task['uuid'],
                                            status=consts.TaskStatus.FINISHED)

    @mock.patch('rally.objects.task.db.task_delete')
    def test_delete_by_uuid(self, mock_delete):
        objects.Task.delete_by_uuid(self.task['uuid'])
        mock_delete.assert_called_once_with(self.task['uuid'], status=None)

    @mock.patch('rally.objects.task.db.task_delete')
    def test_delete_by_uuid_status(self, mock_delete):
        objects.Task.delete_by_uuid(self.task['uuid'],
                                    consts.TaskStatus.FINISHED)
        mock_delete.assert_called_once_with(self.task['uuid'],
                                            status=consts.TaskStatus.FINISHED)

    @mock.patch('rally.objects.deploy.db.task_update')
    @mock.patch('rally.objects.task.db.task_create')
    def test_update(self, mock_create, mock_update):
        mock_create.return_value = self.task
        mock_update.return_value = {'opt': 'val2'}
        deploy = objects.Task(opt='val1')
        deploy._update({'opt': 'val2'})
        mock_update.assert_called_once_with(self.task['uuid'],
                                            {'opt': 'val2'})
        self.assertEqual(deploy['opt'], 'val2')

    @mock.patch('rally.objects.task.db.task_update')
    def test_update_status(self, mock_update):
        mock_update.return_value = self.task
        task = objects.Task(task=self.task)
        task.update_status(consts.TaskStatus.FINISHED)
        mock_update.assert_called_once_with(
            self.task['uuid'],
            {'status': consts.TaskStatus.FINISHED},
        )

    @mock.patch('rally.objects.task.db.task_update')
    def test_update_verification_log(self, mock_update):
        mock_update.return_value = self.task
        task = objects.Task(task=self.task)
        task.update_verification_log('fake')
        mock_update.assert_called_once_with(
            self.task['uuid'],
            {'verification_log': 'fake'},
        )

    @mock.patch('rally.objects.task.db.task_result_create')
    def test_append_results(self, mock_append_results):
        task = objects.Task(task=self.task)
        task.append_results('opt', 'val')
        mock_append_results.assert_called_once_with(self.task['uuid'],
                                                    'opt', 'val')

    @mock.patch('rally.objects.task.db.task_update')
    def test_set_failed(self, mock_update):
        mock_update.return_value = self.task
        task = objects.Task(task=self.task)
        task.set_failed()
        mock_update.assert_called_once_with(
            self.task['uuid'],
            {'failed': True},
        )
