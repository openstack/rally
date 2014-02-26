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

import mock
import os
import uuid

from rally.cmd.commands import use
from rally.openstack.common import test

from rally import exceptions


class UseCommandsTestCase(test.BaseTestCase):
    def setUp(self):
        super(UseCommandsTestCase, self).setUp()
        self.use = use.UseCommands()

    @mock.patch('os.remove')
    @mock.patch('os.symlink')
    @mock.patch('rally.cmd.commands.use.db.deployment_get')
    @mock.patch('os.path.exists')
    @mock.patch('rally.cmd.commands.use.fileutils.update_env_file')
    def test_deployment(self, mock_env, mock_path, mock_deployment,
                        mock_symlink, mock_remove):
        deploy_id = str(uuid.uuid4())
        endpoints = {'endpoints': [{'auth_url': 'fake_auth_url',
                                    'username': 'fake_username',
                                    'password': 'fake_password',
                                    'tenant_name': 'fake_tenant_name'}]}
        mock_deployment.return_value = endpoints
        mock_path.return_value = True
        with mock.patch('rally.cmd.commands.use.open', mock.mock_open(),
                        create=True) as mock_file:
            self.use.deployment(deploy_id)
            self.assertEqual(2, mock_path.call_count)
            mock_env.assert_called_once_with(os.path.expanduser(
                '~/.rally/globals'), 'RALLY_DEPLOYMENT', '%s\n' % deploy_id)
            mock_file.return_value.write.assert_called_once_with(
                'export OS_AUTH_URL=fake_auth_url\n'
                'export OS_USERNAME=fake_username\n'
                'export OS_PASSWORD=fake_password\n'
                'export OS_TENANT_NAME=fake_tenant_name\n')
            mock_symlink.assert_called_once_with(
                os.path.expanduser('~/.rally/openrc-%s' % deploy_id),
                os.path.expanduser('~/.rally/openrc'))
            mock_remove.assert_called_once_with(os.path.expanduser(
                '~/.rally/openrc'))

    @mock.patch('rally.cmd.commands.use.db.deployment_get')
    def test_deployment_not_found(self, mock_deployment):
        deploy_id = str(uuid.uuid4())
        mock_deployment.side_effect = exceptions.DeploymentNotFound(
            uuid=deploy_id)
        self.assertRaises(exceptions.DeploymentNotFound,
                          self.use.deployment,
                          deploy_id)

    @mock.patch('rally.cmd.commands.use.fileutils._rewrite_env_file')
    @mock.patch('rally.cmd.commands.use.db.task_get')
    def test_task(self, mock_task, mock_file):
        task_id = str(uuid.uuid4())
        mock_task.return_value = True
        self.use.task(task_id)
        mock_file.assert_called_once_with(
            os.path.expanduser('~/.rally/globals'),
            ['RALLY_TASK=%s\n' % task_id])

    @mock.patch('rally.cmd.commands.use.db.task_get')
    def test_task_not_found(self, mock_task):
        task_id = str(uuid.uuid4())
        mock_task.side_effect = exceptions.TaskNotFound(uuid=task_id)
        self.assertRaises(exceptions.TaskNotFound, self.use.task, task_id)
