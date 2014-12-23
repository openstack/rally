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
from tests.unit import fakes
from tests.unit import test


class TaskCommandsTestCase(test.TestCase):

    def setUp(self):
        super(TaskCommandsTestCase, self).setUp()
        self.task = task.TaskCommands()

    @mock.patch('rally.cmd.commands.task.TaskCommands.detailed')
    @mock.patch('rally.api.create_task')
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
        deployment_id = 'e0617de9-77d1-4875-9b49-9d5789e29f20'
        self.task.start('path_to_config.json', deployment_id)
        mock_api.assert_called_once_with(deployment_id, {u'some': u'json'},
                                         task=mock_create_task.return_value)

    @mock.patch('rally.cmd.commands.task.envutils.get_global')
    def test_start_no_deployment_id(self, mock_default):
        mock_default.side_effect = exceptions.InvalidArgumentsException
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.task.start, 'path_to_config.json', None)

    @mock.patch('rally.cmd.commands.task.TaskCommands.detailed')
    @mock.patch('rally.api.create_task')
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
        deployment_id = 'f586dcd7-8473-4c2e-a4d4-22be26371c10'
        self.assertRaises(KeyboardInterrupt, self.task.start,
                          'path_to_config.json', deployment_id)
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
                        "load_duration": 1.0,
                        "raw": []
                    }
                }
            ],
            "failed": False
        }
        mock_db.task_get_detailed = mock.MagicMock(return_value=value)
        self.task.detailed(test_uuid)
        mock_db.task_get_detailed.assert_called_once_with(test_uuid)

    @mock.patch("rally.cmd.commands.task.envutils.get_global")
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

    @mock.patch("json.dumps")
    @mock.patch("rally.cmd.commands.task.objects.Task.get")
    def test_results(self, mock_get, mock_json):
        task_id = "foo_task_id"
        data = [
            {"key": "foo_key", "data": {"raw": "foo_raw", "sla": [],
                                        "load_duration": "lo_duration",
                                        "full_duration": "fu_duration"}}
        ]
        result = map(lambda x: {"key": x["key"],
                                "result": x["data"]["raw"],
                                "load_duration": x["data"]["load_duration"],
                                "full_duration": x["data"]["full_duration"],
                                "sla": x["data"]["sla"]}, data)
        mock_results = mock.Mock(return_value=data)
        mock_get.return_value = mock.Mock(get_results=mock_results)

        self.task.results(task_id)
        mock_json.assert_called_once_with(result, sort_keys=True, indent=4)
        mock_get.assert_called_once_with(task_id)

    @mock.patch("rally.cmd.commands.task.objects.Task.get")
    def test_invalid_results(self, mock_get):
        task_id = "foo_task_id"
        data = []
        mock_results = mock.Mock(return_value=data)
        mock_get.return_value = mock.Mock(get_results=mock_results)

        result = self.task.results(task_id)
        mock_get.assert_called_once_with(task_id)
        self.assertEqual(1, result)

    @mock.patch("rally.cmd.commands.task.jsonschema.validate",
                return_value=None)
    @mock.patch("rally.cmd.commands.task.os.path.realpath",
                side_effect=lambda p: "realpath_%s" % p)
    @mock.patch("rally.cmd.commands.task.open", create=True)
    @mock.patch("rally.cmd.commands.task.plot")
    @mock.patch("rally.cmd.commands.task.webbrowser")
    @mock.patch("rally.cmd.commands.task.objects.Task.get")
    def test_report_one_uuid(self, mock_get, mock_web, mock_plot, mock_open,
                             mock_os, mock_validate):
        task_id = "eb290c30-38d8-4c8f-bbcc-fc8f74b004ae"
        data = [
            {"key": {"name": "test", "pos": 0},
             "data": {"raw": "foo_raw", "sla": "foo_sla",
                      "load_duration": 0.1,
                      "full_duration": 1.2}},
            {"key": {"name": "test", "pos": 0},
             "data": {"raw": "bar_raw", "sla": "bar_sla",
                      "load_duration": 2.1,
                      "full_duration": 2.2}}]

        results = map(lambda x: {"key": x["key"],
                                 "result": x["data"]["raw"],
                                 "sla": x["data"]["sla"],
                                 "load_duration": x["data"]["load_duration"],
                                 "full_duration": x["data"]["full_duration"]},
                      data)
        mock_results = mock.Mock(return_value=data)
        mock_get.return_value = mock.Mock(get_results=mock_results)
        mock_plot.plot.return_value = "html_report"
        mock_write = mock.Mock()
        mock_open.return_value.__enter__.return_value = (
            mock.Mock(write=mock_write))

        def reset_mocks():
            for m in mock_get, mock_web, mock_plot, mock_open:
                m.reset_mock()
        self.task.report(tasks=task_id, out="/tmp/%s.html" % task_id)
        mock_open.assert_called_once_with("/tmp/%s.html" % task_id, "w+")
        mock_plot.plot.assert_called_once_with(results)

        mock_write.assert_called_once_with("html_report")
        mock_get.assert_called_once_with(task_id)

        reset_mocks()
        self.task.report(task_id, out="spam.html", open_it=True)
        mock_web.open_new_tab.assert_called_once_with(
            "file://realpath_spam.html")

    @mock.patch("rally.cmd.commands.task.jsonschema.validate",
                return_value=None)
    @mock.patch("rally.cmd.commands.task.os.path.realpath",
                side_effect=lambda p: "realpath_%s" % p)
    @mock.patch("rally.cmd.commands.task.open", create=True)
    @mock.patch("rally.cmd.commands.task.plot")
    @mock.patch("rally.cmd.commands.task.webbrowser")
    @mock.patch("rally.cmd.commands.task.objects.Task.get")
    def test_report_bunch_uuids(self, mock_get, mock_web, mock_plot, mock_open,
                                mock_os, mock_validate):
        tasks = ["eb290c30-38d8-4c8f-bbcc-fc8f74b004ae",
                 "eb290c30-38d8-4c8f-bbcc-fc8f74b004af"]
        data = [
            {"key": {"name": "test", "pos": 0},
             "data": {"raw": "foo_raw", "sla": "foo_sla",
                      "load_duration": 0.1,
                      "full_duration": 1.2}},
            {"key": {"name": "test", "pos": 0},
             "data": {"raw": "bar_raw", "sla": "bar_sla",
                      "load_duration": 2.1,
                      "full_duration": 2.2}}]

        results = list()
        for task_uuid in tasks:
            results.extend(map(lambda x: {"key": x["key"],
                                          "result": x["data"]["raw"],
                                          "sla": x["data"]["sla"],
                                          "load_duration": x[
                                            "data"]["load_duration"],
                                          "full_duration": x[
                                            "data"]["full_duration"]},
                               data))

        mock_results = mock.Mock(return_value=data)
        mock_get.return_value = mock.Mock(get_results=mock_results)
        mock_plot.plot.return_value = "html_report"
        mock_write = mock.Mock()
        mock_open.return_value.__enter__.return_value = (
            mock.Mock(write=mock_write))

        def reset_mocks():
            for m in mock_get, mock_web, mock_plot, mock_open:
                m.reset_mock()
        self.task.report(tasks=tasks, out="/tmp/1_test.html")
        mock_open.assert_called_once_with("/tmp/1_test.html", "w+")
        mock_plot.plot.assert_called_once_with(results)

        mock_write.assert_called_once_with("html_report")
        expected_get_calls = [mock.call(task) for task in tasks]
        mock_get.assert_has_calls(expected_get_calls, any_order=True)

    @mock.patch("rally.cmd.commands.task.json.load")
    @mock.patch("rally.cmd.commands.task.os.path.exists", return_value=True)
    @mock.patch("rally.cmd.commands.task.jsonschema.validate",
                return_value=None)
    @mock.patch("rally.cmd.commands.task.os.path.realpath",
                side_effect=lambda p: "realpath_%s" % p)
    @mock.patch("rally.cmd.commands.task.open", create=True)
    @mock.patch("rally.cmd.commands.task.plot")
    def test_report_one_file(self, mock_plot, mock_open, mock_os,
                             mock_validate, mock_path_exists, mock_json_load):

        task_file = "/tmp/some_file.json"
        data = [
            {"key": {"name": "test", "pos": 0},
             "data": {"raw": "foo_raw", "sla": "foo_sla",
                      "load_duration": 0.1,
                      "full_duration": 1.2}},
            {"key": {"name": "test", "pos": 1},
             "data": {"raw": "bar_raw", "sla": "bar_sla",
                      "load_duration": 2.1,
                      "full_duration": 2.2}}]

        results = map(lambda x: {"key": x["key"],
                                 "result": x["data"]["raw"],
                                 "sla": x["data"]["sla"],
                                 "load_duration": x["data"]["load_duration"],
                                 "full_duration": x["data"]["full_duration"]},
                      data)

        mock_plot.plot.return_value = "html_report"
        mock_write = mock.Mock()
        mock_read = mock.MagicMock(return_value=results)
        mock_json_load.return_value = results
        mock_open.return_value.__enter__.return_value = (
            mock.Mock(write=mock_write, read=mock_read))

        def reset_mocks():
            for m in mock_plot, mock_open, mock_json_load, mock_validate:
                m.reset_mock()
        self.task.report(tasks=task_file, out="/tmp/1_test.html")
        expected_open_calls = [mock.call(task_file, "r"),
                               mock.call("/tmp/1_test.html", "w+")]
        mock_open.assert_has_calls(expected_open_calls, any_order=True)
        mock_plot.plot.assert_called_once_with(results)

        mock_write.assert_called_once_with("html_report")

    @mock.patch("rally.cmd.commands.task.os.path.exists", return_value=True)
    @mock.patch("rally.cmd.commands.task.json.load")
    @mock.patch("rally.cmd.commands.task.open", create=True)
    def test_report_exceptions(self, mock_open, mock_json_load,
                               mock_path_exists):

        results = [
            {"key": {"name": "test", "pos": 0},
             "data": {"raw": "foo_raw", "sla": "foo_sla",
                      "load_duration": 0.1,
                      "full_duration": 1.2}}]

        mock_write = mock.Mock()
        mock_read = mock.MagicMock(return_value=results)
        mock_json_load.return_value = results
        mock_open.return_value.__enter__.return_value = (
            mock.Mock(write=mock_write, read=mock_read))

        ret = self.task.report(tasks="/tmp/task.json",
                               out="/tmp/tmp.hsml")

        self.assertEqual(ret, 1)
        for m in mock_open, mock_json_load:
            m.reset_mock()
        mock_path_exists.return_value = False
        ret = self.task.report(tasks="/tmp/task.json",
                               out="/tmp/tmp.hsml")
        self.assertEqual(ret, 1)

    @mock.patch('rally.cmd.commands.task.common_cliutils.print_list')
    @mock.patch('rally.cmd.commands.task.envutils.get_global',
                return_value='123456789')
    @mock.patch("rally.cmd.commands.task.objects.Task.list",
                return_value=[fakes.FakeTask(uuid="a",
                                             created_at="b",
                                             status="c",
                                             failed=True,
                                             tag="d",
                                             deployment_name="some_name")])
    def test_list(self, mock_objects_list, mock_default, mock_print_list):

        self.task.list()
        mock_objects_list.assert_called_once_with(
            deployment=mock_default.return_value)

        headers = ["uuid", "deployment_name", "created_at", "status",
                   "failed", "tag"]
        mock_print_list.assert_called_once_with(
            mock_objects_list.return_value, headers,
            sortby_index=headers.index('created_at'))

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

    @mock.patch("rally.cmd.commands.task.common_cliutils.print_list")
    @mock.patch("rally.cmd.commands.task.db")
    def _test_sla_check(self, mock_db, mock_print_list):
        data = [{"key": {"name": "fake_name",
                         "pos": "fake_pos",
                         "kw": "fake_kw"},
                 "data": {"scenario_duration": 42.0,
                          "raw": [],
                          "sla": [{"benchmark": "KeystoneBasic.create_user",
                                   "criterion": "max_seconds_per_iteration",
                                   "pos": 0,
                                   "success": False,
                                   "detail": "Max foo, actually bar"}]}}]
        mock_db.task_result_get_all_by_uuid.return_value = data
        result = self.task.sla_check(task_id="fake_task_id")
        self.assertEqual(1, result)

    @mock.patch("rally.cmd.commands.task.open",
                mock.mock_open(read_data='{"some": "json"}'),
                create=True)
    @mock.patch("rally.api.task_validate")
    def test_verify(self, mock_validate):
        self.task.validate("path_to_config.json", "fake_id")
        mock_validate.assert_called_once_with("fake_id", {"some": "json"})
