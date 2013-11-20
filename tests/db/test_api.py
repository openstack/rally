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
    def setUp(self):
        super(TasksTestCase, self).setUp()
        self.deploy = db.deployment_create({})

    def _get_task(self, uuid):
        return db.task_get(uuid)

    def _create_task(self, values=None):
        values = values or {}
        if 'deployment_uuid' not in values:
            values['deployment_uuid'] = self.deploy['uuid']
        return db.task_create(values)

    def test_task_get_not_found(self):
        self.assertRaises(exceptions.TaskNotFound,
                          db.task_get, str(uuid.uuid4()))

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


class DeploymentTestCase(test.DBTestCase):
    def test_deployment_create(self):
        deploy = db.deployment_create({'config': {'opt': 'val'}})
        deploys = db.deployment_list()
        self.assertEqual(len(deploys), 1)
        self.assertEqual(deploy['uuid'], deploys[0]['uuid'])
        self.assertEqual(deploy['status'], consts.DeployStatus.DEPLOY_INIT)
        self.assertEqual(deploy['config'], {'opt': 'val'})

    def test_deployment_create_several(self):
        # Create a deployment
        deploys = db.deployment_list()
        self.assertEqual(len(deploys), 0)
        deploy_one = db.deployment_create({'config': {'opt1': 'val1'}})
        deploys = db.deployment_list()
        self.assertEqual(len(deploys), 1)
        self.assertEqual(deploy_one['uuid'], deploys[0]['uuid'])
        self.assertEqual(deploy_one['status'], consts.DeployStatus.DEPLOY_INIT)
        self.assertEqual(deploy_one['config'], {'opt1': 'val1'})

        # Create another deployment and sure that they are different
        deploy_two = db.deployment_create({'config': {'opt2': 'val2'}})
        deploys = db.deployment_list()
        self.assertEqual(len(deploys), 2)
        self.assertEqual([deploy_one['uuid'], deploy_two['uuid']],
                         [deploy['uuid'] for deploy in deploys])
        self.assertNotEqual(deploy_one['uuid'], deploy_two['uuid'])
        self.assertEqual(deploy_two['status'], consts.DeployStatus.DEPLOY_INIT)
        self.assertEqual(deploy_two['config'], {'opt2': 'val2'})

    def test_deployment_update(self):
        deploy = db.deployment_create({})
        self.assertEqual(deploy['config'], {})
        update_deploy = db.deployment_update(deploy['uuid'],
                                             {'config': {'opt': 'val'}})
        self.assertEqual(update_deploy['uuid'], deploy['uuid'])
        self.assertEqual(update_deploy['config'], {'opt': 'val'})
        get_deploy = db.deployment_get(deploy['uuid'])
        self.assertEqual(get_deploy['uuid'], deploy['uuid'])
        self.assertEqual(get_deploy['config'], {'opt': 'val'})

    def test_deployment_update_several(self):
        # Create a deployment and update it
        deploy_one = db.deployment_create({})
        self.assertEqual(deploy_one['config'], {})
        update_deploy_one = db.deployment_update(
            deploy_one['uuid'],
            {'config': {'opt1': 'val1'}},
        )
        self.assertEqual(update_deploy_one['uuid'], deploy_one['uuid'])
        self.assertEqual(update_deploy_one['config'], {'opt1': 'val1'})
        get_deploy_one = db.deployment_get(deploy_one['uuid'])
        self.assertEqual(get_deploy_one['uuid'], deploy_one['uuid'])
        self.assertEqual(get_deploy_one['config'], {'opt1': 'val1'})

        # Create another deployment
        deploy_two = db.deployment_create({})
        update_deploy_two = db.deployment_update(
            deploy_two['uuid'],
            {'config': {'opt2': 'val2'}},
        )
        self.assertEqual(update_deploy_two['uuid'], deploy_two['uuid'])
        self.assertEqual(update_deploy_two['config'], {'opt2': 'val2'})
        get_deploy_one_again = db.deployment_get(deploy_one['uuid'])
        self.assertEqual(get_deploy_one_again['uuid'], deploy_one['uuid'])
        self.assertEqual(get_deploy_one_again['config'], {'opt1': 'val1'})

    def test_deployment_get(self):
        deploy_one = db.deployment_create({'config': {'opt1': 'val1'}})
        deploy_two = db.deployment_create({'config': {'opt2': 'val2'}})
        get_deploy_one = db.deployment_get(deploy_one['uuid'])
        get_deploy_two = db.deployment_get(deploy_two['uuid'])
        self.assertNotEqual(get_deploy_one['uuid'], get_deploy_two['uuid'])
        self.assertEqual(get_deploy_one['config'], {'opt1': 'val1'})
        self.assertEqual(get_deploy_two['config'], {'opt2': 'val2'})

    def test_deployment_get_not_found(self):
        self.assertRaises(exceptions.DeploymentNotFound,
                          db.deployment_get, str(uuid.uuid4()))

    def test_deployment_list(self):
        deploy_one = db.deployment_create({})
        deploy_two = db.deployment_create({})
        deploys = db.deployment_list()
        self.assertEqual(sorted([deploy_one['uuid'], deploy_two['uuid']]),
                         sorted([deploy['uuid'] for deploy in deploys]))

    def test_deployment_list_with_status(self):
        deploy_one = db.deployment_create({})
        deploy_two = db.deployment_create({
            'config': {},
            'status': consts.DeployStatus.DEPLOY_FAILED,
        })
        deploys = db.deployment_list(status=consts.DeployStatus.DEPLOY_INIT)
        self.assertEqual(len(deploys), 1)
        self.assertEqual(deploys[0]['uuid'], deploy_one['uuid'])
        deploys = db.deployment_list(status=consts.DeployStatus.DEPLOY_FAILED)
        self.assertEqual(len(deploys), 1)
        self.assertEqual(deploys[0]['uuid'], deploy_two['uuid'])
        deploys = db.deployment_list(
            status=consts.DeployStatus.DEPLOY_FINISHED)
        self.assertEqual(len(deploys), 0)

    def test_deployment_delete(self):
        deploy_one = db.deployment_create({})
        deploy_two = db.deployment_create({})
        db.deployment_delete(deploy_two['uuid'])
        deploys = db.deployment_list()
        self.assertEqual(len(deploys), 1)
        self.assertEqual(deploys[0]['uuid'], deploy_one['uuid'])

    def test_deployment_delete_not_found(self):
        self.assertRaises(exceptions.DeploymentNotFound,
                          db.deployment_delete, str(uuid.uuid4()))

    def test_deployment_delete_is_busy(self):
        deployment = db.deployment_create({})
        db.resource_create({'deployment_uuid': deployment['uuid']})
        db.resource_create({'deployment_uuid': deployment['uuid']})
        self.assertRaises(exceptions.DeploymentIsBusy, db.deployment_delete,
                          deployment['uuid'])


