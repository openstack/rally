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
import uuid

from rally.cmd import main
from rally.openstack.common import test


class TaskCommandsTestCase(test.BaseTestCase):

    def setUp(self):
        super(TaskCommandsTestCase, self).setUp()
        self.task = main.TaskCommands()

    @mock.patch('rally.cmd.main.api.start_task')
    @mock.patch('rally.cmd.main.open',
                mock.mock_open(read_data='{"some": "json"}'),
                create=True)
    def test_start(self, mock_api):
        deploy_id = str(uuid.uuid4())
        self.task.start(deploy_id, 'path_to_config.json')
        mock_api.assert_called_once_with(deploy_id, {'some': 'json'})

    def test_abort(self):
        test_uuid = str(uuid.uuid4())
        with mock.patch("rally.cmd.main.api") as mock_api:
            mock_api.abort_task = mock.MagicMock()
            self.task.abort(test_uuid)
            main.api.abort_task.assert_called_once_with(test_uuid)

    def test_status(self):
        test_uuid = str(uuid.uuid4())
        value = {'task_id': "task", "status": "status"}
        with mock.patch("rally.cmd.main.db") as mock_db:
            mock_db.task_get = mock.MagicMock(return_value=value)
            self.task.status(test_uuid)
            mock_db.task_get.assert_called_once_with(test_uuid)

    def test_list(self):
        db_response = [
            {'uuid': 'a', 'created_at': 'b', 'status': 'c', 'failed': True}
        ]
        with mock.patch("rally.cmd.main.db") as mock_db:
            mock_db.task_list = mock.MagicMock(return_value=db_response)
            self.task.list()
            mock_db.task_list.assert_called_once_with()

    def test_delete(self):
        task_uuid = str(uuid.uuid4())
        force = False
        with mock.patch("rally.cmd.main.api") as mock_api:
            mock_api.delete_task = mock.Mock()
            self.task.delete(task_uuid, force)
            mock_api.delete_task.assert_called_once_with(task_uuid,
                                                         force=force)

    def test_plot(self):
        test_uuid = str(uuid.uuid4())
        mock_plot = mock.Mock()
        PLOTS = {"aggregated": mock_plot}
        with mock.patch("rally.cmd.main.processing.PLOTS", new=PLOTS):
            self.task.plot("aggregated", "concurrent", test_uuid)
        mock_plot.assert_called_once_with(test_uuid, "concurrent")


class DeploymentCommandsTestCase(test.BaseTestCase):
    def setUp(self):
        super(DeploymentCommandsTestCase, self).setUp()
        self.deployment = main.DeploymentCommands()

    @mock.patch('rally.cmd.main.api.create_deploy')
    @mock.patch('rally.cmd.main.open',
                mock.mock_open(read_data='{"some": "json"}'),
                create=True)
    def test_create(self, mock_create):
        self.deployment.create('path_to_config.json', 'fake_deploy')
        mock_create.assert_called_once_with({'some': 'json'}, 'fake_deploy')

    @mock.patch('rally.cmd.main.api.recreate_deploy')
    def test_recreate(self, mock_recreate):
        deploy_id = str(uuid.uuid4())
        self.deployment.recreate(deploy_id)
        mock_recreate.assert_called_once_with(deploy_id)

    @mock.patch('rally.cmd.main.api.destroy_deploy')
    def test_destroy(self, mock_destroy):
        deploy_id = str(uuid.uuid4())
        self.deployment.destroy(deploy_id)
        mock_destroy.assert_called_once_with(deploy_id)
