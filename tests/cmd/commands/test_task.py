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

from rally.cmd.commands import task
from rally import exceptions
from tests import test


class TaskCommandsTestCase(test.TestCase):

    def setUp(self):
        super(TaskCommandsTestCase, self).setUp()
        self.task = task.TaskCommands()

    @mock.patch('rally.cmd.commands.task.TaskCommands.detailed')
    @mock.patch('rally.orchestrator.api.create_task')
    @mock.patch('rally.cmd.commands.task.api.start_task')
    @mock.patch('rally.cmd.commands.task.open',
                mock.mock_open(read_data='{"some": "json"}'),
                create=True)
    def test_start(self, mock_api, mock_create_task,
                   mock_task_detailed):
        mock_create_task.return_value = (
            dict(uuid='fc1a9bbe-1ead-4740-92b5-0feecf421634',
                 created_at='2014-01-14 09:14:45.395822',
                 status='init', failed=False, tag=None))
        deploy_id = 'e0617de9-77d1-4875-9b49-9d5789e29f20'
        self.task.start('path_to_config.json', deploy_id)
        mock_api.assert_called_once_with(deploy_id, {u'some': u'json'},
                                         task=mock_create_task.return_value)

    @mock.patch('rally.cmd.commands.task.envutils.get_global')
    def test_start_no_deploy_id(self, mock_default):
        mock_default.side_effect = exceptions.InvalidArgumentsException
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.task.start, 'path_to_config.json', None)

    @mock.patch('rally.cmd.commands.task.TaskCommands.detailed')
    @mock.patch('rally.orchestrator.api.create_task')
    @mock.patch('rally.cmd.commands.task.api')
    @mock.patch('rally.cmd.commands.task.open',
                mock.mock_open(read_data='{"some": "json"}'),
                create=True)
    def test_start_kb_interuupt(self, mock_api, mock_create_task,
                                mock_task_detailed):
        mock_create_task.return_value = (
            dict(uuid='fc1a9bbe-1ead-4740-92b5-0feecf421634',
                 created_at='2014-01-14 09:14:45.395822',
                 status='init', failed=False, tag=None))
        mock_api.start_task.side_effect = KeyboardInterrupt
        deploy_id = 'f586dcd7-8473-4c2e-a4d4-22be26371c10'
        self.assertRaises(KeyboardInterrupt, self.task.start,
                          'path_to_config.json', deploy_id)
        mock_api.abort_task.assert_called_once_with(
            mock_api.create_task.return_value['uuid'])

    @mock.patch("rally.cmd.commands.task.api")
    def test_abort(self, mock_api):
        test_uuid = '17860c43-2274-498d-8669-448eff7b073f'
        mock_api.abort_task = mock.MagicMock()
        self.task.abort(test_uuid)
        task.api.abort_task.assert_called_once_with(test_uuid)

    @mock.patch('rally.cmd.commands.task.envutils.get_global')
    def test_abort_no_task_id(self, mock_default):
        mock_default.side_effect = exceptions.InvalidArgumentsException
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.task.abort, None)

    def test_status(self):
        test_uuid = 'a3e7cefb-bec2-4802-89f6-410cc31f71af'
        value = {'task_id': "task", "status": "status"}
        with mock.patch("rally.cmd.commands.task.db") as mock_db:
            mock_db.task_get = mock.MagicMock(return_value=value)
            self.task.status(test_uuid)
            mock_db.task_get.assert_called_once_with(test_uuid)

    @mock.patch('rally.cmd.commands.task.envutils.get_global')
    def test_status_no_task_id(self, mock_default):
        mock_default.side_effect = exceptions.InvalidArgumentsException
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.task.status, None)

    @mock.patch('rally.cmd.commands.task.db')
    def test_detailed(self, mock_db):
        test_uuid = 'c0d874d4-7195-4fd5-8688-abe82bfad36f'
        value = {
            "id": "task",
            "uuid": test_uuid,
            "status": "status",
            "results": [
                {
                    "key": {
                        "name": "fake_name",
                        "pos": "fake_pos",
                        "kw": "fake_kw"
                    },
                    "data": {
                        "scenario_duration": 1.0,
                        "raw": []
                    }
                }
            ],
            "failed": False
        }
        mock_db.task_get_detailed = mock.MagicMock(return_value=value)
        self.task.detailed(test_uuid)
        mock_db.task_get_detailed.assert_called_once_with(test_uuid)

    @mock.patch('rally.cmd.commands.task.envutils.get_global')
    def test_detailed_no_task_id(self, mock_default):
        mock_default.side_effect = exceptions.InvalidArgumentsException
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.task.detailed, None)

    @mock.patch('rally.cmd.commands.task.db')
    def test_detailed_wrong_id(self, mock_db):
        test_uuid = 'eb290c30-38d8-4c8f-bbcc-fc8f74b004ae'
        mock_db.task_get_detailed = mock.MagicMock(return_value=None)
        self.task.detailed(test_uuid)
        mock_db.task_get_detailed.assert_called_once_with(test_uuid)

    @mock.patch('rally.cmd.commands.task.db')
    def test_results(self, mock_db):
        test_uuid = 'aa808c14-69cc-4faf-a906-97e05f5aebbd'
        value = [
            {'key': 'key', 'data': {'raw': 'raw'}}
        ]
        mock_db.task_result_get_all_by_uuid.return_value = value
        self.task.results(test_uuid)
        mock_db.task_result_get_all_by_uuid.assert_called_once_with(test_uuid)

    @mock.patch('rally.cmd.commands.task.db')
    def test_invalid_results(self, mock_db):
        test_uuid = 'd1f58069-d221-4577-b6ba-5c635027765a'
        mock_db.task_result_get_all_by_uuid.return_value = []
        return_value = self.task.results(test_uuid)
        mock_db.task_result_get_all_by_uuid.assert_called_once_with(test_uuid)
        self.assertEqual(1, return_value)

    @mock.patch('rally.cmd.commands.task.common_cliutils.print_list')
    @mock.patch('rally.cmd.commands.task.envutils.get_global')
    @mock.patch("rally.cmd.commands.task.db")
    def test_list(self, mock_db, mock_default, mock_print_list):
        mock_default.side_effect = exceptions.InvalidArgumentsException
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.task.results, None)

        db_response = [
                {'uuid': 'a',
                 'created_at': 'b',
                 'status': 'c',
                 'failed': True,
                 'tag': 'd'}
        ]
        mock_db.task_list = mock.MagicMock(return_value=db_response)
        self.task.list()
        mock_db.task_list.assert_called_once_with()

        headers = ['uuid', 'created_at', 'status', 'failed', 'tag']
        mock_print_list.assert_called_once_with(db_response, headers,
                                                sortby_index=headers.index(
                                                    'created_at'))

    def test_delete(self):
        task_uuid = '8dcb9c5e-d60b-4022-8975-b5987c7833f7'
        force = False
        with mock.patch("rally.cmd.commands.task.api") as mock_api:
            mock_api.delete_task = mock.Mock()
            self.task.delete(task_uuid, force=force)
            mock_api.delete_task.assert_called_once_with(task_uuid,
                                                         force=force)

    @mock.patch("rally.cmd.commands.task.api")
    def test_delete_multiple_uuid(self, mock_api):
        task_uuids = ['4bf35b06-5916-484f-9547-12dce94902b7',
                      '52cad69d-d3e4-47e1-b445-dec9c5858fe8',
                      '6a3cb11c-ac75-41e7-8ae7-935732bfb48f',
                      '018af931-0e5a-40d5-9d6f-b13f4a3a09fc',
                      '1a4d88c9-fb68-4ff6-a246-f9122aec79b0']
        force = False
        self.task.delete(task_uuids, force=force)
        self.assertTrue(mock_api.delete_task.call_count == len(task_uuids))
        expected_calls = [mock.call(task_uuid, force=force) for task_uuid
                          in task_uuids]
        self.assertTrue(mock_api.delete_task.mock_calls == expected_calls)

    @mock.patch('rally.cmd.commands.task.common_cliutils.print_list')
    @mock.patch("rally.cmd.commands.task.base_sla")
    @mock.patch("rally.cmd.commands.task.db")
    def test_sla_check(self, mock_db, mock_sla, mock_print_list):
        fake_rows = [
                {'success': True},
                {'success': False},
        ]
        mock_db.task_get_detailed.return_value = 'fake_task'
        mock_sla.SLA.check_all.return_value = fake_rows
        retval = self.task.sla_check(task_id='fake_task_id')
        self.assertEqual(1, retval)
        mock_sla.SLA.check_all.assert_called_once_with('fake_task')
