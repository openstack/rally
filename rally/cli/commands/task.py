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

""" Rally command: task """

from __future__ import print_function
import json
import os
import sys
import webbrowser

import jsonschema
from oslo_utils import uuidutils
import six
import yaml

from rally import api
from rally.cli import cliutils
from rally.cli import envutils
from rally.common import db
from rally.common import fileutils
from rally.common.i18n import _
from rally.common import junit
from rally.common import log as logging
from rally.common import objects
from rally.common import utils as rutils
from rally import consts
from rally import exceptions
from rally import plugins
from rally.task.processing import plot
from rally.task.processing import utils


class FailedToLoadTask(exceptions.RallyException):
    msg_fmt = _("Failed to load task")


class TaskCommands(object):
    """Task management.

    Set of commands that allow you to manage benchmarking tasks and results.
    """

    def _load_task(self, task_file, task_args=None, task_args_file=None):
        """Load tasks template from file and render it with passed args.

        :param task_file: Path to file with input task
        :param task_args: JSON or YAML representation of dict with args that
                          will be used to render input task with jinja2
        :param task_args_file: Path to file with JSON or YAML representation
                               of dict, that will be used to render input
                               with jinja2. If both specified task_args and
                               task_args_file they will be merged. task_args
                               has bigger priority so it will update values
                               from task_args_file.
        :returns: Str with loaded and rendered task
        """
        print(cliutils.make_header("Preparing input task"))

        def print_invalid_header(source_name, args):
            print(_("Invalid %(source)s passed: \n\n %(args)s \n")
                  % {"source": source_name, "args": args},
                  file=sys.stderr)

        def parse_task_args(src_name, args):
            try:
                kw = args and yaml.safe_load(args)
                kw = {} if kw is None else kw
            except yaml.parser.ParserError as e:
                print_invalid_header(src_name, args)
                print(_("%(source)s has to be YAML or JSON. Details:"
                        "\n\n%(err)s\n")
                      % {"source": src_name, "err": e},
                      file=sys.stderr)
                raise TypeError()

            if not isinstance(kw, dict):
                print_invalid_header(src_name, args)
                print(_("%(src)s has to be dict, actually %(src_type)s\n")
                      % {"src": src_name, "src_type": type(kw)},
                      file=sys.stderr)
                raise TypeError()
            return kw

        try:
            kw = {}
            if task_args_file:
                with open(task_args_file) as f:
                    kw.update(parse_task_args("task_args_file", f.read()))
            kw.update(parse_task_args("task_args", task_args))
        except TypeError:
            raise FailedToLoadTask()

        with open(task_file) as f:
            try:
                input_task = f.read()
                task_dir = os.path.expanduser(
                    os.path.dirname(task_file)) or "./"
                rendered_task = api.Task.render_template(input_task,
                                                         task_dir, **kw)
            except Exception as e:
                print(_("Failed to render task template:\n%(task)s\n%(err)s\n")
                      % {"task": input_task, "err": e},
                      file=sys.stderr)
                raise FailedToLoadTask()

            print(_("Input task is:\n%s\n") % rendered_task)
            try:
                parsed_task = yaml.safe_load(rendered_task)

            except Exception as e:
                print(_("Wrong format of rendered input task. It should be "
                        "YAML or JSON.\n%s") % e,
                      file=sys.stderr)
                raise FailedToLoadTask()

            print(_("Task syntax is correct :)"))
            return parsed_task

    def _load_and_validate_task(self, task, task_args, task_args_file,
                                deployment, task_instance=None):
        if not os.path.exists(task) or os.path.isdir(task):
            if task_instance:
                task_instance.set_failed(log="No such file '%s'" % task)
            raise IOError("File '%s' is not found." % task)
        input_task = self._load_task(task, task_args, task_args_file)
        api.Task.validate(deployment, input_task, task_instance)
        print(_("Task config is valid :)"))
        return input_task

    @cliutils.args("--deployment", type=str, dest="deployment",
                   required=False, help="UUID or name of the deployment")
    @cliutils.args("--task", "--filename",
                   help="Path to the file with full configuration of task")
    @cliutils.args("--task-args", dest="task_args",
                   help="Input task args (dict in json). These args are used "
                        "to render input task that is jinja2 template.")
    @cliutils.args("--task-args-file", dest="task_args_file",
                   help="Path to the file with input task args (dict in "
                        "json/yaml). These args are used to render input "
                        "task that is jinja2 template.")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    @plugins.ensure_plugins_are_loaded
    def validate(self, task, deployment=None, task_args=None,
                 task_args_file=None):
        """Validate a task configuration file.

        This will check that task configuration file has valid syntax and
        all required options of scenarios, contexts, SLA and runners are set.

        :param task: a file with yaml/json task
        :param task_args: Input task args (dict in json/yaml). These args are
                          used to render input task that is jinja2 template.
        :param task_args_file: File with input task args (dict in json/yaml).
                               These args are used to render input task that
                               is jinja2 template.
        :param deployment: UUID or name of a deployment
        """
        try:
            self._load_and_validate_task(task, task_args, task_args_file,
                                         deployment)

        except (exceptions.InvalidTaskException, FailedToLoadTask) as e:
            print(e, file=sys.stderr)
            return(1)

    @cliutils.args("--deployment", type=str, dest="deployment",
                   required=False, help="UUID or name of the deployment")
    @cliutils.args("--task", "--filename", help="Path to the input task file")
    @cliutils.args("--task-args", dest="task_args",
                   help="Input task args (dict in json). These args are used "
                        "to render input task that is jinja2 template.")
    @cliutils.args("--task-args-file", dest="task_args_file",
                   help="Path to the file with input task args (dict in "
                        "json/yaml). These args are used to render input "
                        "task that is jinja2 template.")
    @cliutils.args("--tag", help="Tag for this task")
    @cliutils.args("--no-use", action="store_false", dest="do_use",
                   help="Don't set new task as default for future operations")
    @cliutils.args("--abort-on-sla-failure", action="store_true",
                   dest="abort_on_sla_failure",
                   help="Abort the execution of a benchmark scenario when"
                        "any SLA check for it fails")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    @plugins.ensure_plugins_are_loaded
    def start(self, task, deployment=None, task_args=None, task_args_file=None,
              tag=None, do_use=False, abort_on_sla_failure=False):
        """Start benchmark task.

        :param task: a file with yaml/json task
        :param task_args: Input task args (dict in json/yaml). These args are
                          used to render input task that is jinja2 template.
        :param task_args_file: File with input task args (dict in json/yaml).
                               These args are used to render input task that
                               is jinja2 template.
        :param deployment: UUID or name of a deployment
        :param tag: optional tag for this task
        :param do_use: if True, the new task will be stored as the default one
                       for future operations
        :param abort_on_sla_failure: if True, the execution of a benchmark
                                     scenario will stop when any SLA check
                                     for it fails
        """

        task_instance = api.Task.create(deployment, tag)

        try:
            input_task = self._load_and_validate_task(
                task, task_args, task_args_file, deployment,
                task_instance=task_instance)

            print(cliutils.make_header(
                  _("Task %(tag)s %(uuid)s: started")
                  % {"uuid": task_instance["uuid"],
                     "tag": task_instance["tag"]}))
            print("Benchmarking... This can take a while...\n")
            print("To track task status use:\n")
            print("\trally task status\n\tor\n\trally task detailed\n")

            if do_use:
                self.use(task_instance["uuid"])

            api.Task.start(deployment, input_task, task=task_instance,
                           abort_on_sla_failure=abort_on_sla_failure)
            self.detailed(task_id=task_instance["uuid"])

        except (exceptions.InvalidTaskException, FailedToLoadTask) as e:
            task_instance.set_failed(log=e.format_message())
            print(e, file=sys.stderr)
            return(1)

    @cliutils.args("--uuid", type=str, dest="task_id", help="UUID of task")
    @envutils.with_default_task_id
    @cliutils.args("--soft", action="store_true",
                   help="Abort task after current scenario full execution")
    def abort(self, task_id=None, soft=False):
        """Abort started benchmarking task.

        :param task_id: Task uuid
        :param soft: if set to True, task should be aborted after execution of
                     current scenario
        """
        if soft:
            print("INFO: please be informed that soft abort wont stop "
                  "current running scenario, it will prevent to start "
                  "new ones, so if you are running task with only one "
                  "scenario - soft abort will not help at all.")

        api.Task.abort(task_id, soft, async=False)

        print("Task %s successfully stopped." % task_id)

    @cliutils.args("--uuid", type=str, dest="task_id", help="UUID of task")
    @envutils.with_default_task_id
    def status(self, task_id=None):
        """Display current status of task.

        :param task_id: Task uuid
        Returns current status of task
        """

        task = db.task_get(task_id)
        print(_("Task %(task_id)s: %(status)s")
              % {"task_id": task_id, "status": task["status"]})

    @cliutils.args("--uuid", type=str, dest="task_id",
                   help=("uuid of task, if --uuid is \"last\" results of most "
                         "recently created task will be displayed."))
    @cliutils.args("--iterations-data", dest="iterations_data",
                   action="store_true",
                   help="print detailed results for each iteration")
    @envutils.with_default_task_id
    def detailed(self, task_id=None, iterations_data=False):
        """Display results table.

        :param task_id: Task uuid
        :param iterations_data: print detailed results for each iteration
        Prints detailed information of task.
        """

        def _print_iterations_data(raw_data):
            headers = ["iteration", "full duration"]
            float_cols = ["full duration"]
            atomic_actions = []
            for row in raw_data:
                # find first non-error result to get atomic actions names
                if not row["error"] and "atomic_actions" in row:
                    atomic_actions = row["atomic_actions"].keys()
            for row in raw_data:
                if row["atomic_actions"]:
                    for (c, a) in enumerate(atomic_actions, 1):
                        action = "%(no)i. %(action)s" % {"no": c, "action": a}
                        headers.append(action)
                        float_cols.append(action)
                    break
            table_rows = []
            formatters = dict(zip(float_cols,
                                  [cliutils.pretty_float_formatter(col, 3)
                                   for col in float_cols]))
            for (c, r) in enumerate(raw_data, 1):
                dlist = [c]
                dlist.append(r["duration"])
                if r["atomic_actions"]:
                    for action in atomic_actions:
                        dlist.append(r["atomic_actions"].get(action) or 0)
                table_rows.append(rutils.Struct(**dict(zip(headers, dlist))))
            cliutils.print_list(table_rows,
                                fields=headers,
                                formatters=formatters)
            print()

        task = db.task_get_detailed(task_id)

        if task is None:
            print("The task %s can not be found" % task_id)
            return(1)

        print()
        print("-" * 80)
        print(_("Task %(task_id)s: %(status)s")
              % {"task_id": task_id, "status": task["status"]})

        if task["status"] == consts.TaskStatus.FAILED:
            print("-" * 80)
            verification = yaml.safe_load(task["verification_log"])

            if not logging.is_debug():
                print(verification[0])
                print(verification[1])
                print()
                print(_("For more details run:\nrally -vd task detailed %s")
                      % task["uuid"])
            else:
                print(yaml.safe_load(verification[2]))
            return

        for result in task["results"]:
            key = result["key"]
            print("-" * 80)
            print()
            print("test scenario %s" % key["name"])
            print("args position %s" % key["pos"])
            print("args values:")
            print(json.dumps(key["kw"], indent=2))

            raw = result["data"]["raw"]
            table_cols = ["action", "min", "median",
                          "90%ile", "95%ile", "max",
                          "avg", "success", "count"]
            float_cols = ["min", "median",
                          "90%ile", "95%ile", "max",
                          "avg"]
            formatters = dict(zip(float_cols,
                                  [cliutils.pretty_float_formatter(col, 3)
                                   for col in float_cols]))
            table_rows = []

            actions_data = utils.get_atomic_actions_data(raw)
            for action in actions_data:
                durations = actions_data[action]
                if durations:
                    data = [action,
                            round(min(durations), 3),
                            round(utils.median(durations), 3),
                            round(utils.percentile(durations, 0.90), 3),
                            round(utils.percentile(durations, 0.95), 3),
                            round(max(durations), 3),
                            round(utils.mean(durations), 3),
                            "%.1f%%" % (len(durations) * 100.0 / len(raw)),
                            len(raw)]
                else:
                    data = [action, None, None, None, None, None, None,
                            "0.0%", len(raw)]
                table_rows.append(rutils.Struct(**dict(zip(table_cols, data))))

            cliutils.print_list(table_rows, fields=table_cols,
                                formatters=formatters,
                                table_label="Response Times (sec)",
                                sortby_index=None)

            if iterations_data:
                _print_iterations_data(raw)

            print(_("Load duration: %s") % result["data"]["load_duration"])
            print(_("Full duration: %s") % result["data"]["full_duration"])

            # NOTE(hughsaunders): ssrs=scenario specific results
            ssrs = []
            for result in raw:
                data = result["scenario_output"].get("data")
                if data:
                    ssrs.append(data)
            if ssrs:
                keys = set()
                for ssr in ssrs:
                    keys.update(ssr.keys())
                headers = ["key", "min", "median",
                           "90%ile", "95%ile", "max",
                           "avg"]
                float_cols = ["min", "median", "90%ile",
                              "95%ile", "max", "avg"]
                formatters = dict(zip(float_cols,
                                  [cliutils.pretty_float_formatter(col, 3)
                                   for col in float_cols]))
                table_rows = []
                for key in keys:
                    values = [float(ssr[key]) for ssr in ssrs if key in ssr]

                    if values:
                        row = [str(key),
                               round(min(values), 3),
                               round(utils.median(values), 3),
                               round(utils.percentile(values, 0.90), 3),
                               round(utils.percentile(values, 0.95), 3),
                               round(max(values), 3),
                               round(utils.mean(values), 3)]
                    else:
                        row = [str(key)] + ["n/a"] * 6
                    table_rows.append(rutils.Struct(**dict(zip(headers, row))))
                print("\nScenario Specific Results\n")
                cliutils.print_list(table_rows,
                                    fields=headers,
                                    formatters=formatters,
                                    table_label="Response Times (sec)")

                for result in raw:
                    errors = result["scenario_output"].get("errors")
                    if errors:
                        print(errors)

        print()
        print("HINTS:")
        print(_("* To plot HTML graphics with this data, run:"))
        print("\trally task report %s --out output.html" % task["uuid"])
        print()
        print(_("* To generate a JUnit report, run:"))
        print("\trally task report %s --junit --out output.xml" %
              task["uuid"])
        print()
        print(_("* To get raw JSON output of task results, run:"))
        print("\trally task results %s\n" % task["uuid"])

    @cliutils.args("--uuid", type=str, dest="task_id", help="uuid of task")
    @envutils.with_default_task_id
    @cliutils.suppress_warnings
    def results(self, task_id=None):
        """Display raw task results.

        This will produce a lot of output data about every iteration.

        :param task_id: Task uuid
        """
        results = [{"key": x["key"], "result": x["data"]["raw"],
                    "sla": x["data"]["sla"],
                    "load_duration": x["data"]["load_duration"],
                    "full_duration": x["data"]["full_duration"]}
                   for x in objects.Task.get(task_id).get_results()]

        if results:
            print(json.dumps(results, sort_keys=True, indent=4))
        else:
            print(_("The task %s marked as '%s'. Results "
                    "available when it is '%s' .") % (
                task_id, consts.TaskStatus.FAILED, consts.TaskStatus.FINISHED))
            return(1)

    @cliutils.args("--deployment", type=str, dest="deployment",
                   help="List tasks from specified deployment."
                   "By default tasks listed from active deployment.")
    @cliutils.args("--all-deployments", action="store_true",
                   dest="all_deployments",
                   help="List tasks from all deployments.")
    @cliutils.args("--status", type=str, dest="status",
                   help="List tasks with specified status."
                   " Available statuses: %s" % ", ".join(consts.TaskStatus))
    @cliutils.args("--uuids-only", action="store_true",
                   dest="uuids_only", help="List task UUIDs only")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    def list(self, deployment=None, all_deployments=False, status=None,
             uuids_only=False):
        """List tasks, started and finished.

        Displayed tasks could be filtered by status or deployment.
        By default 'rally task list' will display tasks from active deployment
        without filtering by status.
        :param deployment: UUID or name of deployment
        :param status: task status to filter by.
            Available task statuses are in rally.consts.TaskStatus
        :param all_deployments: display tasks from all deployments
        :param uuids_only: list task UUIDs only
        """

        filters = {}
        headers = ["uuid", "deployment_name", "created_at", "duration",
                   "status", "tag"]

        if status in consts.TaskStatus:
            filters.setdefault("status", status)
        elif status:
            print(_("Error: Invalid task status '%s'.\n"
                    "Available statuses: %s") % (
                  status, ", ".join(consts.TaskStatus)),
                  file=sys.stderr)
            return(1)

        if not all_deployments:
            filters.setdefault("deployment", deployment)

        task_list = [task.to_dict() for task in objects.Task.list(**filters)]

        for x in task_list:
            x["duration"] = x["updated_at"] - x["created_at"]

        if uuids_only:
            if task_list:
                cliutils.print_list(task_list, ["uuid"],
                                    print_header=False,
                                    print_border=False)
        elif task_list:
            cliutils.print_list(
                task_list,
                headers, sortby_index=headers.index("created_at"))
        else:
            if status:
                print(_("There are no tasks in '%s' status. "
                        "To run a new task, use:\n"
                        "\trally task start") % status)
            else:
                print(_("There are no tasks. To run a new task, use:\n"
                        "\trally task start"))

    @cliutils.args("--tasks", dest="tasks", nargs="+",
                   help="uuids of tasks or json files with task results")
    @cliutils.args("--out", type=str, dest="out", required=True,
                   help="Path to output file.")
    @cliutils.args("--open", dest="open_it", action="store_true",
                   help="Open it in browser.")
    @cliutils.args("--html", dest="out_format",
                   action="store_const", const="html",
                   help="Generate the report in HTML.")
    @cliutils.args("--junit", dest="out_format",
                   action="store_const", const="junit",
                   help="Generate the report in the JUnit format.")
    @envutils.default_from_global("tasks", envutils.ENV_TASK, "--uuid")
    @cliutils.suppress_warnings
    def report(self, tasks=None, out=None, open_it=False, out_format="html"):
        """Generate report file for specified task.

        :param task_id: UUID, task identifier
        :param tasks: list, UUIDs od tasks or pathes files with tasks results
        :param out: str, output file name
        :param open_it: bool, whether to open output file in web browser
        :param out_format: output format (junit or html)
        """

        tasks = isinstance(tasks, list) and tasks or [tasks]

        results = []
        message = []
        processed_names = {}
        for task_file_or_uuid in tasks:
            if os.path.exists(os.path.expanduser(task_file_or_uuid)):
                with open(os.path.expanduser(task_file_or_uuid),
                          "r") as inp_js:
                    tasks_results = json.load(inp_js)
                    for result in tasks_results:
                        try:
                            jsonschema.validate(
                                result,
                                objects.task.TASK_RESULT_SCHEMA)
                        except jsonschema.ValidationError as e:
                            print(_("ERROR: Invalid task result format in %s")
                                  % task_file_or_uuid, file=sys.stderr)
                            print(six.text_type(e), file=sys.stderr)
                            return 1

            elif uuidutils.is_uuid_like(task_file_or_uuid):
                tasks_results = map(
                    lambda x: {"key": x["key"],
                               "sla": x["data"]["sla"],
                               "result": x["data"]["raw"],
                               "load_duration": x["data"]["load_duration"],
                               "full_duration": x["data"]["full_duration"]},
                    objects.Task.get(task_file_or_uuid).get_results())
            else:
                print(_("ERROR: Invalid UUID or file name passed: %s"
                        ) % task_file_or_uuid,
                      file=sys.stderr)
                return 1

            for task_result in tasks_results:
                if task_result["key"]["name"] in processed_names:
                    processed_names[task_result["key"]["name"]] += 1
                    task_result["key"]["pos"] = processed_names[
                        task_result["key"]["name"]]
                else:
                    processed_names[task_result["key"]["name"]] = 0
                results.append(task_result)

        output_file = os.path.expanduser(out)

        if out_format == "html":
            with open(output_file, "w+") as f:
                f.write(plot.plot(results))
            if open_it:
                webbrowser.open_new_tab("file://" + os.path.realpath(out))
        elif out_format == "junit":
            test_suite = junit.JUnit("Rally test suite")
            for result in results:
                if isinstance(result["sla"], list):
                    message = ",".join([sla["detail"] for sla in
                                        result["sla"] if not sla["success"]])
                if message:
                    outcome = junit.JUnit.FAILURE
                else:
                    outcome = junit.JUnit.SUCCESS
                test_suite.add_test(result["key"]["name"],
                                    result["full_duration"], outcome, message)
            with open(output_file, "w+") as f:
                f.write(test_suite.to_xml())
        else:
            print(_("Invalid output format: %s") % out_format,
                  file=sys.stderr)
            return 1

    @cliutils.args("--force", action="store_true", help="force delete")
    @cliutils.args("--uuid", type=str, dest="task_id", nargs="*",
                   metavar="TASK_ID",
                   help="uuid of task or a list of task uuids")
    @envutils.with_default_task_id
    def delete(self, task_id=None, force=False):
        """Delete task and its results.

        :param task_id: Task uuid or a list of task uuids
        :param force: Force delete or not
        """

        def _delete_single_task(tid, force):
            try:
                api.Task.delete(tid, force=force)
                print("Successfully deleted task `%s`" % tid)
            except exceptions.TaskInvalidStatus as e:
                print(e)
                print("Use '--force' option to delete the task with vague "
                      "state.")

        if isinstance(task_id, list):
            for tid in task_id:
                _delete_single_task(tid, force)
        else:
            _delete_single_task(task_id, force)

    @cliutils.args("--uuid", type=str, dest="task_id", help="uuid of task")
    @cliutils.args("--json", dest="tojson",
                   action="store_true",
                   help="output in json format")
    @envutils.with_default_task_id
    def sla_check(self, task_id=None, tojson=False):
        """Display SLA check results table.

        :param task_id: Task uuid.
        :returns: Number of failed criteria.
        """
        results = objects.Task.get(task_id).get_results()
        failed_criteria = 0
        data = []
        STATUS_PASS = "PASS"
        STATUS_FAIL = "FAIL"
        for result in results:
            key = result["key"]
            for sla in sorted(result["data"]["sla"],
                              key=lambda x: x["criterion"]):
                success = sla.pop("success")
                sla["status"] = success and STATUS_PASS or STATUS_FAIL
                sla["benchmark"] = key["name"]
                sla["pos"] = key["pos"]
                failed_criteria += int(not success)
                data.append(sla if tojson else rutils.Struct(**sla))
        if tojson:
            print(json.dumps(data, sort_keys=False))
        else:
            cliutils.print_list(data, ("benchmark", "pos", "criterion",
                                       "status", "detail"))
        return failed_criteria

    @cliutils.args("--task", type=str, dest="task", required=False,
                   help="UUID of the task")
    def use(self, task):
        """Set active task.

        :param task: Task uuid.
        """
        print("Using task: %s" % task)
        db.task_get(task)
        fileutils.update_globals_file("RALLY_TASK", task)
