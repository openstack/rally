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

"""Tests for db.deploy layer."""

import mock
import uuid

from rally import consts
from rally import objects
from rally import test


class DeploymentTestCase(test.TestCase):
    def setUp(self):
        super(DeploymentTestCase, self).setUp()
        self.deployment = {
            'uuid': str(uuid.uuid4()),
            'name': '',
            'config': {},
            'endpoint': {},
            'status': consts.DeployStatus.DEPLOY_INIT,
        }

    @mock.patch('rally.objects.deploy.db.deployment_create')
    def test_init_with_create(self, mock_create):
        mock_create.return_value = self.deployment
        deploy = objects.Deployment()
        mock_create.assert_called_once_with({})
        self.assertEqual(deploy['uuid'], self.deployment['uuid'])

    @mock.patch('rally.objects.deploy.db.deployment_create')
    def test_init_without_create(self, mock_create):
        deploy = objects.Deployment(deployment=self.deployment)
        self.assertFalse(mock_create.called)
        self.assertEqual(deploy['uuid'], self.deployment['uuid'])

    @mock.patch('rally.objects.deploy.db.deployment_get')
    def test_get(self, mock_get):
        mock_get.return_value = self.deployment
        deploy = objects.Deployment.get(self.deployment['uuid'])
        mock_get.assert_called_once_with(self.deployment['uuid'])
        self.assertEqual(deploy['uuid'], self.deployment['uuid'])

    @mock.patch('rally.objects.deploy.db.deployment_delete')
    @mock.patch('rally.objects.deploy.db.deployment_create')
    def test_create_and_delete(self, mock_create, mock_delete):
        mock_create.return_value = self.deployment
        deploy = objects.Deployment()
        deploy.delete()
        mock_delete.assert_called_once_with(self.deployment['uuid'])

    @mock.patch('rally.objects.deploy.db.deployment_delete')
    def test_delete_by_uuid(self, mock_delete):
        objects.Deployment.delete_by_uuid(self.deployment['uuid'])
        mock_delete.assert_called_once_with(self.deployment['uuid'])

    @mock.patch('rally.objects.deploy.db.deployment_update')
    def test_update_status(self, mock_update):
        deploy = objects.Deployment(deployment=self.deployment)
        deploy.update_status(consts.DeployStatus.DEPLOY_FAILED)
        mock_update.assert_called_once_with(
            self.deployment['uuid'],
            {'status': consts.DeployStatus.DEPLOY_FAILED},
        )

    @mock.patch('rally.objects.deploy.db.deployment_update')
    def test_update_name(self, mock_update):
        deploy = objects.Deployment(deployment=self.deployment)
        deploy.update_name('new_name')
        mock_update.assert_called_once_with(
            self.deployment['uuid'],
            {'name': 'new_name'},
        )

    @mock.patch('rally.objects.deploy.db.deployment_update')
    def test_update_config(self, mock_update):
        deploy = objects.Deployment(deployment=self.deployment)
        deploy.update_config({'opt': 'val'})
        mock_update.assert_called_once_with(
            self.deployment['uuid'],
            {'config': {'opt': 'val'}},
        )

    @mock.patch('rally.objects.deploy.db.deployment_update')
    def test_update_endpoint(self, mock_update):
        deploy = objects.Deployment(deployment=self.deployment)
        deploy.update_endpoint({'opt': 'val'})
        mock_update.assert_called_once_with(
            self.deployment['uuid'],
            {'endpoint': {'opt': 'val'}},
        )
