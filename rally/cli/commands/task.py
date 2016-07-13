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
import traceback
import webbrowser

import jsonschema
from oslo_utils import uuidutils
import six
from six.moves.urllib import parse as urlparse
import yaml

from rally import api
from rally.cli import cliutils
from rally.cli import envutils
from rally.common import fileutils
from rally.common.i18n import _
from rally.common import junit
from rally.common import logging
from rally.common import utils as rutils
from rally import consts
from rally import exceptions
from rally import plugins
from rally.task import exporter
from rally.task.processing import plot


class FailedToLoadTask(exceptions.RallyException):
    msg_fmt = _("Failed to load task")

LOG = logging.getLogger(__name__)


class TaskCommands(object):
    """Set of commands that allow you to manage benchmarking tasks and results.

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
        try:
            input_task = self._load_task(task, task_args, task_args_file)
        except Exception as err:
            if task_instance:
                task_instance.set_failed(err.__class__.__name__,
                                         str(err),
                                         json.dumps(traceback.format_stack()))
            raise
        api.Task.validate(deployment, input_task, task_instance)
        print(_("Task config is valid :)"))
        return input_task

    @cliutils.args("--deployment", dest="deployment", type=str,
                   metavar="<uuid>", required=False,
                   help="UUID or name of a deployment.")
    @cliutils.args("--task", "--filename", metavar="<path>",
                   help="Path to the input task file.")
    @cliutils.args("--task-args", metavar="<json>", dest="task_args",
                   help="Input task args (JSON dict). These args are used "
                        "to render the Jinja2 template in the input task.")
    @cliutils.args("--task-args-file", metavar="<path>", dest="task_args_file",
                   help="Path to the file with input task args (dict in "
                        "JSON/YAML). These args are used "
                        "to render the Jinja2 template in the input task.")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    @plugins.ensure_plugins_are_loaded
    def validate(self, task, deployment=None, task_args=None,
                 task_args_file=None):
        """Validate a task configuration file.

        This will check that task configuration file has valid syntax and
        all required options of scenarios, contexts, SLA and runners are set.

        If both task_args and task_args_file are specified, they will
        be merged. task_args has a higher priority so it will override
        values from task_args_file.

        :param task: Path to the input task file.
        :param task_args: Input task args (JSON dict). These args are
                          used to render the Jinja2 template in the
                          input task.
        :param task_args_file: Path to the file with input task args
                               (dict in JSON/YAML). These args are
                               used to render the Jinja2 template in
                               the input task.
        :param deployment: UUID or name of the deployment
        """
        try:
            self._load_and_validate_task(task, task_args, task_args_file,
                                         deployment)

        except (exceptions.InvalidTaskException, FailedToLoadTask) as e:
            print(e, file=sys.stderr)
            return(1)

    @cliutils.args("--deployment", dest="deployment", type=str,
                   metavar="<uuid>", required=False,
                   help="UUID or name of a deployment.")
    @cliutils.args("--task", "--filename", metavar="<path>",
                   help="Path to the input task file")
    @cliutils.args("--task-args", dest="task_args", metavar="<json>",
                   help="Input task args (JSON dict). These args are used "
                        "to render the Jinja2 template in the input task.")
    @cliutils.args("--task-args-file", dest="task_args_file", metavar="<path>",
                   help="Path to the file with input task args (dict in "
                        "JSON/YAML). These args are used "
                        "to render the Jinja2 template in the input task.")
    @cliutils.args("--tag", help="Tag for this task")
    @cliutils.args("--no-use", action="store_false", dest="do_use",
                   help="Don't set new task as default for future operations.")
    @cliutils.args("--abort-on-sla-failure", action="store_true",
                   dest="abort_on_sla_failure",
                   help="Abort the execution of a benchmark scenario when"
                        "any SLA check for it fails.")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    @plugins.ensure_plugins_are_loaded
    def start(self, task, deployment=None, task_args=None, task_args_file=None,
              tag=None, do_use=False, abort_on_sla_failure=False):
        """Start benchmark task.

        If both task_args and task_args_file are specified, they will
        be merged. task_args has a higher priority so it will override
        values from task_args_file.

        :param task: Path to the input task file.
        :param task_args: Input task args (JSON dict). These args are
                          used to render the Jinja2 template in the
                          input task.
        :param task_args_file: Path to the file with input task args
                               (dict in JSON/YAML). These args are
                               used to render the Jinja2 template in
                               the input task.
        :param deployment: UUID or name of the deployment
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
            task_instance.set_failed(type(e).__name__,
                                     str(e),
                                     json.dumps(traceback.format_exc()))
            print(e, file=sys.stderr)
            return(1)

    @cliutils.args("--uuid", type=str, dest="task_id", help="UUID of task.")
    @envutils.with_default_task_id
    @cliutils.args(
        "--soft", action="store_true",
        help="Abort task after current scenario finishes execution.")
    def abort(self, task_id=None, soft=False):
        """Abort a running benchmarking task.

        :param task_id: Task uuid
        :param soft: if set to True, task should be aborted after execution of
                     current scenario
        """
        if soft:
            print("INFO: please be informed that soft abort won't stop "
                  "a running scenario, but will prevent new ones from "
                  "starting. If you are running task with only one "
                  "scenario, soft abort will not help at all.")

        api.Task.abort(task_id, soft, async=False)

        print("Task %s successfully stopped." % task_id)

    @cliutils.args("--uuid", type=str, dest="task_id", help="UUID of task")
    @envutils.with_default_task_id
    def status(self, task_id=None):
        """Display the current status of a task.

        :param task_id: Task uuid
        Returns current status of task
        """

        task = api.Task.get(task_id)
        print(_("Task %(task_id)s: %(status)s")
              % {"task_id": task_id, "status": task["status"]})

    @cliutils.args("--uuid", type=str, dest="task_id",
                   help=("UUID of task. If --uuid is \"last\" the results of "
                         " the most recently created task will be displayed."))
    @cliutils.args("--iterations-data", dest="iterations_data",
                   action="store_true",
                   help="Print detailed results for each iteration.")
    @envutils.with_default_task_id
    def detailed(self, task_id=None, iterations_data=False):
        """Print detailed information about given task.

        :param task_id: str, task uuid
        :param iterations_data: bool, include results for each iteration
        """
        task = api.Task.get_detailed(task_id, extended_results=True)

        if not task:
            print("The task %s can not be found" % task_id)
            return 1

        print()
        print("-" * 80)
        print(_("Task %(task_id)s: %(status)s")
              % {"task_id": task_id, "status": task["status"]})

        if task["status"] == consts.TaskStatus.FAILED:
            print("-" * 80)
            verification = yaml.safe_load(task["verification_log"])
            if logging.is_debug():
                print(yaml.safe_load(verification[2]))
            else:
                print(verification[0])
                print(verification[1])
                print(_("\nFor more details run:\nrally -vd task detailed %s")
                      % task["uuid"])
            return 0
        elif task["status"] not in [consts.TaskStatus.FINISHED,
                                    consts.TaskStatus.ABORTED]:
            print("-" * 80)
            print(_("\nThe task %s marked as '%s'. Results "
                    "available when it is '%s'.") % (
                task_id, task["status"], consts.TaskStatus.FINISHED))
            return 0
        for result in task["results"]:
            key = result["key"]
            print("-" * 80)
            print()
            print("test scenario %s" % key["name"])
            print("args position %s" % key["pos"])
            print("args values:")
            print(json.dumps(key["kw"], indent=2))
            print()

            iterations = []
            iterations_headers = ["iteration", "full duration"]
            iterations_actions = []
            output = []
            task_errors = []
            if iterations_data:
                for i, atomic_name in enumerate(result["info"]["atomic"], 1):
                    action = "%i. %s" % (i, atomic_name)
                    iterations_headers.append(action)
                    iterations_actions.append((atomic_name, action))

            for idx, itr in enumerate(result["iterations"], 1):

                if iterations_data:
                    row = {"iteration": idx,
                           "full duration": itr["duration"]}
                    for name, action in iterations_actions:
                        row[action] = itr["atomic_actions"].get(name, 0)
                    iterations.append(row)

                if "output" in itr:
                    iteration_output = itr["output"]
                else:
                    iteration_output = {"additive": [], "complete": []}

                    # NOTE(amaretskiy): "scenario_output" is supported
                    #   for backward compatibility
                    if ("scenario_output" in itr
                            and itr["scenario_output"]["data"]):
                        iteration_output["additive"].append(
                            {"data": itr["scenario_output"]["data"].items(),
                             "title": "Scenario output",
                             "description": "",
                             "chart_plugin": "StackedArea"})

                for idx, additive in enumerate(iteration_output["additive"]):
                    if len(output) <= idx + 1:
                        output_table = plot.charts.OutputStatsTable(
                            result["info"], title=additive["title"])
                        output.append(output_table)
                    output[idx].add_iteration(additive["data"])

                if itr.get("error"):
                    task_errors.append(TaskCommands._format_task_error(itr))

            self._print_task_errors(task_id, task_errors)

            cols = plot.charts.MainStatsTable.columns
            float_cols = result["info"]["stat"]["cols"][1:7]
            formatters = dict(zip(float_cols,
                                  [cliutils.pretty_float_formatter(col, 3)
                                   for col in float_cols]))
            rows = [dict(zip(cols, r)) for r in result["info"]["stat"]["rows"]]
            cliutils.print_list(rows,
                                fields=cols,
                                formatters=formatters,
                                table_label="Response Times (sec)",
                                sortby_index=None)
            print()

            if iterations_data:
                formatters = dict(zip(iterations_headers[1:],
                                      [cliutils.pretty_float_formatter(col, 3)
                                       for col in iterations_headers[1:]]))
                cliutils.print_list(iterations,
                                    fields=iterations_headers,
                                    table_label="Atomics per iteration",
                                    formatters=formatters)
                print()

            if output:
                cols = plot.charts.OutputStatsTable.columns
                float_cols = cols[1:7]
                formatters = dict(zip(float_cols,
                                  [cliutils.pretty_float_formatter(col, 3)
                                   for col in float_cols]))

                for out in output:
                    data = out.render()
                    rows = [dict(zip(cols, r)) for r in data["data"]["rows"]]
                    if rows:
                        # NOTE(amaretskiy): print title explicitly because
                        #     prettytable fails if title length is too long
                        print(data["title"])
                        cliutils.print_list(rows, fields=cols,
                                            formatters=formatters)
                        print()

            print(_("Load duration: %s") %
                  rutils.format_float_to_str(result["info"]["load_duration"]))
            print(_("Full duration: %s") %
                  rutils.format_float_to_str(result["info"]["full_duration"]))

            print("\nHINTS:")
            print(_("* To plot HTML graphics with this data, run:"))
            print("\trally task report %s --out output.html\n" % task["uuid"])
            print(_("* To generate a JUnit report, run:"))
            print("\trally task report %s --junit --out output.xml\n" %
                  task["uuid"])
            print(_("* To get raw JSON output of task results, run:"))
            print("\trally task results %s\n" % task["uuid"])

    @cliutils.args("--uuid", type=str, dest="task_id", help="UUID of task.")
    @envutils.with_default_task_id
    @cliutils.suppress_warnings
    def results(self, task_id=None):
        """Display raw task results.

        This will produce a lot of output data about every iteration.

        :param task_id: Task uuid
        """
        task = api.Task.get(task_id)
        finished_statuses = (consts.TaskStatus.FINISHED,
                             consts.TaskStatus.ABORTED)
        if task["status"] not in finished_statuses:
            print(_("Task status is %s. Results available when it is one "
                    "of %s.") % (task["status"], ", ".join(finished_statuses)))
            return 1

        results = [{"key": x["key"], "result": x["data"]["raw"],
                    "sla": x["data"]["sla"],
                    "load_duration": x["data"]["load_duration"],
                    "full_duration": x["data"]["full_duration"]}
                   for x in task.get_results()]

        print(json.dumps(results, sort_keys=True, indent=4))

    @cliutils.args("--deployment", dest="deployment", type=str,
                   metavar="<uuid>", required=False,
                   help="UUID or name of a deployment.")
    @cliutils.args("--all-deployments", action="store_true",
                   dest="all_deployments",
                   help="List tasks from all deployments.")
    @cliutils.args("--status", type=str, dest="status",
                   help="List tasks with specified status."
                   " Available statuses: %s" % ", ".join(consts.TaskStatus))
    @cliutils.args("--uuids-only", action="store_true",
                   dest="uuids_only", help="List task UUIDs only.")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    def list(self, deployment=None, all_deployments=False, status=None,
             uuids_only=False):
        """List tasks, started and finished.

        Displayed tasks can be filtered by status or deployment.  By
        default 'rally task list' will display tasks from the active
        deployment without filtering by status.

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

        task_list = [task.to_dict() for task in api.Task.list(**filters)]

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

    @cliutils.args("--out", metavar="<path>",
                   type=str, dest="out", required=False,
                   help="Path to output file.")
    @cliutils.args("--open", dest="open_it", action="store_true",
                   help="Open the output in a browser.")
    @cliutils.args("--tasks", dest="tasks", nargs="+",
                   help="UUIDs of tasks, or JSON files with task results")
    @cliutils.suppress_warnings
    def trends(self, *args, **kwargs):
        """Generate workloads trends HTML report."""
        tasks = kwargs.get("tasks", []) or list(args)

        if not tasks:
            print(_("ERROR: At least one task must be specified"),
                  file=sys.stderr)
            return 1

        results = []
        for task_id in tasks:
            if os.path.exists(os.path.expanduser(task_id)):
                with open(os.path.expanduser(task_id), "r") as inp_js:
                    task_results = json.load(inp_js)
                    for result in task_results:
                        try:
                            jsonschema.validate(
                                result,
                                api.Task.TASK_RESULT_SCHEMA)
                        except jsonschema.ValidationError as e:
                            print(_("ERROR: Invalid task result format in %s")
                                  % task_id, file=sys.stderr)
                            print(six.text_type(e), file=sys.stderr)
                            return 1

            elif uuidutils.is_uuid_like(task_id):
                task_results = map(
                    lambda x: {"key": x["key"],
                               "sla": x["data"]["sla"],
                               "result": x["data"]["raw"],
                               "load_duration": x["data"]["load_duration"],
                               "full_duration": x["data"]["full_duration"]},
                    api.Task.get(task_id).get_results())
            else:
                print(_("ERROR: Invalid UUID or file name passed: %s")
                      % task_id, file=sys.stderr)
                return 1

            results.extend(task_results)

        result = plot.trends(results)

        out = kwargs.get("out")
        if out:
            output_file = os.path.expanduser(out)

            with open(output_file, "w+") as f:
                f.write(result)
            if kwargs.get("open_it"):
                webbrowser.open_new_tab("file://" + os.path.realpath(out))
        else:
            print(result)

    @cliutils.args("--tasks", dest="tasks", nargs="+",
                   help="UUIDs of tasks, or JSON files with task results")
    @cliutils.args("--out", metavar="<path>",
                   type=str, dest="out", required=False,
                   help="Path to output file.")
    @cliutils.args("--open", dest="open_it", action="store_true",
                   help="Open the output in a browser.")
    @cliutils.args("--html", dest="out_format",
                   action="store_const", const="html",
                   help="Generate the report in HTML.")
    @cliutils.args("--html-static", dest="out_format",
                   action="store_const", const="html_static",
                   help=("Generate the report in HTML with embedded "
                         "JS and CSS, so it will not depend on "
                         "Internet availability."))
    @cliutils.args("--junit", dest="out_format",
                   action="store_const", const="junit",
                   help="Generate the report in the JUnit format.")
    @envutils.default_from_global("tasks", envutils.ENV_TASK, "tasks")
    @cliutils.suppress_warnings
    def report(self, tasks=None, out=None, open_it=False, out_format="html"):
        """Generate report file for specified task.

        :param task_id: UUID, task identifier
        :param tasks: list, UUIDs od tasks or pathes files with tasks results
        :param out: str, output file name
        :param open_it: bool, whether to open output file in web browser
        :param out_format: output format (junit, html or html_static)
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
                                api.Task.TASK_RESULT_SCHEMA)
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
                    api.Task.get(task_file_or_uuid).get_results())
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

        if out_format.startswith("html"):
            result = plot.plot(results,
                               include_libs=(out_format == "html_static"))
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
            result = test_suite.to_xml()
        else:
            print(_("Invalid output format: %s") % out_format, file=sys.stderr)
            return 1

        if out:
            output_file = os.path.expanduser(out)

            with open(output_file, "w+") as f:
                f.write(result)
            if open_it:
                webbrowser.open_new_tab("file://" + os.path.realpath(out))
        else:
            print(result)

    @cliutils.args("--force", action="store_true", help="force delete")
    @cliutils.args("--uuid", type=str, dest="task_id", nargs="*",
                   metavar="<task-id>",
                   help="UUID of task or a list of task UUIDs.")
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

    @cliutils.args("--uuid", type=str, dest="task_id", help="UUID of task.")
    @cliutils.args("--json", dest="tojson",
                   action="store_true",
                   help="Output in JSON format.")
    @envutils.with_default_task_id
    def sla_check(self, task_id=None, tojson=False):
        """Display SLA check results table.

        :param task_id: Task uuid.
        :returns: Number of failed criteria.
        """
        results = api.Task.get(task_id).get_results()
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

    @cliutils.args("--uuid", type=str, dest="task_id",
                   help="UUID of the task")
    @cliutils.deprecated_args("--task", dest="task_id", type=str,
                              release="0.2.0", alternative="--uuid")
    def use(self, task_id):
        """Set active task.

        :param task_id: Task uuid.
        """
        print("Using task: %s" % task_id)
        api.Task.get(task_id)
        fileutils.update_globals_file("RALLY_TASK", task_id)

    @cliutils.args("--uuid", dest="uuid", type=str,
                   required=True,
                   help="UUID of a the task.")
    @cliutils.args("--connection", dest="connection_string", type=str,
                   required=True,
                   help="Connection url to the task export system.")
    @plugins.ensure_plugins_are_loaded
    def export(self, uuid, connection_string):
        """Export task results to the custom task's exporting system.

        :param uuid: UUID of the task
        :param connection_string: string used to connect to the system
        """

        parsed_obj = urlparse.urlparse(connection_string)
        try:
            client = exporter.Exporter.get(parsed_obj.scheme)(
                connection_string)
        except exceptions.InvalidConnectionString as e:
            if logging.is_debug():
                LOG.exception(e)
            print(e)
            return 1
        except exceptions.PluginNotFound as e:
            if logging.is_debug():
                LOG.exception(e)
            msg = ("\nPlease check your connection string. The format of "
                   "`connection` should be plugin-name://"
                   "<user>:<pwd>@<full_address>:<port>/<path>.<type>")
            print(str(e) + msg)
            return 1

        try:
            client.export(uuid)
        except (IOError, exceptions.RallyException) as e:
            if logging.is_debug():
                LOG.exception(e)
            print(e)
            return 1
        print(_("Task %(uuid)s results was successfully exported to %("
                "connection)s using %(name)s plugin.") % {
                    "uuid": uuid,
                    "connection": connection_string,
                    "name": parsed_obj.scheme
        })

    @staticmethod
    def _print_task_errors(task_id, task_errors):
        print(cliutils.make_header("Task %s has %d error(s)" %
                                   (task_id, len(task_errors))))
        for err_data in task_errors:
            print(*err_data, sep="\n")
            print("-" * 80)

    @staticmethod
    def _format_task_error(data):
        error_type = _("Unknown type")
        error_message = _("Rally hasn't caught anything yet")
        error_traceback = _("No traceback available.")
        try:
            error_type = data["error"][0]
            error_message = data["error"][1]
            error_traceback = data["error"][2]
        except IndexError:
            pass
        return ("%(error_type)s: %(error_message)s\n" %
                {"error_type": error_type, "error_message": error_message},
                error_traceback)