class ResourceTestCase(test.DBTestCase):
    def test_create(self):
        deployment = db.deployment_create({})
        resource = db.resource_create({
            'deployment_uuid': deployment['uuid'],
            'provider_name': 'fakeprovider',
            'type': 'faketype',
        })
        resources = db.resource_get_all(deployment['uuid'])
        self.assertTrue(resource['id'])
        self.assertEqual(len(resources), 1)
        self.assertTrue(resource['id'], resources[0]['id'])
        self.assertEqual(resource['deployment_uuid'], deployment['uuid'])
        self.assertEqual(resource['provider_name'], 'fakeprovider')
        self.assertEqual(resource['type'], 'faketype')

    def test_delete(self):
        deployment = db.deployment_create({})
        res = db.resource_create({'deployment_uuid': deployment['uuid']})
        db.resource_delete(res['id'])
        resources = db.resource_get_all(deployment['id'])
        self.assertEqual(len(resources), 0)

    def test_delete_not_found(self):
        self.assertRaises(exceptions.ResourceNotFound,
                          db.resource_delete, str(uuid.uuid4()))

    def test_get_all(self):
        deployment0 = db.deployment_create({})
        deployment1 = db.deployment_create({})
        res0 = db.resource_create({'deployment_uuid': deployment0['uuid']})
        res1 = db.resource_create({'deployment_uuid': deployment1['uuid']})
        res2 = db.resource_create({'deployment_uuid': deployment1['uuid']})
        resources = db.resource_get_all(deployment1['uuid'])
        self.assertEqual(sorted([res1['id'], res2['id']]),
                         sorted([r['id'] for r in resources]))
        resources = db.resource_get_all(deployment0['uuid'])
        self.assertEqual(len(resources), 1)
        self.assertEqual(res0['id'], resources[0]['id'])

    def test_get_all_by_provider_name(self):
        deployment = db.deployment_create({})
        res_one = db.resource_create({
            'deployment_uuid': deployment['uuid'],
            'provider_name': 'one',
        })
        res_two = db.resource_create({
            'deployment_uuid': deployment['uuid'],
            'provider_name': 'two',
        })
        resources = db.resource_get_all(deployment['uuid'],
                                        provider_name='one')
        self.assertEqual(len(resources), 1)
        self.assertEqual(res_one['id'], resources[0]['id'])
        resources = db.resource_get_all(deployment['uuid'],
                                        provider_name='two')
        self.assertEqual(len(resources), 1)
        self.assertEqual(res_two['id'], resources[0]['id'])

    def test_get_all_by_provider_type(self):
        deployment = db.deployment_create({})
        res_one = db.resource_create({
            'deployment_uuid': deployment['uuid'],
            'type': 'one',
        })
        res_two = db.resource_create({
            'deployment_uuid': deployment['uuid'],
            'type': 'two',
        })
        resources = db.resource_get_all(deployment['uuid'],
                                        type='one')
        self.assertEqual(len(resources), 1)
        self.assertEqual(res_one['id'], resources[0]['id'])
        resources = db.resource_get_all(deployment['uuid'],
                                        type='two')
        self.assertEqual(len(resources), 1)
        self.assertEqual(res_two['id'], resources[0]['id'])
