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

""" Test for orchestrator. """

import mock
import uuid

from rally.benchmark import base
from rally import consts
from rally.orchestrator import api
from rally import test


FAKE_DEPLOY_CONFIG = {
    # TODO(akscram): A fake engine is more suitable for that.
    'name': 'DummyEngine',
    'cloud_config': {
        'identity': {
            'url': 'http://example.net/',
            'uri': 'http://example.net:5000/v2.0/',
            'admin_username': 'admin',
            'admin_password': 'myadminpass',
            'admin_tenant_name': 'demo'
        },
    },
}


FAKE_TASK_CONFIG = {
    'verify': ['fake_test'],
    'benchmark': {
        'FakeScenario.fake': [
            {
                'args': {},
                'execution': 'continuous',
                'config': {
                    'timeout': 10000,
                    'times': 1,
                    'active_users': 1,
                    'tenants': 1,
                    'users_per_tenant': 1,
                }
            },
        ],
    },
}


class FakeScenario(base.Scenario):
    @classmethod
    def fake(cls, context):
        pass


# TODO(akscram): The test cases are very superficial because they test
#                only database operations and actually no more. Each
#                case in this test should to mock everything external.
class APITestCase(test.TestCase):
    def setUp(self):
        super(APITestCase, self).setUp()
        self.deploy_config = FAKE_DEPLOY_CONFIG
        self.task_config = FAKE_TASK_CONFIG
        self.deploy_uuid = str(uuid.uuid4())
        self.endpoint = FAKE_DEPLOY_CONFIG['cloud_config']
        self.task_uuid = str(uuid.uuid4())
        self.task = {
            'uuid': self.task_uuid,
        }
        self.deployment = {
            'uuid': self.deploy_uuid,
            'name': 'fake_name',
            'config': self.deploy_config,
            'endpoint': self.endpoint,
        }

    @mock.patch('rally.benchmark.engine.utils.ScenarioRunner')
    @mock.patch('rally.benchmark.engine.utils.Verifier')
    @mock.patch('rally.objects.deploy.db.deployment_get')
    @mock.patch('rally.objects.task.db.task_result_create')
    @mock.patch('rally.objects.task.db.task_update')
    @mock.patch('rally.objects.task.db.task_create')
    def test_start_task(self, mock_task_create, mock_task_update,
                        mock_task_result_create, mock_deploy_get,
                        mock_utils_verifier, mock_utils_runner):
        mock_task_create.return_value = self.task
        mock_task_update.return_value = self.task
        mock_deploy_get.return_value = self.deployment

        mock_utils_verifier.return_value = mock_verifier = mock.Mock()
        mock_utils_verifier.list_verification_tests.return_value = {
            'fake_test': mock.Mock(),
        }
        mock_verifier.run_all.return_value = [{
            'status': 0,
        }]

        mock_utils_runner.return_value = mock_runner = mock.Mock()
        mock_runner.run.return_value = ['fake_result']

        api.start_task(self.deploy_uuid, self.task_config)

        mock_deploy_get.assert_called_once_with(self.deploy_uuid)
        mock_task_create.assert_called_once_with({
            'deployment_uuid': self.deploy_uuid,
        })
        mock_task_update.assert_has_calls([
            mock.call(self.task_uuid,
                      {'status': 'test_tool->verify_openstack'}),
            mock.call(self.task_uuid,
                      {'verification_log': '[{"status": 0}]'}),
            mock.call(self.task_uuid,
                      {'status': 'test_tool->benchmarking'})
        ])
        # NOTE(akscram): It looks really awful, but checks degradation.
        mock_task_result_create.assert_called_once_with(
            self.task_uuid,
            {
                'kw': {
                    'args': {},
                    'execution': 'continuous',
                    'config': {
                        'timeout': 10000,
                        'times': 1,
                        'active_users': 1,
                        'tenants': 1,
                        'users_per_tenant': 1,
                    }
                },
                'name': 'FakeScenario.fake',
                'pos': 0,
            },
            {
                'raw': ['fake_result'],
            },
        )

    def test_abort_task(self):
        self.assertRaises(NotImplementedError, api.abort_task,
                          self.task_uuid)

    @mock.patch('rally.objects.task.db.task_delete')
    def test_delete_task(self, mock_delete):
        api.delete_task(self.task_uuid)
        mock_delete.assert_called_once_with(
            self.task_uuid,
            status=consts.TaskStatus.FINISHED)

    @mock.patch('rally.objects.task.db.task_delete')
    def test_delete_task_force(self, mock_delete):
        api.delete_task(self.task_uuid, force=True)
        mock_delete.assert_called_once_with(self.task_uuid, status=None)

    @mock.patch('rally.objects.deploy.db.deployment_update')
    @mock.patch('rally.objects.deploy.db.deployment_create')
    def test_create_deploy(self, mock_create, mock_update):
        mock_create.return_value = self.deployment
        mock_update.return_value = self.deployment
        api.create_deploy(self.deploy_config, 'fake_deploy')
        mock_create.assert_called_once_with({
            'name': 'fake_deploy',
            'config': self.deploy_config,
        })
        mock_update.assert_has_calls([
            mock.call(self.deploy_uuid, {'endpoint': self.endpoint}),
        ])

    @mock.patch('rally.objects.deploy.db.deployment_delete')
    @mock.patch('rally.objects.deploy.db.deployment_update')
    @mock.patch('rally.objects.deploy.db.deployment_get')
    def test_destroy_deploy(self, mock_get, mock_update, mock_delete):
        mock_get.return_value = self.deployment
        mock_update.return_value = self.deployment
        api.destroy_deploy(self.deploy_uuid)
        mock_get.assert_called_once_with(self.deploy_uuid)
        mock_delete.assert_called_once_with(self.deploy_uuid)

    @mock.patch('rally.objects.deploy.db.deployment_update')
    @mock.patch('rally.objects.deploy.db.deployment_get')
    def test_recreate_deploy(self, mock_get, mock_update):
        mock_get.return_value = self.deployment
        mock_update.return_value = self.deployment
        api.recreate_deploy(self.deploy_uuid)
        mock_get.assert_called_once_with(self.deploy_uuid)
        mock_update.assert_has_calls([
            mock.call(self.deploy_uuid, {'endpoint': self.endpoint}),
        ])
