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

import copy
import datetime as dt
import json
import os.path

import ddt
import mock
import yaml

from rally import api
from rally.cli.commands import task
from rally import consts
from rally import exceptions
from tests.unit import fakes
from tests.unit import test


@ddt.ddt
class TaskCommandsTestCase(test.TestCase):

    def setUp(self):
        super(TaskCommandsTestCase, self).setUp()
        self.task = task.TaskCommands()
        self.fake_api = fakes.FakeAPI()

        with mock.patch("rally.api.API._check_db_revision"):
            self.real_api = api.API()

    @mock.patch("rally.cli.commands.task.open", create=True)
    def test__load_task(self, mock_open):
        input_task = "{'ab': {{test}}}"
        input_args = "{'test': 2}"

        # NOTE(boris-42): Such order of files is because we are reading
        #                 file with args before file with template.
        mock_open.side_effect = [
            mock.mock_open(read_data="{'test': 1}").return_value,
            mock.mock_open(read_data=input_task).return_value
        ]
        task_conf = self.task._load_task(
            self.real_api, "in_task", task_args_file="in_args_path")
        self.assertEqual({"ab": 1}, task_conf)

        mock_open.side_effect = [
            mock.mock_open(read_data=input_task).return_value
        ]
        task_conf = self.task._load_task(
            self.real_api, "in_task", task_args=input_args)
        self.assertEqual(task_conf, {"ab": 2})

        mock_open.side_effect = [
            mock.mock_open(read_data="{'test': 1}").return_value,
            mock.mock_open(read_data=input_task).return_value

        ]
        task_conf = self.task._load_task(
            self.real_api, "in_task", task_args=input_args,
            task_args_file="any_file")
        self.assertEqual(task_conf, {"ab": 2})

    @mock.patch("rally.cli.commands.task.open", create=True)
    def test__load_task_wrong_task_args_file(self, mock_open):
        mock_open.side_effect = [
            mock.mock_open(read_data="{'test': {}").return_value
        ]
        self.assertRaises(task.FailedToLoadTask,
                          self.task._load_task,
                          self.fake_api, "in_task",
                          task_args_file="in_args_path")

    @mock.patch("rally.cli.commands.task.open", create=True)
    def test__load_task_wrong_task_args_file_exception(self, mock_open):
        mock_open.side_effect = IOError
        self.assertRaises(IOError, self.task._load_task, self.fake_api,
                          "in_task", task_args_file="in_args_path")

    def test__load_task_wrong_input_task_args(self):
        self.assertRaises(task.FailedToLoadTask,
                          self.task._load_task, self.real_api, "in_task",
                          "{'test': {}")
        self.assertRaises(task.FailedToLoadTask,
                          self.task._load_task, self.real_api, "in_task", "[]")

    @mock.patch("rally.cli.commands.task.open", create=True)
    def test__load_task_task_render_raise_exc(self, mock_open):
        mock_open.side_effect = [
            mock.mock_open(read_data="{'test': {{t}}}").return_value
        ]
        self.assertRaises(task.FailedToLoadTask,
                          self.task._load_task, self.real_api, "in_task")

    @mock.patch("rally.cli.commands.task.open", create=True)
    def test__load_task_task_not_in_yaml(self, mock_open):
        mock_open.side_effect = [
            mock.mock_open(read_data="{'test': {}").return_value
        ]
        self.assertRaises(task.FailedToLoadTask,
                          self.task._load_task, self.fake_api, "in_task")

    def test_load_task_including_other_template(self):
        other_template_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "..", "samples/tasks/scenarios/nova/boot.json")
        input_task = "{%% include \"%s\" %%}" % os.path.basename(
            other_template_path)
        expect = self.task._load_task(self.real_api, other_template_path)

        with mock.patch("rally.cli.commands.task.open",
                        create=True) as mock_open:
            mock_open.side_effect = [
                mock.mock_open(read_data=input_task).return_value
            ]
            input_task_file = os.path.join(
                os.path.dirname(other_template_path), "input_task.json")
            actual = self.task._load_task(self.real_api, input_task_file)
        self.assertEqual(expect, actual)

    @mock.patch("rally.cli.commands.task.os.path.isfile", return_value=True)
    @mock.patch("rally.cli.commands.task.TaskCommands._load_task",
                return_value={"uuid": "some_uuid"})
    def test__load_and_validate_task(self, mock__load_task,
                                     mock_os_path_isfile):
        deployment = "some_deployment_uuid"
        self.fake_api.task.validate.return_value = fakes.FakeTask()
        self.task._load_and_validate_task(self.fake_api, "some_task",
                                          "task_args", "task_args_file",
                                          deployment)
        mock__load_task.assert_called_once_with(
            self.fake_api, "some_task", "task_args", "task_args_file")
        self.fake_api.task.validate.assert_called_once_with(
            deployment, mock__load_task.return_value, None)

    def test__load_and_validate_file(self):
        deployment = "some_deployment_uuid"
        self.assertRaises(IOError, self.task._load_and_validate_task,
                          self.fake_api, "some_task", "task_args",
                          "task_args_file", deployment)

    @mock.patch("rally.cli.commands.task.version")
    @mock.patch("rally.cli.commands.task.os.path.isfile", return_value=True)
    @mock.patch("rally.cli.commands.task.TaskCommands.use")
    @mock.patch("rally.cli.commands.task.TaskCommands.detailed")
    @mock.patch("rally.cli.commands.task.TaskCommands._load_task",
                return_value={"some": "json"})
    def test_start(self, mock__load_task, mock_detailed, mock_use,
                   mock_os_path_isfile, mock_version):
        deployment_id = "e0617de9-77d1-4875-9b49-9d5789e29f20"
        task_path = "path_to_config.json"
        self.fake_api.task.create.return_value = fakes.FakeTask(
            uuid="some_new_uuid", tag="tag")
        self.fake_api.task.validate.return_value = fakes.FakeTask(
            some="json", uuid="some_uuid", temporary=True)

        self.task.start(self.fake_api, task_path, deployment_id, do_use=True)
        mock_version.version_string.assert_called_once_with()
        self.fake_api.task.create.assert_called_once_with(
            deployment_id, None)
        self.fake_api.task.start.assert_called_once_with(
            deployment_id, mock__load_task.return_value,
            task=self.fake_api.task.validate.return_value,
            abort_on_sla_failure=False)
        mock__load_task.assert_called_once_with(
            self.fake_api, task_path, None, None)
        mock_use.assert_called_once_with(self.fake_api, "some_new_uuid")
        mock_detailed.assert_called_once_with(self.fake_api,
                                              task_id="some_new_uuid")

    @mock.patch("rally.cli.commands.task.os.path.isfile", return_value=True)
    @mock.patch("rally.cli.commands.task.TaskCommands.detailed")
    @mock.patch("rally.cli.commands.task.TaskCommands._load_task",
                return_value="some_config")
    def test_start_with_task_args(self, mock__load_task, mock_detailed,
                                  mock_os_path_isfile):
        self.fake_api.task.create.return_value = fakes.FakeTask(
            uuid="new_uuid", tag="some_tag")
        self.fake_api.task.validate.return_value = fakes.FakeTask(
            uuid="some_id")

        task_path = "path_to_config.json"
        task_args = "task_args"
        task_args_file = "task_args_file"
        self.task.start(self.fake_api, task_path, deployment="any",
                        task_args=task_args, task_args_file=task_args_file,
                        tag="some_tag")
        mock__load_task.assert_called_once_with(
            self.fake_api, task_path, task_args, task_args_file)
        self.fake_api.task.validate.assert_called_once_with(
            "any", mock__load_task.return_value, {})
        self.fake_api.task.start.assert_called_once_with(
            "any", mock__load_task.return_value,
            task=self.fake_api.task.create.return_value,
            abort_on_sla_failure=False)
        mock_detailed.assert_called_once_with(
            self.fake_api,
            task_id=self.fake_api.task.create.return_value["uuid"])
        self.fake_api.task.create.assert_called_once_with("any", "some_tag")

    @mock.patch("rally.cli.commands.task.envutils.get_global")
    def test_start_no_deployment_id(self, mock_get_global):
        mock_get_global.side_effect = exceptions.InvalidArgumentsException
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.task.start, "path_to_config.json", None)

    @mock.patch("rally.cli.commands.task.os.path.isfile", return_value=True)
    @mock.patch("rally.cli.commands.task.TaskCommands._load_task",
                return_value={"some": "json"})
    def test_start_invalid_task(self, mock__load_task, mock_os_path_isfile):
        self.fake_api.task.create.return_value = fakes.FakeTask(
            temporary=False, tag="tag", uuid="uuid")
        exc = exceptions.InvalidTaskException
        self.fake_api.task.start.side_effect = exc
        result = self.task.start(self.fake_api, "task_path", "deployment",
                                 tag="tag")
        self.assertEqual(1, result)

        self.fake_api.task.create.assert_called_once_with("deployment", "tag")

        self.fake_api.task.start.assert_called_once_with(
            "deployment", mock__load_task.return_value,
            task=self.fake_api.task.create.return_value,
            abort_on_sla_failure=False)

    def test_abort(self):
        test_uuid = "17860c43-2274-498d-8669-448eff7b073f"
        self.task.abort(self.fake_api, test_uuid)
        self.fake_api.task.abort.assert_called_once_with(
            test_uuid, False, async=False)

    @mock.patch("rally.cli.commands.task.envutils.get_global")
    def test_abort_no_task_id(self, mock_get_global):
        mock_get_global.side_effect = exceptions.InvalidArgumentsException
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.task.abort, self.fake_api, None)

    def test_status(self):
        test_uuid = "a3e7cefb-bec2-4802-89f6-410cc31f71af"
        value = {"task_id": "task", "status": "status"}
        self.fake_api.task.get.return_value = value
        self.task.status(self.fake_api, test_uuid)
        self.fake_api.task.get.assert_called_once_with(test_uuid)

    @mock.patch("rally.cli.commands.task.envutils.get_global")
    def test_status_no_task_id(self, mock_get_global):
        mock_get_global.side_effect = exceptions.InvalidArgumentsException
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.task.status, None)

    def test_detailed(self):
        test_uuid = "c0d874d4-7195-4fd5-8688-abe82bfad36f"
        self.fake_api.task.get_detailed.return_value = {
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
                    "info": {
                        "load_duration": 3.2,
                        "full_duration": 3.5,
                        "iterations_count": 4,
                        "atomic": {"foo": {}, "bar": {}}},
                    "iterations": [
                        {"duration": 0.9,
                         "idle_duration": 0.1,
                         "output": {"additive": [], "complete": []},
                         "atomic_actions": {"foo": 0.6, "bar": 0.7},
                         "error": ["type", "message", "traceback"]
                         },
                        {"duration": 1.2,
                         "idle_duration": 0.3,
                         "output": {"additive": [], "complete": []},
                            "atomic_actions": {"foo": 0.6, "bar": 0.7},
                            "error": ["type", "message", "traceback"]
                         },
                        {"duration": 0.7,
                         "idle_duration": 0.5,
                         "scenario_output": {
                             "data": {"foo": 0.6, "bar": 0.7},
                             "errors": "some"
                         },
                         "atomic_actions": {"foo": 0.6, "bar": 0.7},
                         "error": ["type", "message", "traceback"]
                         },
                        {"duration": 0.5,
                         "idle_duration": 0.5,
                         "output": {"additive": [], "complete": []},
                         "atomic_actions": {"foo": 0.6, "bar": 0.7},
                         "error": ["type", "message", "traceback"]
                         }
                    ]
                }
            ]
        }
        self.task.detailed(self.fake_api, test_uuid)
        self.fake_api.task.get_detailed.assert_called_once_with(
            test_uuid, extended_results=True)
        self.task.detailed(self.fake_api, test_uuid, iterations_data=True)

    @mock.patch("rally.cli.commands.task.sys.stdout")
    @mock.patch("rally.cli.commands.task.logging")
    @ddt.data({"debug": True},
              {"debug": False})
    @ddt.unpack
    def test_detailed_task_failed(self, mock_logging, mock_stdout, debug):
        test_uuid = "test_task_id"
        value = {
            "id": "task",
            "uuid": test_uuid,
            "status": consts.TaskStatus.FAILED,
            "results": [],
            "verification_log": json.dumps({"etype": "error_type",
                                            "msg": "error_message",
                                            "trace": "error_traceback"})
        }
        self.fake_api.task.get_detailed.return_value = value

        mock_logging.is_debug.return_value = debug
        self.task.detailed(self.fake_api, test_uuid)
        verification = yaml.safe_load(value["verification_log"])
        if debug:
            expected_calls = [mock.call("Task test_task_id: failed"),
                              mock.call("%s" % verification["trace"])]
            mock_stdout.write.assert_has_calls(expected_calls, any_order=True)
        else:
            expected_calls = [mock.call("Task test_task_id: failed"),
                              mock.call("%s" % verification["etype"]),
                              mock.call("%s" % verification["msg"]),
                              mock.call("\nFor more details run:\nrally "
                                        "-d task detailed %s" % test_uuid)]
            mock_stdout.write.assert_has_calls(expected_calls, any_order=True)

    @mock.patch("rally.cli.commands.task.sys.stdout")
    def test_detailed_task_status_not_in_finished_abort(self, mock_stdout):
        test_uuid = "test_task_id"
        value = {
            "id": "task",
            "uuid": test_uuid,
            "status": consts.TaskStatus.INIT,
            "results": []
        }
        self.fake_api.task.get_detailed.return_value = value
        self.task.detailed(self.fake_api, test_uuid)
        expected_calls = [mock.call("Task test_task_id: init"),
                          mock.call("\nThe task test_task_id marked as "
                                    "'init'. Results available when it "
                                    "is 'finished'.")]
        mock_stdout.write.assert_has_calls(expected_calls, any_order=True)

    @mock.patch("rally.cli.commands.task.envutils.get_global")
    def test_detailed_no_task_id(self, mock_get_global):
        mock_get_global.side_effect = exceptions.InvalidArgumentsException
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.task.detailed, None)

    def test_detailed_wrong_id(self):
        test_uuid = "eb290c30-38d8-4c8f-bbcc-fc8f74b004ae"
        self.fake_api.task.get_detailed.return_value = None
        self.task.detailed(self.fake_api, test_uuid)
        self.fake_api.task.get_detailed.assert_called_once_with(
            test_uuid, extended_results=True)

    @mock.patch("json.dumps")
    def test_results(self, mock_json_dumps):
        task_id = "foo_task_id"
        data = [
            {"key": "foo_key", "data": {"raw": "foo_raw", "sla": [],
                                        "hooks": [],
                                        "load_duration": 1.0,
                                        "full_duration": 2.0}}
        ]
        result = map(lambda x: {"key": x["key"],
                                "result": x["data"]["raw"],
                                "load_duration": x["data"]["load_duration"],
                                "full_duration": x["data"]["full_duration"],
                                "hooks": x["data"]["hooks"],
                                "sla": x["data"]["sla"]}, data)
        fake_task = fakes.FakeTask({"status": consts.TaskStatus.FINISHED})
        fake_task.get_results = mock.Mock(return_value=data)
        self.fake_api.task.get.return_value = fake_task

        self.task.results(self.fake_api, task_id)
        self.assertEqual(1, mock_json_dumps.call_count)
        self.assertEqual(1, len(mock_json_dumps.call_args[0]))
        self.assertSequenceEqual(result, mock_json_dumps.call_args[0][0])
        self.assertEqual({"sort_keys": False, "indent": 4},
                         mock_json_dumps.call_args[1])
        self.fake_api.task.get.assert_called_once_with(task_id)

    @mock.patch("rally.cli.commands.task.sys.stdout")
    def test_results_no_data(self, mock_stdout):
        task_id = "foo_task_id"
        fake_task = fakes.FakeTask({"status": consts.TaskStatus.FAILED})
        self.fake_api.task.get.return_value = fake_task

        self.assertEqual(1, self.task.results(self.fake_api, task_id))

        self.fake_api.task.get.assert_called_once_with(task_id)

        expected_out = ("Task status is %s. Results "
                        "available when it is one of %s.") % (
            consts.TaskStatus.FAILED,
            ", ".join((consts.TaskStatus.FINISHED,
                       consts.TaskStatus.ABORTED)))
        mock_stdout.write.assert_has_calls([mock.call(expected_out)])

    def _make_result(self, keys):
        return [{"key": {"name": key, "pos": 0},
                 "data": {"raw": key + "_raw",
                          "sla": key + "_sla",
                          "hooks": key + "_hooks",
                          "load_duration": 1.2,
                          "full_duration": 2.3}} for key in keys]

    @mock.patch("rally.cli.commands.task.jsonschema.validate",
                return_value=None)
    @mock.patch("rally.cli.commands.task.os.path")
    @mock.patch("rally.cli.commands.task.open", create=True)
    @mock.patch("rally.cli.commands.task.plot")
    @mock.patch("rally.cli.commands.task.webbrowser")
    def test_trends(self, mock_webbrowser, mock_plot,
                    mock_open, mock_os_path, mock_validate):
        mock_os_path.exists = lambda p: p.startswith("path_to_")
        mock_os_path.expanduser = lambda p: p + "_expanded"
        mock_os_path.realpath.side_effect = lambda p: "realpath_" + p
        results_iter = iter([self._make_result(["bar"]),
                             self._make_result(["spam"])])
        fake_task = self.fake_api.task.get.return_value
        fake_task.get_results.side_effect = results_iter
        mock_plot.trends.return_value = "rendered_trends_report"
        mock_fd = mock.mock_open(
            read_data="[\"result_1_from_file\", \"result_2_from_file\"]")
        mock_open.side_effect = mock_fd
        ret = self.task.trends(self.fake_api,
                               tasks=["ab123456-38d8-4c8f-bbcc-fc8f74b004ae",
                                      "cd654321-38d8-4c8f-bbcc-fc8f74b004ae",
                                      "path_to_file"],
                               out="output.html", out_format="html")
        expected = [
            {"load_duration": 1.2, "full_duration": 2.3, "sla": "bar_sla",
             "hooks": "bar_hooks",
             "key": {"name": "bar", "pos": 0}, "result": "bar_raw"},
            {"load_duration": 1.2, "full_duration": 2.3, "sla": "spam_sla",
             "hooks": "spam_hooks",
             "key": {"name": "spam", "pos": 0}, "result": "spam_raw"},
            "result_1_from_file", "result_2_from_file"]
        mock_plot.trends.assert_called_once_with(expected)
        self.assertEqual([mock.call("path_to_file_expanded", "r"),
                          mock.call("output.html_expanded", "w+")],
                         mock_open.mock_calls)
        self.assertIsNone(ret)
        self.assertEqual([mock.call("result_1_from_file",
                                    self.fake_api.task.TASK_RESULT_SCHEMA),
                          mock.call("result_2_from_file",
                                    self.fake_api.task.TASK_RESULT_SCHEMA)],
                         mock_validate.mock_calls)
        self.assertEqual([mock.call("ab123456-38d8-4c8f-bbcc-fc8f74b004ae"),
                          mock.call().get_results(),
                          mock.call("cd654321-38d8-4c8f-bbcc-fc8f74b004ae"),
                          mock.call().get_results()],
                         self.fake_api.task.get.mock_calls)
        self.assertFalse(mock_webbrowser.open_new_tab.called)
        mock_fd.return_value.write.assert_called_once_with(
            "rendered_trends_report")

    @mock.patch("rally.cli.commands.task.jsonschema.validate",
                return_value=None)
    @mock.patch("rally.cli.commands.task.os.path")
    @mock.patch("rally.cli.commands.task.open", create=True)
    @mock.patch("rally.cli.commands.task.plot")
    @mock.patch("rally.cli.commands.task.webbrowser")
    def test_trends_single_file_and_open_webbrowser(
            self, mock_webbrowser, mock_plot, mock_open, mock_os_path,
            mock_validate):
        mock_os_path.exists.return_value = True
        mock_os_path.expanduser = lambda path: path
        mock_os_path.realpath.side_effect = lambda p: "realpath_" + p
        mock_open.side_effect = mock.mock_open(read_data="[\"result\"]")
        ret = self.task.trends(self.real_api,
                               tasks=["path_to_file"], open_it=True,
                               out="output.html", out_format="html")
        self.assertIsNone(ret)
        mock_webbrowser.open_new_tab.assert_called_once_with(
            "file://realpath_output.html")

    @mock.patch("rally.cli.commands.task.os.path")
    @mock.patch("rally.cli.commands.task.open", create=True)
    @mock.patch("rally.cli.commands.task.plot")
    def test_trends_task_id_is_not_uuid_like(self, mock_plot,
                                             mock_open, mock_os_path):
        mock_os_path.exists.return_value = False
        self.fake_api.task.get.return_value.get_results.return_value = (
            self._make_result(["foo"]))

        ret = self.task.trends(self.fake_api,
                               tasks=["ab123456-38d8-4c8f-bbcc-fc8f74b004ae"],
                               out="output.html", out_format="html")
        self.assertIsNone(ret)

        ret = self.task.trends(self.fake_api,
                               tasks=["this-is-not-uuid"],
                               out="output.html", out_format="html")
        self.assertEqual(1, ret)

    @mock.patch("rally.cli.commands.task.os.path")
    @mock.patch("rally.cli.commands.task.open", create=True)
    @mock.patch("rally.cli.commands.task.plot")
    def test_trends_wrong_results_format(self, mock_plot,
                                         mock_open, mock_os_path):
        mock_os_path.exists.return_value = True
        mock_open.side_effect = mock.mock_open(read_data="[42]")
        ret = self.task.trends(self.real_api, tasks=["path_to_file"],
                               out="output.html", out_format="html")
        self.assertEqual(1, ret)

        with mock.patch("rally.api._Task.TASK_RESULT_SCHEMA",
                        {"type": "number"}):
            ret = self.task.trends(self.real_api, tasks=["path_to_file"],
                                   out="output.html", out_format="html")
            self.assertIsNone(ret)

    def test_trends_no_tasks_given(self):
        ret = self.task.trends(self.fake_api, tasks=[],
                               out="output.html", out_format="html")
        self.assertEqual(1, ret)

    @mock.patch("rally.cli.commands.task.jsonschema.validate",
                return_value=None)
    @mock.patch("rally.cli.commands.task.os.path.realpath",
                side_effect=lambda p: "realpath_%s" % p)
    @mock.patch("rally.cli.commands.task.open",
                side_effect=mock.mock_open(), create=True)
    @mock.patch("rally.cli.commands.task.plot")
    @mock.patch("rally.cli.commands.task.webbrowser")
    def test_report_one_uuid(self, mock_webbrowser,
                             mock_plot, mock_open, mock_realpath,
                             mock_validate):
        task_id = "eb290c30-38d8-4c8f-bbcc-fc8f74b004ae"
        data = [
            {"key": {"name": "class.test", "pos": 0},
             "data": {"raw": "foo_raw", "sla": "foo_sla",
                      "hooks": "foo_hooks",
                      "load_duration": 0.1,
                      "full_duration": 1.2}},
            {"key": {"name": "class.test", "pos": 0},
             "data": {"raw": "bar_raw", "sla": "bar_sla",
                      "hooks": "bar_hooks",
                      "load_duration": 2.1,
                      "full_duration": 2.2}}]

        results = [{"key": x["key"],
                    "result": x["data"]["raw"],
                    "sla": x["data"]["sla"],
                    "hooks": x["data"]["hooks"],
                    "load_duration": x["data"]["load_duration"],
                    "full_duration": x["data"]["full_duration"]}
                   for x in data]
        mock_results = mock.Mock(return_value=data)
        self.fake_api.task.get.return_value.get_results = mock_results
        mock_plot.plot.return_value = "html_report"

        def reset_mocks():
            for m in (self.fake_api.task.get, mock_webbrowser,
                      mock_plot, mock_open):
                m.reset_mock()
        self.task.report(self.fake_api, tasks=task_id,
                         out="/tmp/%s.html" % task_id)
        mock_open.assert_called_once_with("/tmp/%s.html" % task_id, "w+")
        mock_plot.plot.assert_called_once_with(results, include_libs=False)

        mock_open.side_effect().write.assert_called_once_with("html_report")
        self.fake_api.task.get.assert_called_once_with(task_id)

        # JUnit
        reset_mocks()
        self.task.report(self.fake_api, tasks=task_id,
                         out="/tmp/%s.html" % task_id, out_format="junit")
        mock_open.assert_called_once_with("/tmp/%s.html" % task_id, "w+")
        self.assertFalse(mock_plot.plot.called)

        # HTML
        reset_mocks()
        self.task.report(self.fake_api, task_id, out="output.html",
                         open_it=True, out_format="html")
        mock_webbrowser.open_new_tab.assert_called_once_with(
            "file://realpath_output.html")
        mock_plot.plot.assert_called_once_with(results, include_libs=False)

        # HTML with embedded JS/CSS
        reset_mocks()
        self.task.report(self.fake_api, task_id, open_it=False,
                         out="output.html", out_format="html_static")
        self.assertFalse(mock_webbrowser.open_new_tab.called)
        mock_plot.plot.assert_called_once_with(results, include_libs=True)

    @mock.patch("rally.cli.commands.task.jsonschema.validate",
                return_value=None)
    @mock.patch("rally.cli.commands.task.os.path.realpath",
                side_effect=lambda p: "realpath_%s" % p)
    @mock.patch("rally.cli.commands.task.open",
                side_effect=mock.mock_open(), create=True)
    @mock.patch("rally.cli.commands.task.plot")
    @mock.patch("rally.cli.commands.task.webbrowser")
    def test_report_bunch_uuids(self, mock_webbrowser,
                                mock_plot, mock_open, mock_realpath,
                                mock_validate):
        tasks = ["eb290c30-38d8-4c8f-bbcc-fc8f74b004ae",
                 "eb290c30-38d8-4c8f-bbcc-fc8f74b004af"]
        data = [
            {"key": {"name": "test", "pos": 0},
             "data": {"raw": "foo_raw", "sla": "foo_sla",
                      "hooks": "foo_hooks",
                      "load_duration": 0.1,
                      "full_duration": 1.2}},
            {"key": {"name": "test", "pos": 0},
             "data": {"raw": "bar_raw", "sla": "bar_sla",
                      "hooks": "bar_hooks",
                      "load_duration": 2.1,
                      "full_duration": 2.2}}]

        results = []
        for task_uuid in tasks:
            results.extend(
                map(lambda x: {"key": x["key"],
                               "result": x["data"]["raw"],
                               "sla": x["data"]["sla"],
                               "hooks": x["data"]["hooks"],
                               "load_duration": x["data"]["load_duration"],
                               "full_duration": x["data"]["full_duration"]},
                    data))

        mock_results = mock.Mock(return_value=data)
        self.fake_api.task.get.return_value.get_results = mock_results
        mock_plot.plot.return_value = "html_report"

        def reset_mocks():
            for m in (self.fake_api.task.get, mock_webbrowser,
                      mock_plot, mock_open):
                m.reset_mock()
        self.task.report(self.fake_api, tasks=tasks, out="/tmp/1_test.html")
        mock_open.assert_called_once_with("/tmp/1_test.html", "w+")
        mock_plot.plot.assert_called_once_with(results, include_libs=False)

        mock_open.side_effect().write.assert_called_once_with("html_report")
        expected_get_calls = [mock.call(task) for task in tasks]
        self.fake_api.task.get.assert_has_calls(
            expected_get_calls, any_order=True)

    @mock.patch("rally.cli.commands.task.json.load")
    @mock.patch("rally.cli.commands.task.os.path.exists", return_value=True)
    @mock.patch("rally.cli.commands.task.jsonschema.validate",
                return_value=None)
    @mock.patch("rally.cli.commands.task.os.path.realpath",
                side_effect=lambda p: "realpath_%s" % p)
    @mock.patch("rally.cli.commands.task.open", create=True)
    @mock.patch("rally.cli.commands.task.plot")
    def test_report_one_file(self, mock_plot, mock_open, mock_realpath,
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

        results = [{"key": x["key"],
                    "result": x["data"]["raw"],
                    "sla": x["data"]["sla"],
                    "load_duration": x["data"]["load_duration"],
                    "full_duration": x["data"]["full_duration"]}
                   for x in data]

        mock_plot.plot.return_value = "html_report"
        mock_open.side_effect = mock.mock_open(read_data=results)

        mock_json_load.return_value = results

        def reset_mocks():
            for m in mock_plot, mock_open, mock_json_load, mock_validate:
                m.reset_mock()
        self.task.report(self.real_api, tasks=task_file,
                         out="/tmp/1_test.html")
        expected_open_calls = [mock.call(task_file, "r"),
                               mock.call("/tmp/1_test.html", "w+")]
        mock_open.assert_has_calls(expected_open_calls, any_order=True)
        mock_plot.plot.assert_called_once_with(results, include_libs=False)

        mock_open.side_effect().write.assert_called_once_with("html_report")

    @mock.patch("rally.cli.commands.task.os.path.exists", return_value=True)
    @mock.patch("rally.cli.commands.task.json.load")
    @mock.patch("rally.cli.commands.task.open", create=True)
    def test_report_exceptions(self, mock_open, mock_json_load,
                               mock_path_exists):

        results = [
            {"key": {"name": "test", "pos": 0},
             "data": {"raw": "foo_raw", "sla": "foo_sla",
                      "load_duration": 0.1,
                      "full_duration": 1.2}}]

        mock_open.side_effect = mock.mock_open(read_data=results)
        mock_json_load.return_value = results

        ret = self.task.report(self.real_api, tasks="/tmp/task.json",
                               out="/tmp/tmp.hsml")

        self.assertEqual(ret, 1)
        for m in mock_open, mock_json_load:
            m.reset_mock()
        mock_path_exists.return_value = False
        ret = self.task.report(self.real_api, tasks="/tmp/task.json",
                               out="/tmp/tmp.hsml")
        self.assertEqual(ret, 1)

    @mock.patch("rally.cli.commands.task.sys.stderr")
    @mock.patch("rally.cli.commands.task.os.path.exists", return_value=True)
    @mock.patch("rally.cli.commands.task.json.load")
    @mock.patch("rally.cli.commands.task.open", create=True)
    def test_report_invalid_format(self, mock_open, mock_json_load,
                                   mock_path_exists, mock_stderr):
        result = self.task.report(self.real_api, tasks="/tmp/task.json",
                                  out="/tmp/tmp.html",
                                  out_format="invalid")
        self.assertEqual(1, result)
        expected_out = "Invalid output format: invalid"
        mock_stderr.write.assert_has_calls([mock.call(expected_out)])

    @mock.patch("rally.cli.commands.task.cliutils.print_list")
    @mock.patch("rally.cli.commands.task.envutils.get_global",
                return_value="123456789")
    def test_list(self, mock_get_global, mock_print_list):
        self.fake_api.task.list.return_value = [
            fakes.FakeTask(uuid="a",
                           created_at=dt.datetime.now(),
                           updated_at=dt.datetime.now(),
                           status="c",
                           tag="d",
                           deployment_name="some_name")]
        self.task.list(self.fake_api, status="running")
        self.fake_api.task.list.assert_called_once_with(
            deployment=mock_get_global.return_value,
            status=consts.TaskStatus.RUNNING)

        headers = ["uuid", "deployment_name", "created_at", "duration",
                   "status", "tag"]

        mock_print_list.assert_called_once_with(
            self.fake_api.task.list.return_value, headers,
            sortby_index=headers.index("created_at"))

    @mock.patch("rally.cli.commands.task.cliutils.print_list")
    @mock.patch("rally.cli.commands.task.envutils.get_global",
                return_value="123456789")
    def test_list_uuids_only(self, mock_get_global, mock_print_list):
        self.fake_api.task.list.return_value = [
            fakes.FakeTask(uuid="a",
                           created_at=dt.datetime.now(),
                           updated_at=dt.datetime.now(),
                           status="c",
                           tag="d",
                           deployment_name="some_name")]
        self.task.list(self.fake_api, status="running", uuids_only=True)
        self.fake_api.task.list.assert_called_once_with(
            deployment=mock_get_global.return_value,
            status=consts.TaskStatus.RUNNING)
        mock_print_list.assert_called_once_with(
            self.fake_api.task.list.return_value, ["uuid"],
            print_header=False, print_border=False)

    def test_list_wrong_status(self):
        self.assertEqual(1, self.task.list(self.fake_api, deployment="fake",
                                           status="wrong non existing status"))

    def test_list_no_results(self):
        self.fake_api.task.list.return_value = []
        self.assertIsNone(self.task.list(self.fake_api, deployment="fake",
                                         all_deployments=True))
        self.fake_api.task.list.assert_called_once_with()
        self.fake_api.task.list.reset_mock()

        self.assertIsNone(self.task.list(self.fake_api, deployment="d",
                                         status=consts.TaskStatus.RUNNING))
        self.fake_api.task.list.assert_called_once_with(
            deployment="d", status=consts.TaskStatus.RUNNING)

    def test_delete(self):
        task_uuid = "8dcb9c5e-d60b-4022-8975-b5987c7833f7"
        force = False
        self.task.delete(self.fake_api, task_uuid, force=force)
        self.fake_api.task.delete.assert_called_once_with(
            task_uuid, force=force)

    def test_delete_multiple_uuid(self):
        task_uuids = ["4bf35b06-5916-484f-9547-12dce94902b7",
                      "52cad69d-d3e4-47e1-b445-dec9c5858fe8",
                      "6a3cb11c-ac75-41e7-8ae7-935732bfb48f",
                      "018af931-0e5a-40d5-9d6f-b13f4a3a09fc"]
        force = False
        self.task.delete(self.fake_api, task_uuids, force=force)
        self.assertTrue(
            self.fake_api.task.delete.call_count == len(task_uuids))
        expected_calls = [mock.call(task_uuid, force=force) for task_uuid
                          in task_uuids]
        self.assertTrue(self.fake_api.task.delete.mock_calls == expected_calls)

    @mock.patch("rally.cli.commands.task.cliutils.print_list")
    def test_sla_check(self, mock_print_list):
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

        fake_task = self.fake_api.task.get.return_value
        fake_task.get_results.return_value = copy.deepcopy(data)
        result = self.task.sla_check(self.fake_api, task_id="fake_task_id")
        self.assertEqual(1, result)
        self.fake_api.task.get.assert_called_with("fake_task_id")

        data[0]["data"]["sla"][0]["success"] = True
        fake_task.get_results.return_value = data

        result = self.task.sla_check(self.fake_api, task_id="fake_task_id",
                                     tojson=True)
        self.assertEqual(0, result)

    @mock.patch("rally.cli.commands.task.os.path.isfile", return_value=True)
    @mock.patch("rally.cli.commands.task.open",
                side_effect=mock.mock_open(read_data="{\"some\": \"json\"}"),
                create=True)
    def test_validate(self, mock_open, mock_os_path_isfile):
        self.fake_api.task.render_template = self.real_api.task.render_template
        self.task.validate(self.fake_api, "path_to_config.json", "fake_id")
        self.fake_api.task.validate.assert_called_once_with(
            "fake_id", {"some": "json"}, None)

    @mock.patch("rally.cli.commands.task.os.path.isfile", return_value=True)
    @mock.patch("rally.cli.commands.task.TaskCommands._load_task",
                side_effect=task.FailedToLoadTask)
    def test_validate_failed_to_load_task(self, mock__load_task,
                                          mock_os_path_isfile):
        args = "args"
        args_file = "args_file"

        result = self.task.validate(self.real_api,
                                    "path_to_task", "fake_deployment_id",
                                    task_args=args, task_args_file=args_file)
        self.assertEqual(1, result)
        mock__load_task.assert_called_once_with(
            self.real_api, "path_to_task", args, args_file)

    @mock.patch("rally.cli.commands.task.os.path.isfile", return_value=True)
    @mock.patch("rally.cli.commands.task.TaskCommands._load_task")
    def test_validate_invalid(self, mock__load_task, mock_os_path_isfile):
        exc = exceptions.InvalidTaskException
        self.fake_api.task.validate.side_effect = exc
        result = self.task.validate(self.fake_api,
                                    "path_to_task", "deployment")
        self.assertEqual(1, result)
        self.fake_api.task.validate.assert_called_once_with(
            "deployment", mock__load_task.return_value, None)

    @mock.patch("rally.common.fileutils._rewrite_env_file")
    def test_use(self, mock__rewrite_env_file):
        task_id = "80422553-5774-44bd-98ac-38bd8c7a0feb"
        self.task.use(self.fake_api, task_id)
        mock__rewrite_env_file.assert_called_once_with(
            os.path.expanduser("~/.rally/globals"),
            ["RALLY_TASK=%s\n" % task_id])

    def test_use_not_found(self):
        task_id = "ddc3f8ba-082a-496d-b18f-72cdf5c10a14"
        exc = exceptions.TaskNotFound(uuid=task_id)
        self.fake_api.task.get.side_effect = exc
        self.assertRaises(exceptions.TaskNotFound, self.task.use,
                          self.fake_api, task_id)

    @mock.patch("rally.task.exporter.Exporter.get")
    def test_export(self, mock_exporter_get):
        mock_client = mock.Mock()
        mock_exporter_class = mock.Mock(return_value=mock_client)
        mock_exporter_get.return_value = mock_exporter_class
        self.task.export(self.fake_api, "fake_uuid", "file:///fake_path.json")
        mock_exporter_get.assert_called_once_with("file")
        mock_client.export.assert_called_once_with("fake_uuid")

    @mock.patch("rally.task.exporter.Exporter.get")
    def test_export_exception(self, mock_exporter_get):
        mock_client = mock.Mock()
        mock_exporter_class = mock.Mock(return_value=mock_client)
        mock_exporter_get.return_value = mock_exporter_class
        mock_client.export.side_effect = IOError
        self.task.export(self.fake_api, "fake_uuid", "file:///fake_path.json")
        mock_exporter_get.assert_called_once_with("file")
        mock_client.export.assert_called_once_with("fake_uuid")

    @mock.patch("rally.cli.commands.task.sys.stdout")
    @mock.patch("rally.task.exporter.Exporter.get")
    def test_export_InvalidConnectionString(self, mock_exporter_get,
                                            mock_stdout):
        mock_exporter_class = mock.Mock(
            side_effect=exceptions.InvalidConnectionString)
        mock_exporter_get.return_value = mock_exporter_class
        self.task.export(self.fake_api, "fake_uuid", "file:///fake_path.json")
        mock_stdout.write.assert_has_calls([
            mock.call("The connection string is not valid: None. "
                      "Please check your connection string."),
            mock.call("\n")])
        mock_exporter_get.assert_called_once_with("file")

    @mock.patch("rally.cli.commands.task.plot.charts")
    @mock.patch("rally.cli.commands.task.sys.stdout")
    @ddt.data({"error_type": "test_no_trace_type",
               "error_message": "no_trace_error_message",
               "error_traceback": None,
               },
              {"error_type": "test_error_type",
               "error_message": "test_error_message",
               "error_traceback": "test\nerror\ntraceback",
               })
    @ddt.unpack
    def test_show_task_errors_no_trace(self, mock_stdout,
                                       mock_charts, error_type, error_message,
                                       error_traceback=None):
        mock_charts.MainStatsTable.columns = ["Column 1", "Column 2"]
        test_uuid = "test_task_id"
        error_data = [error_type, error_message]
        if error_traceback:
            error_data.append(error_traceback)
        self.fake_api.task.get_detailed.return_value = {
            "id": "task",
            "uuid": test_uuid,
            "status": "finished",
            "results": [{
                "key": {
                    "name": "fake_name",
                    "pos": "fake_pos",
                    "kw": "fake_kw"
                },
                "info": {
                    "stat": {"cols": ["Column 1", "Column 2"],
                             "rows": [[11, 22], [33, 44]]},
                    "load_duration": 3.2,
                    "full_duration": 3.5,
                    "iterations_count": 1,
                    "iterations_failed": 1,
                    "atomic": {"foo": {}, "bar": {}}},

                "iterations": [
                    {"duration": 0.9,
                     "idle_duration": 0.1,
                     "output": {"additive": [], "complete": []},
                     "atomic_actions": {"foo": 0.6, "bar": 0.7},
                     "error": error_data
                     },
                ]},
            ],
            "verification_log": json.dumps([error_type, error_message,
                                            error_traceback])
        }
        self.task.detailed(self.fake_api, test_uuid)
        self.fake_api.task.get_detailed.assert_called_once_with(
            test_uuid, extended_results=True)
        mock_stdout.write.assert_has_calls([
            mock.call(error_traceback or "No traceback available.")
        ], any_order=False)
