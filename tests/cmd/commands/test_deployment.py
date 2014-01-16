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

from rally.cmd.commands import deployment
from rally import exceptions
from rally.openstack.common import test


class DeploymentCommandsTestCase(test.BaseTestCase):
    def setUp(self):
        super(DeploymentCommandsTestCase, self).setUp()
        self.deployment = deployment.DeploymentCommands()

    @mock.patch('rally.cmd.commands.deployment.api.create_deploy')
    @mock.patch('rally.cmd.commands.deployment.open',
                mock.mock_open(read_data='{"some": "json"}'),
                create=True)
    def test_create(self, mock_create):
        self.deployment.create('fake_deploy', False, 'path_to_config.json')
        mock_create.assert_called_once_with({'some': 'json'}, 'fake_deploy')

    @mock.patch.dict(os.environ, {'OS_AUTH_URL': 'fake_auth_url',
                                  'OS_USERNAME': 'fake_username',
                                  'OS_PASSWORD': 'fake_password',
                                  'OS_TENANT_NAME': 'fake_tenant_name'})
    @mock.patch('rally.cmd.commands.deployment.api.create_deploy')
    def test_createfromenv(self, mock_create):
        self.deployment.create('from_env', True)
        mock_create.assert_called_once_with(
            {
                "name": "DummyEngine",
                "endpoint": {
                    "auth_url": 'fake_auth_url',
                    "username": 'fake_username',
                    "password": 'fake_password',
                    "tenant_name": 'fake_tenant_name'
                }
            },
            'from_env'
        )

    @mock.patch('rally.cmd.commands.deployment.DeploymentCommands.list')
    @mock.patch('rally.cmd.commands.use.UseCommands.deployment')
    @mock.patch('rally.cmd.commands.deployment.api.create_deploy',
                return_value=dict(uuid='uuid'))
    @mock.patch('rally.cmd.commands.deployment.open',
                mock.mock_open(read_data='{"uuid": "uuid"}'),
                create=True)
    def test_create_and_use(self, mock_create, mock_use_deployment,
                            mock_list):
        self.deployment.create('fake_deploy', False, 'path_to_config.json',
                               True)
        mock_create.assert_called_once_with({'uuid': 'uuid'}, 'fake_deploy')
        mock_use_deployment.assert_called_once_with('uuid')

    @mock.patch('rally.cmd.commands.deployment.api.recreate_deploy')
    def test_recreate(self, mock_recreate):
        deploy_id = str(uuid.uuid4())
        self.deployment.recreate(deploy_id)
        mock_recreate.assert_called_once_with(deploy_id)

    @mock.patch('rally.cmd.commands.deployment.envutils.'
                '_default_deployment_id')
    def test_recreate_no_deploy_id(self, mock_default):
        mock_default.side_effect = exceptions.InvalidArgumentsException
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.deployment.recreate, None)

    @mock.patch('rally.cmd.commands.deployment.api.destroy_deploy')
    def test_destroy(self, mock_destroy):
        deploy_id = str(uuid.uuid4())
        self.deployment.destroy(deploy_id)
        mock_destroy.assert_called_once_with(deploy_id)

    @mock.patch('rally.cmd.commands.deployment.envutils.'
                '_default_deployment_id')
    def test_destroy_no_deploy_id(self, mock_default):
        mock_default.side_effect = exceptions.InvalidArgumentsException
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.deployment.destroy, None)

    @mock.patch('rally.cmd.commands.deployment.db.deployment_get')
    def test_config(self, mock_deployment):
        deploy_id = str(uuid.uuid4())
        value = {'config': 'config'}
        mock_deployment.return_value = value
        self.deployment.config(deploy_id)
        mock_deployment.assert_called_once_with(deploy_id)

    @mock.patch('rally.cmd.commands.deployment.envutils.'
                '_default_deployment_id')
    def test_config_no_deploy_id(self, mock_default):
        mock_default.side_effect = exceptions.InvalidArgumentsException
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.deployment.config, None)

    @mock.patch('rally.cmd.commands.deployment.db.deployment_get')
    def test_endpoint(self, mock_deployment):
        deploy_id = str(uuid.uuid4())
        value = {'endpoints': [{}]}
        mock_deployment.return_value = value
        self.deployment.endpoint(deploy_id)
        mock_deployment.assert_called_once_with(deploy_id)

    @mock.patch('rally.cmd.commands.deployment.envutils.'
                '_default_deployment_id')
    def test_deploy_no_deploy_id(self, mock_default):
        mock_default.side_effect = exceptions.InvalidArgumentsException
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.deployment.endpoint, None)
