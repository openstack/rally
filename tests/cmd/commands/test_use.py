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
        endpoint = {'endpoint': {'auth_url': 'fake_auth_url',
                                 'username': 'fake_username',
                                 'password': 'fake_password',
                                 'tenant_name': 'fake_tenant_name'}}
        mock_deployment.return_value = endpoint
        mock_path.return_value = True
        with mock.patch('rally.cmd.commands.use.open', mock.mock_open(),
                        create=True) as mock_file:
            self.use.deployment(deploy_id)
            self.assertEqual(2, mock_path.call_count)
            mock_env.assert_called_once_with(os.path.expanduser(
                '~/.rally/deployment'), 'RALLY_DEPLOYMENT', deploy_id)
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
