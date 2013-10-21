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

"""Tests for db.api layer."""

import uuid

from rally import consts
from rally import db
from rally import exceptions
from rally import test


class TasksTestCase(test.DBTestCase):

    def _get_task(self, uuid):
        return db.task_get_by_uuid(uuid)

    def _create_task(self, values=None):
        return db.task_create(values or {})

    def test_task_get_by_uuid_not_found(self):
        self.assertRaises(exceptions.TaskNotFound,
                          db.task_get_by_uuid, str(uuid.uuid4()))

    def test_task_create(self):
        task = self._create_task()
        db_task = self._get_task(task['uuid'])
        self.assertIsNotNone(db_task['uuid'])
        self.assertIsNotNone(db_task['id'])
        self.assertEqual(db_task['status'], consts.TaskStatus.INIT)
        self.assertFalse(db_task['failed'])

    def test_task_create_without_uuid(self):
        _uuid = str(uuid.uuid4())
        task = self._create_task({'uuid': _uuid})
        db_task = self._get_task(task['uuid'])
        self.assertEqual(db_task['uuid'], _uuid)

    def test_task_update(self):
        task = self._create_task({})
        db.task_update(task['uuid'], {'failed': True})
        db_task = self._get_task(task['uuid'])
        self.assertTrue(db_task['failed'])

    def test_task_update_not_found(self):
        self.assertRaises(exceptions.TaskNotFound,
                          db.task_update, str(uuid.uuid4()), {})

    def test_task_update_all_stats(self):
        _uuid = self._create_task({})['uuid']
        for status in consts.TaskStatus:
            db.task_update(_uuid, {'status': status})
            db_task = self._get_task(_uuid)
            self.assertEqual(db_task['status'], status)

    def test_task_list_empty(self):
        self.assertEqual([], db.task_list())

    def test_task_list(self):
        INIT = consts.TaskStatus.INIT
        task_init = sorted(self._create_task()['uuid'] for i in xrange(3))
        FINISHED = consts.TaskStatus.FINISHED
        task_finished = sorted(self._create_task({'status': FINISHED})['uuid']
                               for i in xrange(3))

        task_all = sorted(task_init + task_finished)

        def get_uuids(status):
            tasks = db.task_list(status=status)
            return sorted(task['uuid'] for task in tasks)

        self.assertEqual(task_all, get_uuids(None))

        self.assertEqual(task_init, get_uuids(INIT))
        self.assertEqual(task_finished, get_uuids(FINISHED))

        deleted_task_uuid = task_finished.pop()
        db.task_delete(deleted_task_uuid)
        self.assertEqual(task_init, get_uuids(INIT))
        self.assertEqual(sorted(task_finished), get_uuids(FINISHED))

    def test_task_delete(self):
        task1, task2 = self._create_task()['uuid'], self._create_task()['uuid']
        db.task_delete(task1)
        self.assertRaises(exceptions.TaskNotFound, self._get_task, task1)
        self.assertEqual(task2, self._get_task(task2)['uuid'])

    def test_task_delete_not_found(self):
        self.assertRaises(exceptions.TaskNotFound,
                          db.task_delete, str(uuid.uuid4()))

    def test_task_delete_with_results(self):
        task_id = self._create_task()['uuid']
        db.task_result_create(task_id,
                              {task_id: task_id},
                              {task_id: task_id})
        res = db.task_result_get_all_by_uuid(task_id)
        self.assertEqual(len(res), 1)
        db.task_delete(task_id)
        res = db.task_result_get_all_by_uuid(task_id)
        self.assertEqual(len(res), 0)

    def test_task_delete_by_uuid_and_status(self):
        values = {
            'status': consts.TaskStatus.FINISHED,
        }
        task1 = self._create_task(values=values)['uuid']
        task2 = self._create_task(values=values)['uuid']
        db.task_delete(task1, status=consts.TaskStatus.FINISHED)
        self.assertRaises(exceptions.TaskNotFound, self._get_task, task1)
        self.assertEqual(task2, self._get_task(task2)['uuid'])

    def test_task_delete_by_uuid_and_status_invalid(self):
        task = self._create_task(values={
            'status': consts.TaskStatus.INIT,
        })['uuid']
        self.assertRaises(exceptions.TaskInvalidStatus, db.task_delete, task,
                          status=consts.TaskStatus.FINISHED)

    def test_task_delete_by_uuid_and_status_not_found(self):
        self.assertRaises(exceptions.TaskNotFound,
                          db.task_delete, str(uuid.uuid4()),
                          status=consts.TaskStatus.FINISHED)

    def test_task_result_get_all_by_uuid(self):
        task1 = self._create_task()['uuid']
        task2 = self._create_task()['uuid']

        for task_id in (task1, task2):
            db.task_result_create(task_id,
                                  {task_id: task_id},
                                  {task_id: task_id})

        for task_id in (task1, task2):
            res = db.task_result_get_all_by_uuid(task_id)
            data = {task_id: task_id}
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]['key'], data)
            self.assertEqual(res[0]['data'], data)

    def test_task_get_detailed(self):
        task1 = self._create_task()
        key = {'name': 'atata'}
        data = {'a': 'b', 'c': 'd'}

        db.task_result_create(task1['uuid'], key, data)
        task1_full = db.task_get_detailed(task1['uuid'])
        results = task1_full["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["key"], key)
        self.assertEqual(results[0]["data"], data)
