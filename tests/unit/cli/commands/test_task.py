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

import os
import tempfile
from unittest import mock

from rally import consts
from rally import exceptions
from rally.cli.commands import task
from rally.common import db
from rally.common import objects
from rally.env import env_mgr
from tests.unit.cli import test


class TaskCommandsTestCase(test.CLITestCase):

    def _create_env(self, name="MyDeployment"):
        db.env_create(name=name, status=env_mgr.STATUS.READY, description="",
                      extras={}, config={}, spec={}, platforms=[])
        return db.env_get(name)

    def _create_task(self, env=None, tags=None, **attrs):
        env = env or self._create_env()
        return objects.Task(env_uuid=env["uuid"], tags=tags or [], **attrs)

    def _write(self, content, suffix=".json"):
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "w") as f:
            f.write(content)
        self.addCleanup(os.remove, path)
        return path

    def _make_task(self, status=None, data=None):
        return {
            "uuid": "task-uuid",
            "status": status or consts.TaskStatus.FINISHED,
            "pass_sla": True,
            "subtasks": [{"title": "subtask", "description": "",
                          "workloads": [{
                              "full_duration": 1, "load_duration": 2,
                              "created_at": "2017-09-27T07:22:55",
                              "name": "Foo.bar", "description": "descr",
                              "position": 2, "pass_sla": True,
                              "args": {"key1": "value1"},
                              "runner_type": "rruunneerr",
                              "runner": {"arg1": "args2"},
                              "hooks": [],
                              "sla": {"failure_rate": {"max": 0}},
                              "sla_results": {"sla": [{"success": True}]},
                              "contexts": {"users": {}},
                              "statistics": {"durations": {
                                  "atomics": [],
                                  "total": {
                                      "name": "total", "display_name": "total",
                                      "count_per_iteration": 1, "children": [],
                                      "data": {"min": 1, "median": 2,
                                               "90%ile": 1.5, "95%ile": 1.6,
                                               "max": 3, "avg": 1.4,
                                               "success": 3,
                                               "iteration_count": 3}}}},
                              "data": data or []}]}]}

    def _rich_detailed_value(self):
        stats = {"min": 1, "median": 2, "90%ile": 1.5, "95%ile": 1.6,
                 "max": 3, "avg": 1.4, "success": 3, "iteration_count": 3}
        action = [{"name": "foo", "started_at": 0.0, "finished_at": 0.6,
                   "children": []}]
        return {
            "id": "task", "uuid": "task-uuid", "pass_sla": False,
            "status": consts.TaskStatus.FINISHED,
            "subtasks": [{"title": "s", "description": "", "workloads": [{
                "name": "fake_name", "position": "0", "args": {},
                "contexts": {}, "sla": {}, "runner": {}, "runner_type": "c",
                "hooks": [], "pass_sla": False, "load_duration": 3.2,
                "full_duration": 3.5, "total_iteration_count": 3,
                "statistics": {"durations": {
                    "atomics": [{
                        "name": "foo", "display_name": "foo (x2)",
                        "count_per_iteration": 2, "data": stats,
                        "children": [{
                            "name": "inner", "display_name": "inner",
                            "count_per_iteration": 1, "children": [],
                            "data": stats}]}],
                    "total": {"name": "total", "display_name": "total",
                              "count_per_iteration": 1, "children": [],
                              "data": stats}}},
                "data": [
                    {"duration": 0.9, "idle_duration": 0.1,
                     "output": {"additive": [], "complete": []},
                     "atomic_actions": action, "error": []},
                    {"duration": 0.7, "idle_duration": 0.5,
                     "output": {"additive": [
                         {"data": [("foo", 0.6), ("bar", 0.7)],
                          "title": "Scenario output", "description": "",
                          "chart_plugin": "StackedArea"}], "complete": []},
                     "atomic_actions": action,
                     "error": ["type", "message", "traceback"]},
                    {"duration": 0.5, "idle_duration": 0.5,
                     "atomic_actions": action, "error": []}]}]}]}

    @mock.patch("rally.api._Task.validate")
    def test__load_and_validate_task(self, mock_validate):
        # the rendered task (jinja args merged) is echoed by the command;
        # --task-args overrides --task-args-file
        env = self._create_env()
        task_file = self._write("{'ab': {{test}}}")
        args_file = self._write("{'test': 1}")
        for extra, expected in (
            (["--task-args-file", args_file], "'ab': 1"),
            (["--task-args", "{'test': 2}"], "'ab': 2"),
            (["--task-args", "{'test': 2}",
              "--task-args-file", args_file], "'ab': 2"),
            (["--task-args", "test=2",
              "--task-args-file", args_file], "'ab': 2"),
        ):
            with self.subTest(extra=extra):
                result = self.invoke(["task", "validate", task_file,
                                      "--deployment", env["uuid"], *extra])
                self.assertEqual(0, result.exit_code, result.output)
                self.assertIn(expected, result.output)

    def test__load_task_wrong_task_args_file(self):
        env = self._create_env()
        task_file = self._write("{}")
        result = self.invoke(["task", "validate", task_file,
                              "--deployment", env["uuid"],
                              "--task-args-file", "/no/such/args"])
        self.assertEqual(task.FailedToLoadTask.error_code, result.exit_code)
        self.assertIn("Invalid --task-args-file passed", result.output)

    def test__load_task_wrong_input_task_args(self):
        env = self._create_env()
        task_file = self._write("{}")
        for raw_args in ("{'test': {}", "foo"):
            with self.subTest(raw_args=raw_args):
                result = self.invoke(["task", "validate", task_file,
                                      "--deployment", env["uuid"],
                                      "--task-args", raw_args])
                self.assertEqual(task.FailedToLoadTask.error_code,
                                 result.exit_code)
                self.assertIn("Invalid --task-args passed", result.output)

    def test__load_task_wrong_task_args_file_format(self):
        env = self._create_env()
        task_file = self._write("{}")
        bad_args = self._write("{'a': {}")
        result = self.invoke(["task", "validate", task_file, "--deployment",
                              env["uuid"], "--task-args-file", bad_args])
        self.assertEqual(task.FailedToLoadTask.error_code, result.exit_code)
        self.assertIn("has to be YAML or JSON", result.output)

    def test__load_task_task_render_raise_exc(self):
        env = self._create_env()
        task_file = self._write("{'test': {{t}}}")
        result = self.invoke(["task", "validate", task_file,
                              "--deployment", env["uuid"]])
        self.assertEqual(task.FailedToLoadTask.error_code, result.exit_code)
        self.assertIn("Failed to render task template", result.output)

    def test__load_task_task_not_in_yaml(self):
        env = self._create_env()
        # renders fine (no jinja) but is not valid YAML/JSON
        task_file = self._write("{'test': {}")
        result = self.invoke(["task", "validate", task_file,
                              "--deployment", env["uuid"]])
        self.assertEqual(task.FailedToLoadTask.error_code, result.exit_code)
        self.assertIn("Wrong format of rendered input task", result.output)

    def test_load_task_including_other_template(self):
        import rally
        other = os.path.join(os.path.dirname(rally.__file__), os.pardir,
                             "samples/tasks/scenarios/dummy/dummy.json")
        including = self._write(
            "{%% include \"%s\" %%}" % os.path.basename(other))
        # move the including file next to the referenced one
        target = os.path.join(os.path.dirname(other), os.path.basename(
            including))
        with open(including) as f:
            content = f.read()
        with open(target, "w") as f:
            f.write(content)
        self.addCleanup(os.remove, target)

        from rally import api as rally_api
        api = rally_api.API(skip_db_check=True)
        expect = task._load_and_validate_task(api, other)
        actual = task._load_and_validate_task(api, target)
        self.assertEqual(expect, actual)

    def test__load_and_validate_file_failed(self):
        env = self._create_env()
        result = self.invoke(["task", "validate", "/no/such/task",
                              "--deployment", env["uuid"]])
        self.assertEqual(task.FailedToLoadTask.error_code, result.exit_code)
        self.assertIn("Error reading /no/such/task", result.output)

    @mock.patch("rally.api._Task.start")
    @mock.patch("rally.api._Task.get")
    @mock.patch("rally.api._Task.create")
    def test_start(self, mock_create, mock_get, mock_start):
        env = self._create_env()
        task_file = self._write('{"a": 1}')
        mock_create.return_value = {"uuid": "new-uuid", "tags": []}
        mock_get.return_value = {"uuid": "new-uuid", "status": "finished",
                                 "pass_sla": True, "subtasks": []}

        result = self.invoke(["task", "start", task_file,
                              "--deployment", env["uuid"]])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("started", result.output)
        mock_create.assert_called_once_with(deployment=env["uuid"], tags=None)
        mock_start.assert_called_once_with(
            deployment=env["uuid"], config={"a": 1}, task="new-uuid",
            abort_on_sla_failure=False)

    @mock.patch("rally.api._Task.create")
    def test_start_on_unfinished_deployment(self, mock_create):
        env = self._create_env()
        task_file = self._write('{"a": 1}')
        mock_create.side_effect = exceptions.DeploymentNotFinishedStatus(
            name="xxx", uuid=env["uuid"],
            status=consts.DeployStatus.DEPLOY_INIT)

        result = self.invoke(["task", "start", task_file,
                              "--deployment", env["uuid"], "--tag", "some"])

        self.assertEqual(1, result.exit_code, result.output)
        self.assertIn("unfinished deployment", result.output)

    @mock.patch("rally.api._Task.start")
    @mock.patch("rally.api._Task.get")
    @mock.patch("rally.api._Task.create")
    def test_start_with_task_args(self, mock_create, mock_get, mock_start):
        env = self._create_env()
        task_file = self._write("{'a': {{v}}}")
        args_file = self._write("{'v': 5}")
        mock_create.return_value = {"uuid": "new-uuid", "tags": ["t"]}
        mock_get.return_value = {"uuid": "new-uuid", "status": "finished",
                                 "pass_sla": True, "subtasks": []}

        result = self.invoke(["task", "start", task_file,
                              "--deployment", env["uuid"],
                              "--task-args-file", args_file, "--tag", "t"])

        self.assertEqual(0, result.exit_code, result.output)
        mock_create.assert_called_once_with(deployment=env["uuid"], tags=["t"])
        mock_start.assert_called_once_with(
            deployment=env["uuid"], config={"a": 5}, task="new-uuid",
            abort_on_sla_failure=False)

    @mock.patch("rally.api._Task.create")
    def test_start_invalid_task(self, mock_create):
        env = self._create_env()
        task_file = self._write('{"a": 1}')
        mock_create.side_effect = exceptions.InvalidTaskException("foo")

        result = self.invoke(["task", "start", task_file,
                              "--deployment", env["uuid"]])

        self.assertEqual(exceptions.InvalidTaskException.error_code,
                         result.exit_code)

    @mock.patch("rally.api._Task.start")
    @mock.patch("rally.api._Task.get")
    @mock.patch("rally.api._Task.create")
    def test_start_sla_failure_exits_2(self, mock_create, mock_get,
                                       mock_start):
        env = self._create_env()
        task_file = self._write('{"a": 1}')
        mock_create.return_value = {"uuid": "new-uuid", "tags": []}
        mock_get.return_value = {"uuid": "new-uuid", "pass_sla": False,
                                 "status": "finished", "subtasks": []}

        result = self.invoke(["task", "start", task_file, "--deployment",
                              env["uuid"], "--no-use"])

        self.assertEqual(2, result.exit_code, result.output)

    @mock.patch("rally.cli.commands.task._start_task", return_value=0)
    @mock.patch("rally.api._Task.get")
    def test_restart(self, mock_get, mock__start_task):
        for scenario in (None, "scenario_name", "none_name"):
            with self.subTest(scenario=scenario):
                mock_get.return_value = {
                    "uuid": "task-uuid", "status": "finished",
                    "title": "fake_task", "description": "d", "tags": [],
                    "subtasks": [{"title": "s", "description": "",
                                  "workloads": [{
                                      "name": "scenario_name", "args": {},
                                      "contexts": {},
                                      "runner_type": "constant",
                                      "runner": {"times": 1}, "hooks": [],
                                      "sla": {}}]}]}
                args = ["task", "restart", "--deployment", "dep",
                        "--uuid", "task-uuid"]
                if scenario:
                    args += ["--scenario", scenario]
                result = self.invoke(args)
                if scenario == "none_name":
                    self.assertEqual(1, result.exit_code, result.output)
                    self.assertIn("Not Found matched scenario",
                                  result.output)
                else:
                    self.assertEqual(0, result.exit_code, result.output)
            mock_get.reset_mock()

    @mock.patch("rally.api._Task.get")
    def test_restart_by_crashed_task(self, mock_get):
        mock_get.return_value = {
            "uuid": "task-uuid", "status": "crashed", "title": "t",
            "description": "d", "tags": [], "subtasks": [],
            "validation_result": {"trace": {}, "etype": "E", "msg": "m"}}

        result = self.invoke(["task", "restart", "--deployment", "dep",
                              "--uuid", "task-uuid"])

        self.assertEqual(1, result.exit_code, result.output)
        self.assertIn("Unable to restart task", result.output)

    @mock.patch("rally.cli.commands.task._start_task", return_value=2)
    @mock.patch("rally.api._Task.get")
    def test_restart_propagates_rc(self, mock_get, mock__start_task):
        mock_get.return_value = {
            "uuid": "task-uuid", "status": "finished", "title": "t",
            "description": "d", "tags": [], "subtasks": [{
                "title": "s", "description": "", "workloads": [{
                    "name": "sc", "args": {}, "contexts": {},
                    "runner_type": "c", "runner": {}, "hooks": [],
                    "sla": {}}]}]}

        result = self.invoke(["task", "restart", "--deployment", "dep",
                              "--uuid", "task-uuid"])

        self.assertEqual(2, result.exit_code, result.output)

    @mock.patch("rally.api._Task.get")
    def test_restart_by_crashed_task_debug(self, mock_get):
        mock_get.return_value = {
            "uuid": "task-uuid", "status": "crashed", "title": "t",
            "description": "d", "tags": [], "subtasks": [],
            "validation_result": {"trace": "traceback: x", "etype": "E",
                                  "msg": "m"}}

        with mock.patch("rally.cli.commands.task.logging.is_debug",
                        return_value=True):
            result = self.invoke(["task", "restart", "--deployment", "dep",
                                  "--uuid", "task-uuid"])

        self.assertEqual(1, result.exit_code, result.output)

    @mock.patch("rally.api._Task.abort")
    def test_abort(self, mock_abort):
        result = self.invoke(["task", "abort", "the-uuid", "--soft"])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("successfully stopped", result.output)
        mock_abort.assert_called_once_with(
            task_uuid="the-uuid", soft=True, wait=True)

    @mock.patch("rally.api._Task.abort")
    def test_abort_hard(self, mock_abort):
        result = self.invoke(["task", "abort", "the-uuid"])

        self.assertEqual(0, result.exit_code, result.output)
        mock_abort.assert_called_once_with(
            task_uuid="the-uuid", soft=False, wait=True)

    def test_status(self):
        task_obj = self._create_task()

        result = self.invoke(["task", "status", task_obj["uuid"]])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("%s: init" % task_obj["uuid"], result.output)

    @mock.patch("rally.api._Task.get")
    def test_detailed(self, mock_get):
        for iterations_data in (False, True):
            with self.subTest(iterations_data=iterations_data):
                mock_get.return_value = self._make_task(data=[
                    {"duration": 0.9, "idle_duration": 0.1,
                     "output": {"additive": [], "complete": []},
                     "atomic_actions": [], "error": []}])
                args = ["task", "detailed", "task-uuid"]
                if iterations_data:
                    args.append("--iterations-data")
                result = self.invoke(args)
                self.assertEqual(0, result.exit_code, result.output)
                self.assertIn("Foo.bar", result.output)

    @mock.patch("rally.api._Task.get")
    def test_detailed_task_failed(self, mock_get):
        value = {
            "id": "task", "uuid": "task-uuid",
            "status": consts.TaskStatus.CRASHED, "results": [],
            "validation_result": {"etype": "error_type",
                                  "msg": "error_message",
                                  "trace": "error_traceback"}}
        for debug in (True, False):
            with self.subTest(debug=debug):
                mock_get.return_value = value
                with mock.patch("rally.cli.commands.task.logging.is_debug",
                                return_value=debug):
                    result = self.invoke(["task", "detailed", "task-uuid"])
                self.assertEqual(0, result.exit_code, result.output)
                self.assertIn("crashed", result.output)
                self.assertIn("error_traceback" if debug else "error_message",
                              result.output)

    @mock.patch("rally.api._Task.get")
    def test_detailed_task_status_not_in_finished_abort(self, mock_get):
        mock_get.return_value = {"id": "task", "uuid": "task-uuid",
                                 "status": consts.TaskStatus.INIT,
                                 "results": []}

        result = self.invoke(["task", "detailed", "task-uuid"])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("marked as 'init'", result.output)

    def test_detailed_wrong_id(self):
        result = self.invoke(["task", "detailed", "no-such-uuid"])

        self.assertNotEqual(0, result.exit_code)
        self.assertIn("no-such-uuid", result.output)

    @mock.patch("rally.api._Task.get")
    def test_detailed_full_output(self, mock_get):
        # rich data drives the atomics/output/error rendering branches
        for iterations_data, extra in (
            (False, []),
            (True, ["--filter-by", "scenario=fake_name",
                    "--filter-by", "sla-failures"]),
        ):
            with self.subTest(iterations_data=iterations_data):
                mock_get.return_value = self._rich_detailed_value()
                args = ["task", "detailed", "task-uuid", *extra]
                if iterations_data:
                    args.append("--iterations-data")
                result = self.invoke(args)
                self.assertEqual(0, result.exit_code, result.output)
                self.assertIn("fake_name", result.output)

    @mock.patch("rally.api._Task.export")
    def test_results(self, mock_export):
        mock_export.return_value = {"print": "the-json-body"}

        result = self.invoke(["task", "results", "task-uuid"])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("the-json-body", result.output)

    @mock.patch("rally.api._Task.export")
    def test_results_no_data(self, mock_export):
        mock_export.side_effect = exceptions.RallyException(
            "Task status is crashed.")

        result = self.invoke(["task", "results", "task-uuid"])

        self.assertEqual(1, result.exit_code, result.output)
        self.assertIn("Task status is crashed", result.output)

    @mock.patch("rally.cli.commands.task._export")
    def test_trends(self, mock__export):
        for extra, otype in (([], "trends-html"),
                             (["--html-static"], "trends-html-static")):
            with self.subTest(extra=extra):
                mock__export.reset_mock()
                result = self.invoke(["task", "trends", "uuid",
                                      "--out", "output.html", *extra])
                self.assertEqual(0, result.exit_code, result.output)
                mock__export.assert_called_once_with(
                    mock.ANY, tasks=["uuid"], output_type=otype,
                    output_dest="output.html", open_it=False)

    def test_trends_no_tasks_given(self):
        result = self.invoke(["task", "trends", "--out", "output.html"])

        self.assertEqual(1, result.exit_code, result.output)
        self.assertIn("At least one task must be specified", result.output)

    @mock.patch("rally.cli.commands.task._export")
    def test_report(self, mock__export):
        for extra, otype in (([], "html"),
                             (["--json"], "json"),
                             (["--html-static"], "html-static")):
            with self.subTest(extra=extra):
                mock__export.reset_mock()
                result = self.invoke(["task", "report", "uuid",
                                      "--out", "out", *extra])
                self.assertEqual(0, result.exit_code, result.output)
                mock__export.assert_called_once_with(
                    mock.ANY, tasks=["uuid"], output_type=otype,
                    output_dest="out", open_it=False, deployment=None)

    @mock.patch("rally.api._Task.export")
    @mock.patch("rally.api._Task.list")
    def test_report_by_deployment(self, mock_list, mock_export):
        mock_list.return_value = [{"uuid": "u1"}]
        mock_export.return_value = {"print": "the report body"}

        # --deployment lists the tasks itself; the positional is still required
        result = self.invoke(["task", "report", "ignored", "--deployment",
                              "dep", "--out", "out"])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("the report body", result.output)
        mock_list.assert_called_once_with(deployment="dep", uuids_only=True)
        mock_export.assert_called_once_with(
            tasks=["u1"], output_type="html", output_dest="out")

    @mock.patch("rally.cli.commands.task.webbrowser.open_new_tab")
    @mock.patch("rally.api._Task.export")
    def test_report_writes_files(self, mock_export, mock_open_new_tab):
        out = self._write("", suffix=".html")
        mock_export.return_value = {"files": {out: "<html/>"},
                                    "open": "file://%s" % out}

        result = self.invoke(["task", "report", "uuid", "--out", out,
                              "--open"])

        self.assertEqual(0, result.exit_code, result.output)
        with open(out) as f:
            self.assertEqual("<html/>", f.read())
        mock_open_new_tab.assert_called_once_with("file://%s" % out)

    @mock.patch("rally.api._Task.export")
    @mock.patch("rally.cli.commands.task.task_results_loader.load")
    def test_report_file_input(self, mock_load, mock_export):
        report_file = self._write("[]")
        mock_load.return_value = ["loaded"]
        mock_export.return_value = {"print": "body"}

        result = self.invoke(["task", "report", report_file, "--out", "o"])

        self.assertEqual(0, result.exit_code, result.output)
        mock_load.assert_called_once_with(report_file)
        mock_export.assert_called_once_with(
            tasks=["loaded"], output_type="html", output_dest="o")

    def test_list(self):
        env = self._create_env()
        task_obj = self._create_task(env=env, tags=["d"])

        result = self.invoke(["task", "list", "--deployment", env["uuid"]])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn(task_obj["uuid"], result.output)
        self.assertIn("MyDeployment", result.output)

    def test_list_uuids_only(self):
        env = self._create_env()
        task_obj = self._create_task(env=env)

        result = self.invoke(["task", "list", "--deployment", env["uuid"],
                              "--uuids-only"])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertEqual("%s\n" % task_obj["uuid"], result.stdout)

    def test_list_wrong_status(self):
        result = self.invoke(["task", "list", "--deployment", "fake",
                              "--status", "wrong non existing status"])

        self.assertEqual(1, result.exit_code, result.output)
        self.assertIn("Invalid task status", result.output)

    def test_list_no_results(self):
        env = self._create_env()

        result = self.invoke(["task", "list", "--deployment", env["uuid"]])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("There are no tasks", result.output)

    def test_list_filters(self):
        env = self._create_env()
        self._create_task(env=env)  # a task with no tags
        with self.subTest("no-tag task lists with an empty tag cell"):
            result = self.invoke(["task", "list", "--deployment",
                                  env["uuid"]])
            self.assertEqual(0, result.exit_code, result.output)
        with self.subTest("valid status filter with no matches"):
            result = self.invoke(["task", "list", "--deployment",
                                  env["uuid"], "--status", "finished"])
            self.assertEqual(0, result.exit_code, result.output)
            self.assertIn("no tasks in 'finished' status", result.output)
        with self.subTest("all deployments + tag filter"):
            result = self.invoke(["task", "list", "--deployment",
                                  env["uuid"], "--all-deployments",
                                  "--tag", "x"])
            self.assertEqual(0, result.exit_code, result.output)

    def test_list_uuids_only_empty(self):
        env = self._create_env()

        result = self.invoke(["task", "list", "--deployment", env["uuid"],
                              "--uuids-only"])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertEqual("", result.stdout.strip())

    def test_delete(self):
        env = self._create_env()
        one = self._create_task(env=env)
        two = self._create_task(env=env)

        result = self.invoke(["task", "delete", one["uuid"], two["uuid"],
                              "--force"])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Successfully deleted task", result.output)
        self.assertEqual([], db.task_list())

    @mock.patch("rally.api._Task.delete",
                side_effect=exceptions.DBConflict("busy"))
    def test_delete_conflict(self, mock_delete):
        result = self.invoke(["task", "delete", "some-uuid"])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Use '--force'", result.output)

    @mock.patch("rally.api._Task.get")
    def test_sla_check(self, mock_get):
        task_obj = self._make_task()
        task_obj["subtasks"][0]["workloads"][0]["sla_results"]["sla"] = [
            {"benchmark": "Foo.bar", "criterion": "max",
             "pos": 0, "success": False, "detail": "boom"}]
        mock_get.return_value = task_obj

        result = self.invoke(["task", "sla-check", "task-uuid"])
        self.assertEqual(1, result.exit_code, result.output)

        task_obj["subtasks"][0]["workloads"][0]["sla_results"]["sla"] = [
            {"benchmark": "Foo.bar", "criterion": "max",
             "pos": 0, "success": True, "detail": ""}]
        result = self.invoke(["task", "sla-check", "task-uuid", "--json"])
        self.assertEqual(0, result.exit_code, result.output)

    @mock.patch("rally.api._Task.get")
    def test_sla_check_no_data(self, mock_get):
        mock_get.return_value = {"subtasks": [{"workloads": [{
            "name": "n", "position": 0, "sla_results": {"sla": []}}]}]}

        result = self.invoke(["task", "sla-check", "task-uuid"])

        self.assertEqual(2, result.exit_code, result.output)

    @mock.patch("rally.api._Task.validate")
    def test_validate(self, mock_validate):
        env = self._create_env()
        task_file = self._write('{"some": "json"}')

        result = self.invoke(["task", "validate", task_file,
                              "--deployment", env["uuid"]])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Input Task is valid", result.output)
        mock_validate.assert_called_once_with(
            deployment=env["uuid"], config={"some": "json"})

    def test_validate_failed_to_load_task(self):
        env = self._create_env()
        result = self.invoke(["task", "validate", "/no/such/task",
                              "--deployment", env["uuid"]])

        self.assertEqual(task.FailedToLoadTask.error_code, result.exit_code)

    @mock.patch("rally.api._Task.validate")
    def test_validate_invalid(self, mock_validate):
        env = self._create_env()
        task_file = self._write('{"some": "json"}')
        mock_validate.side_effect = exceptions.InvalidTaskException("foo")

        result = self.invoke(["task", "validate", task_file,
                              "--deployment", env["uuid"]])

        self.assertEqual(exceptions.InvalidTaskException.error_code,
                         result.exit_code)

    def test_use(self):
        task_obj = self._create_task()

        result = self.invoke(["task", "use", task_obj["uuid"]])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Using task: %s" % task_obj["uuid"], result.output)

    def test_use_not_found(self):
        result = self.invoke(["task", "use", "no-such-uuid"])

        self.assertNotEqual(0, result.exit_code)

    @mock.patch("rally.api._Task.export")
    def test_export(self, mock_export):
        mock_export.return_value = {"print": "content"}

        result = self.invoke(["task", "export", "uuid", "--type", "json"])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("content", result.output)
        mock_export.assert_called_once_with(
            tasks=["uuid"], output_type="json", output_dest=None)

    @mock.patch("rally.api._Task.get")
    def test_show_task_errors_no_trace(self, mock_get):
        for etype, emsg, etrace in (
            ("no_trace_type", "no_trace_error_message", None),
            ("test_error_type", "test_error_message", "test\ntraceback"),
        ):
            with self.subTest(etype=etype):
                error_data = [etype, emsg]
                if etrace:
                    error_data.append(etrace)
                task_obj = self._make_task(data=[
                    {"duration": 0.9, "idle_duration": 0.1,
                     "output": {"additive": [], "complete": []},
                     "atomic_actions": [], "error": error_data}])
                mock_get.return_value = task_obj
                result = self.invoke(["task", "detailed", "task-uuid"])
                self.assertEqual(0, result.exit_code, result.output)
                self.assertIn(etrace or "No traceback available.",
                              result.output)

    @mock.patch("rally.api._Task.import_results")
    @mock.patch("rally.cli.task_results_loader.load")
    def test_import_results(self, mock_load, mock_import_results):
        env = self._create_env()
        results_file = self._write("[]")
        mock_load.return_value = ["results"]
        mock_import_results.return_value = {"uuid": "new-uuid"}

        result = self.invoke(["task", "import", "--file", results_file,
                              "--deployment", env["uuid"], "--tag", "tag"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Task UUID: new-uuid", result.output)
        mock_import_results.assert_called_once_with(
            deployment=env["uuid"], task_results="results", tags=["tag"])

        result = self.invoke(["task", "import", "--file", "/no/such/file",
                              "--deployment", env["uuid"]])
        self.assertEqual(1, result.exit_code, result.output)
        self.assertIn("Invalid file name", result.output)
