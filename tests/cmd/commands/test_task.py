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

from rally.cmd.commands import task
from rally import exceptions
from rally.openstack.common import test


class TaskCommandsTestCase(test.BaseTestCase):

    def setUp(self):
        super(TaskCommandsTestCase, self).setUp()
        self.task = task.TaskCommands()

    @mock.patch('rally.cmd.commands.task.TaskCommands.detailed')
    @mock.patch('rally.orchestrator.api.create_task',
                return_value=dict(uuid='fc1a9bbe-1ead-4740-92b5-0feecf421634',
                                  created_at='2014-01-14 09:14:45.395822',
                                  status='init',
                                  failed=False))
    @mock.patch('rally.cmd.commands.task.api.start_task')
    @mock.patch('rally.cmd.commands.task.open',
                mock.mock_open(read_data='{"some": "json"}'),
                create=True)
    def test_start(self, mock_api, mock_create_task,
                   mock_task_detailed):
        deploy_id = str(uuid.uuid4())
        self.task.start('path_to_config.json', deploy_id)
        mock_api.assert_called_once_with(deploy_id, {u'some': u'json'},
                                         task=mock_create_task.return_value)

    @mock.patch('rally.cmd.commands.task.envutils._default_deployment_id')
    def test_start_no_deploy_id(self, mock_default):
        mock_default.side_effect = exceptions.InvalidArgumentsException
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.task.start, 'path_to_config.json', None)

    def test_abort(self):
        test_uuid = str(uuid.uuid4())
        with mock.patch("rally.cmd.commands.task.api") as mock_api:
            mock_api.abort_task = mock.MagicMock()
            self.task.abort(test_uuid)
            task.api.abort_task.assert_called_once_with(test_uuid)

    def test_status(self):
        test_uuid = str(uuid.uuid4())
        value = {'task_id': "task", "status": "status"}
        with mock.patch("rally.cmd.commands.task.db") as mock_db:
            mock_db.task_get = mock.MagicMock(return_value=value)
            self.task.status(test_uuid)
            mock_db.task_get.assert_called_once_with(test_uuid)

    @mock.patch('rally.cmd.commands.task.db')
    def test_detailed(self, mock_db):
        test_uuid = str(uuid.uuid4())
        value = {'task_id': "task",
                 "status": "status",
                 "results": [],
                 "failed": False
                 }
        mock_db.task_get_detailed = mock.MagicMock(return_value=value)
        self.task.detailed(test_uuid)
        mock_db.task_get_detailed.assert_called_once_with(test_uuid)

    @mock.patch('rally.cmd.commands.task.db')
    def test_detailed_wrong_id(self, mock_db):
        test_uuid = str(uuid.uuid4())
        mock_db.task_get_detailed = mock.MagicMock(return_value=None)
        self.task.detailed(test_uuid)
        mock_db.task_get_detailed.assert_called_once_with(test_uuid)

    @mock.patch('rally.cmd.commands.task.db')
    def test_results(self, mock_db):
        test_uuid = str(uuid.uuid4())
        value = [
            {'key': 'key', 'data': {'raw': 'raw'}}
        ]
        mock_db.task_result_get_all_by_uuid.return_value = value
        self.task.results(test_uuid)
        mock_db.task_result_get_all_by_uuid.assert_called_once_with(test_uuid)

    def test_list(self):
        db_response = [
            {'uuid': 'a', 'created_at': 'b', 'status': 'c', 'failed': True}
        ]
        with mock.patch("rally.cmd.commands.task.db") as mock_db:
            mock_db.task_list = mock.MagicMock(return_value=db_response)
            self.task.list()
            mock_db.task_list.assert_called_once_with()

    def test_delete(self):
        task_uuid = str(uuid.uuid4())
        force = False
        with mock.patch("rally.cmd.commands.task.api") as mock_api:
            mock_api.delete_task = mock.Mock()
            self.task.delete(task_uuid, force)
            mock_api.delete_task.assert_called_once_with(task_uuid,
                                                         force=force)

    def test_plot(self):
        test_uuid = str(uuid.uuid4())
        mock_plot = mock.Mock()
        PLOTS = {"aggregated": mock_plot}
        with mock.patch("rally.cmd.commands.task.processing.PLOTS", new=PLOTS):
            self.task.plot("aggregated", "concurrent", test_uuid)
        mock_plot.assert_called_once_with(test_uuid, "concurrent")

    def test_percentile(self):
        l = range(1, 101)
        result = task.percentile(l, 0.1)
        self.assertTrue(result == 10.9)
