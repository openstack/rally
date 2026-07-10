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

"""Rally command: task"""

import itertools
import json
import os
import sys
import typing as t
import webbrowser

import typer

from rally import consts
from rally import exceptions
from rally import plugins
from rally.api import API
from rally.cli import argutils
from rally.cli import cliutils
from rally.cli import envutils
from rally.cli import task_results_loader
from rally.cli import yamlutils as yaml
from rally.common import logging
from rally.common import utils as rutils
from rally.common import version
from rally.task import atomic
from rally.task.processing import charts
from rally.utils import strutils


LOG = logging.getLogger(__name__)

task_app = typer.Typer(
    name="task", no_args_is_help=False,
    help="Set of commands that allow you to manage tasks and results.")


class FailedToLoadTask(exceptions.RallyException):
    error_code = 117
    msg_fmt = "Invalid %(source)s passed:\n\n\t %(msg)s"


def _load_and_validate_task(
    api: API, task_file: str, args_file: str | None = None,
    raw_args: str | None = None,
) -> t.Any:
    """Load, render and validate tasks template from file with passed args.

    ``task_file`` may be ``-`` to read the input task from stdin.

    :param task_file: Path to file with input task (or ``-`` for stdin)
    :param raw_args: JSON or YAML representation of dict with args that
        will be used to render input task with jinja2
    :param args_file: Path to file with JSON or YAML representation
        of dict, that will be used to render input with jinja2. If both
        specified task_args and task_args_file they will be merged.
        raw_args has bigger priority so it will update values
        from args_file.
    :returns: Str with loaded and rendered task
    """
    print(cliutils.make_header("Preparing input task"))

    if task_file == "-":
        input_task = sys.stdin.read()
        task_dir = "./"
    else:
        try:
            with open(task_file) as f:
                input_task = f.read()
        except IOError as err:
            raise FailedToLoadTask(
                source="task file",
                msg="Error reading %s: %s" % (task_file, err))
        task_dir = os.path.expanduser(os.path.dirname(task_file)) or "./"

    task_args = {}
    if args_file:
        if args_file == "-":
            args_data = sys.stdin.read()
        else:
            try:
                with open(args_file) as f:
                    args_data = f.read()
            except IOError as err:
                raise FailedToLoadTask(
                    source="--task-args-file",
                    msg="Error reading %s: %s" % (args_file, err))

        try:
            task_args.update(yaml.safe_load(args_data))
        except yaml.ParserError as e:
            raise FailedToLoadTask(
                source="--task-args-file",
                msg="File '%s' has to be YAML or JSON. Details:\n\n%s"
                % (args_file, e))

    if raw_args:
        try:
            data = yaml.safe_load(raw_args)
            if isinstance(data, str):
                raise yaml.ParserError("String '%s' doesn't look like a "
                                       "dictionary." % raw_args)
            task_args.update(data)
        except yaml.ParserError as e:
            args = [keypair.split("=", 1)
                    for keypair in raw_args.split(",")]
            if len([a for a in args if len(a) != 1]) != len(args):
                raise FailedToLoadTask(
                    source="--task-args",
                    msg="Value has to be YAML or JSON. Details:\n\n%s" % e)
            else:
                task_args.update(dict(args))

    try:
        rendered_task = api.task.render_template(task_template=input_task,
                                                 template_dir=task_dir,
                                                 **task_args)
    except Exception as e:
        raise FailedToLoadTask(
            source="task file",
            msg="Failed to render task template.\n\n%s" % e)

    print("Task is:\n%s\n" % rendered_task.strip())
    try:
        parsed_task = yaml.safe_load(rendered_task)
    except Exception as e:
        raise FailedToLoadTask(
            source="task file",
            msg="Wrong format of rendered input task. It should be YAML or"
                " JSON. Details:\n\n%s" % e)

    print("Task syntax is correct :)")
    return parsed_task


def _print_task_errors(task_id: t.Any, task_errors: list) -> None:
    print(cliutils.make_header("Task %s has %d error(s)" %
                               (task_id, len(task_errors))))
    for err_data in task_errors:
        print(*err_data, sep="\n")
        print("-" * 80)


def _format_task_error(data: dict) -> tuple:
    error_type = "Unknown type"
    error_message = "Rally hasn't caught anything yet"
    error_traceback = "No traceback available."
    try:
        error_type = data["error"][0]
        error_message = data["error"][1]
        error_traceback = data["error"][2]
    except IndexError:
        pass
    return ("%(error_type)s: %(error_message)s\n" %
            {"error_type": error_type, "error_message": error_message},
            error_traceback)


def _use(api: API, task_id: str) -> None:
    print("Using task: %s" % task_id)
    api.task.get(task_id=task_id)
    envutils.update_globals_file("RALLY_TASK", task_id)


def _start_task(api: API, deployment: t.Any, task_config: t.Any,
                tags: list | None = None, do_use: bool = False,
                abort_on_sla_failure: bool = False) -> int:
    try:
        task_instance = api.task.create(deployment=deployment, tags=tags)
        tags = "[tags: '%s']" % "', '".join(tags) if tags else ""

        print(cliutils.make_header(
            "Task %(tags)s %(uuid)s: started"
            % {"uuid": task_instance["uuid"], "tags": tags}))
        print("Running Task... This can take a while...\n")
        print("To track task status use:\n")
        print("\trally task status\n\tor\n\trally task detailed\n")

        if do_use:
            _use(api, task_instance["uuid"])

        api.task.start(deployment=deployment, config=task_config,
                       task=task_instance["uuid"],
                       abort_on_sla_failure=abort_on_sla_failure)

    except exceptions.DeploymentNotFinishedStatus as e:
        print("Cannot start a task on unfinished deployment: %s" % e)
        return 1

    if _detailed(api, task_id=task_instance["uuid"]):
        return 2
    return 0


@plugins.ensure_plugins_are_loaded
def _export(api: API, tasks: t.Any = None, output_type: str | None = None,
            output_dest: str | None = None, open_it: bool = False,
            deployment: str | None = None) -> None:
    if deployment is not None:
        tasks = api.task.list(deployment=deployment, uuids_only=True)
        tasks = [task["uuid"] for task in tasks]
    else:
        tasks = isinstance(tasks, list) and tasks or [tasks]

    exported_tasks = []
    for task_file_or_uuid in tasks:
        if os.path.exists(os.path.expanduser(task_file_or_uuid)):
            exported_tasks.extend(task_results_loader.load(task_file_or_uuid))
        else:
            exported_tasks.append(task_file_or_uuid)

    report = api.task.export(tasks=exported_tasks,
                             output_type=output_type,
                             output_dest=output_dest)
    if "files" in report:
        for path in report["files"]:
            output_file = os.path.expanduser(path)
            with open(output_file, "w+") as f:
                f.write(report["files"][path])
            if open_it:
                if "open" in report:
                    webbrowser.open_new_tab(report["open"])

    if "print" in report:
        print(report["print"])


def _detailed(api: API, task_id: str | None = None,
              iterations_data: bool = False,
              filters: list | None = None) -> int | None:
    """Print detailed information about given task."""
    scenarios_filter = []
    only_sla_failures = False
    for filter in filters or []:
        if filter.startswith("scenario="):
            filter_value = filter.split("=")[1]
            scenarios_filter = filter_value.split(",")
        if filter == "sla-failures":
            only_sla_failures = True

    task = api.task.get(task_id=task_id, detailed=True)

    print()
    print("-" * 80)
    print("Task %(task_id)s: %(status)s"
          % {"task_id": task_id, "status": task["status"]})

    if task["status"] == consts.TaskStatus.CRASHED or task["status"] == (
            consts.TaskStatus.VALIDATION_FAILED):
        print("-" * 80)
        validation = task["validation_result"]
        if logging.is_debug():
            print(yaml.safe_load(validation["trace"]))
        else:
            print(validation["etype"])
            print(validation["msg"])
            print("\nFor more details run:\nrally -d task detailed %s"
                  % task["uuid"])
        return 0
    elif task["status"] not in [consts.TaskStatus.FINISHED,
                                consts.TaskStatus.ABORTED]:
        print("-" * 80)
        print("\nThe task %s marked as '%s'. Results "
              "available when it is '%s'."
              % (task_id, task["status"], consts.TaskStatus.FINISHED))
        return 0

    for workload in itertools.chain(
            *[s["workloads"] for s in task["subtasks"]]):
        if scenarios_filter and workload["name"] not in scenarios_filter:
            continue
        if only_sla_failures and workload["pass_sla"]:
            continue

        print("-" * 80)
        print()
        print("test scenario %s" % workload["name"])
        print("args position %s" % workload["position"])
        print("args values:")
        print(json.dumps(
            {"args": workload["args"],
             "runner": workload["runner"],
             "contexts": workload["contexts"],
             "sla": workload["sla"],
             "hooks": [r["config"] for r in workload["hooks"]]},
            indent=2))
        print()

        duration_stats = workload["statistics"]["durations"]

        iterations = []
        iterations_headers = ["iteration", "duration"]
        iterations_actions = []
        output: list = []
        task_errors = []
        if iterations_data:
            atomic_names = [a["display_name"]
                            for a in duration_stats["atomics"]]
            for i, atomic_name in enumerate(atomic_names, 1):
                action = "%i. %s" % (i, atomic_name)
                iterations_headers.append(action)
                iterations_actions.append((atomic_name, action))

        for idx, itr in enumerate(workload["data"], 1):

            if iterations_data:
                row = {"iteration": idx, "duration": itr["duration"]}
                for name, action in iterations_actions:
                    atomic_actions = atomic.merge_atomic_actions(
                        itr["atomic_actions"])
                    action_info: t.Any = atomic_actions.get(name, {})
                    row[action] = action_info.get("duration", 0)
                iterations.append(row)

            if "output" in itr:
                iteration_output = itr["output"]
            else:
                iteration_output = {"additive": [], "complete": []}

            for idx, additive in enumerate(iteration_output["additive"]):
                if len(output) <= idx + 1:
                    output_table = charts.OutputStatsTable(
                        workload, title=additive["title"])
                    output.append(output_table)
                output[idx].add_iteration(additive["data"])

            if itr.get("error"):
                task_errors.append(_format_task_error(itr))

        _print_task_errors(task_id, task_errors)

        cols = charts.MainStatsTable.columns
        formatters = {
            "Action": lambda x: x["display_name"],
            "Min (sec)": lambda x: x["data"]["min"],
            "Median (sec)": lambda x: x["data"]["median"],
            "90%ile (sec)": lambda x: x["data"]["90%ile"],
            "95%ile (sec)": lambda x: x["data"]["95%ile"],
            "Max (sec)": lambda x: x["data"]["max"],
            "Avg (sec)": lambda x: x["data"]["avg"],
            "Success": lambda x: x["data"]["success"],
            "Count": lambda x: x["data"]["iteration_count"]
        }

        rows = []

        def make_flat(r: dict, depth: int = 0) -> None:
            if depth > 0:
                r["display_name"] = (" %s> %s" % ("-" * depth,
                                                  r["display_name"]))

            rows.append(r)
            for children in r["children"]:
                make_flat(children, depth + 1)

        for row in itertools.chain(duration_stats["atomics"],
                                   [duration_stats["total"]]):
            make_flat(row)
        cliutils.print_list(rows,
                            fields=cols,
                            formatters=formatters,
                            normalize_field_names=True,
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
            cols = charts.OutputStatsTable.columns
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

        print("Load duration: %s"
              % strutils.format_float_to_str(workload["load_duration"]))
        print("Full duration: %s"
              % strutils.format_float_to_str(workload["full_duration"]))

    print("\nHINTS:")
    print("* To plot HTML graphics with this data, run:")
    print("\trally task report %s --out output.html\n" % task["uuid"])
    print("* To generate a JUnit report, run:")
    print("\trally task export %s --type junit-xml --to output.xml\n" %
          task["uuid"])
    print("* To get raw JSON output of task results, run:")
    print("\trally task report %s --json --out output.json\n" %
          task["uuid"])

    if not task["pass_sla"]:
        print("At least one workload did not pass SLA criteria.\n")
        return 1


@task_app.command()
@plugins.ensure_plugins_are_loaded
def validate(
    task_file: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--task", "--filename",
            help="Path to the input task file (or '-' for stdin)."
        )
    ],
    deployment: t.Annotated[
        str,
        typer.Option(
            envvar=envutils.ENV_ENV,
            help="UUID or name of a deployment."
        )
    ],
    task_args: t.Annotated[
        str | None,
        typer.Option(
            help="Input task args (JSON dict). These args are used to render "
                 "the Jinja2 template in the input task."
        )
    ] = None,
    task_args_file: t.Annotated[
        str | None,
        typer.Option(
            help="Path to the file with input task args (dict in JSON/YAML). "
                 "These args are used to render the Jinja2 template in the "
                 "input task."
        )
    ] = None,
) -> None:
    """Validate a task configuration file.

    This will check that task configuration file has valid syntax and
    all required options of scenarios, contexts, SLA and runners are set.

    If both task_args and task_args_file are specified, they will
    be merged. task_args has a higher priority so it will override
    values from task_args_file.
    """
    api = cliutils.get_api()
    task = _load_and_validate_task(api, task_file, raw_args=task_args,
                                   args_file=task_args_file)

    api.task.validate(deployment=deployment, config=task)

    print("Input Task is valid :)")


@task_app.command()
@plugins.ensure_plugins_are_loaded
def start(
    task_file: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--task", "--filename",
            help="Path to the input task file (or '-' for stdin)."
        )
    ],
    deployment: t.Annotated[
        str,
        typer.Option(
            envvar=envutils.ENV_ENV,
            help="UUID or name of a deployment."
        )
    ],
    task_args: t.Annotated[
        str | None,
        typer.Option(
            help="Input task args (JSON dict). These args are used to render "
                 "the Jinja2 template in the input task."
        )
    ] = None,
    task_args_file: t.Annotated[
        str | None,
        typer.Option(
            help="Path to the file with input task args (dict in JSON/YAML). "
                 "These args are used to render the Jinja2 template in the "
                 "input task."
        )
    ] = None,
    tags: t.Annotated[
        list[str] | None,
        typer.Option(
            "--tag",
            help="Mark the task with a tag or a few tags."
        )
    ] = None,
    no_use: t.Annotated[
        bool,
        typer.Option(
            "--no-use",
            help="Don't set new task as default for future operations."
        )
    ] = False,
    abort_on_sla_failure: t.Annotated[
        bool,
        typer.Option(
            "--abort-on-sla-failure",
            help="Abort the execution of a task when any SLA check for it "
                 "fails for subtask or workload."
        )
    ] = False,
) -> None:
    """Run task.

    If both task_args and task_args_file are specified, they are going to
    be merged. task_args has a higher priority so it overrides
    values from task_args_file.
    There are 3 kinds of return codes, 0: no error, 1: running error,
    2: sla check failed.
    """
    api = cliutils.get_api()
    input_task = _load_and_validate_task(api, task_file, raw_args=task_args,
                                         args_file=task_args_file)
    print("Running Rally version", version.version_string())

    rc = _start_task(api, deployment, task_config=input_task, tags=tags,
                     do_use=not no_use,
                     abort_on_sla_failure=abort_on_sla_failure)
    if rc:
        raise typer.Exit(code=rc)


@task_app.command()
@plugins.ensure_plugins_are_loaded
def restart(
    deployment: t.Annotated[
        str,
        typer.Option(
            envvar=envutils.ENV_ENV,
            help="UUID or name of a deployment."
        )
    ],
    task_id: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--uuid",
            envvar=envutils.ENV_TASK,
            help="UUID of task."
        )
    ],
    scenarios: t.Annotated[
        list[str] | None,
        typer.Option(
            "--scenario",
            help="scenario name of workload"
        )
    ] = None,
    tags: t.Annotated[
        list[str] | None,
        typer.Option(
            "--tag",
            help="Mark the task with a tag or a few tags."
        )
    ] = None,
    no_use: t.Annotated[
        bool,
        typer.Option(
            "--no-use",
            help="Don't set new task as default for future operations."
        )
    ] = False,
    abort_on_sla_failure: t.Annotated[
        bool,
        typer.Option(
            "--abort-on-sla-failure",
            help="Abort the execution of a task when any SLA check for it "
                 "fails for subtask or workload."
        )
    ] = False,
) -> None:
    """Restart a task or some scenarios in workloads of task."""
    api = cliutils.get_api()
    task = api.task.get(task_id=task_id, detailed=True)
    if task["status"] == consts.TaskStatus.CRASHED or task["status"] == (
            consts.TaskStatus.VALIDATION_FAILED):
        print("-" * 80)
        print("\nUnable to restart task.")
        validation = task["validation_result"]
        if logging.is_debug():
            print(yaml.safe_load(validation["trace"]))
        else:
            print(validation["etype"])
            print(validation["msg"])
            print("\nFor more details run:\nrally -d task detailed %s"
                  % task["uuid"])
        raise typer.Exit(code=1)
    retask = {"version": 2, "title": task["title"],
              "description": task["description"],
              "tags": task["tags"], "subtasks": []}
    for subtask in task["subtasks"]:
        workloads = []
        for workload in subtask["workloads"]:
            if scenarios is None or workload["name"] in scenarios:
                workloads.append({
                    "scenario": {workload["name"]: workload["args"]},
                    "contexts": workload["contexts"],
                    "runner": {workload["runner_type"]: workload["runner"]},
                    "hooks": workload["hooks"],
                    "sla": workload["sla"]
                })
        if workloads:
            retask["subtasks"].append({
                "title": subtask["title"],
                "description": subtask["description"],
                "workloads": workloads})

    if retask["subtasks"]:
        rc = _start_task(api, deployment, retask, tags=tags,
                         do_use=not no_use,
                         abort_on_sla_failure=abort_on_sla_failure)
        if rc:
            raise typer.Exit(code=rc)
    else:
        print("Not Found matched scenario.")
        raise typer.Exit(code=1)


@task_app.command()
def abort(
    task_id: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--uuid",
            envvar=envutils.ENV_TASK,
            help="UUID of task."
        )
    ],
    soft: t.Annotated[
        bool,
        typer.Option(
            "--soft",
            help="Abort task after current scenario finishes execution."
        )
    ] = False,
) -> None:
    """Abort a running task."""
    if soft:
        print("INFO: please be informed that soft abort won't stop "
              "a running workload, but will prevent new ones from "
              "starting. If you are running task with only one "
              "scenario, soft abort will not help at all.")

    cliutils.get_api().task.abort(task_uuid=task_id, soft=soft, wait=True)

    print("Task %s successfully stopped." % task_id)


@task_app.command()
def status(
    task_id: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--uuid",
            envvar=envutils.ENV_TASK,
            help="UUID of task"
        )
    ],
) -> None:
    """Display the current status of a task."""
    task = cliutils.get_api().task.get(task_id=task_id)
    print("Task %(task_id)s: %(status)s"
          % {"task_id": task_id, "status": task["status"]})


@task_app.command()
def detailed(
    task_id: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--uuid",
            envvar=envutils.ENV_TASK,
            help="UUID of task. If \"last\", the results of the most recently "
                 "created task will be displayed."
        )
    ],
    iterations_data: t.Annotated[
        bool,
        typer.Option(
            "--iterations-data",
            help="Print detailed results for each iteration."
        )
    ] = False,
    filters: t.Annotated[
        list[str] | None,
        typer.Option(
            "--filter-by",
            help="Filter the displayed workloads. <sla-failures>: only "
                 "display the failed workloads. <scenarios>: filter the "
                 "workloads by scenarios, "
                 "scenarios=scenario_name1[,scenario_name2]..."
        )
    ] = None,
) -> None:
    """Print detailed information about given task."""
    _detailed(cliutils.get_api(), task_id, iterations_data, filters)


@task_app.command()
@cliutils.suppress_warnings
def results(
    task_id: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--uuid",
            envvar=envutils.ENV_TASK,
            help="UUID of task."
        )
    ],
) -> None:
    """DEPRECATED since Rally 3.0.0."""
    LOG.warning("CLI method `rally task results` is deprecated since "
                "Rally 3.0.0 and will be removed soon. "
                "Use `rally task report --json` instead.")
    try:
        _export(cliutils.get_api(), tasks=[task_id],
                output_type="old-json-results")
    except exceptions.RallyException as e:
        print(e.format_message())
        raise typer.Exit(code=1)


@task_app.command(name="list")
def list_(
    deployment: t.Annotated[
        str,
        typer.Option(
            envvar=envutils.ENV_ENV,
            help="UUID or name of a deployment."
        )
    ],
    all_deployments: t.Annotated[
        bool,
        typer.Option(
            "--all-deployments",
            help="List tasks from all deployments."
        )
    ] = False,
    status: t.Annotated[
        str | None,
        typer.Option(
            help="List tasks with specified status. Available statuses: %s"
                 % ", ".join(consts.TaskStatus)
        )
    ] = None,
    tags: t.Annotated[
        list[str] | None,
        typer.Option(
            "--tag",
            help="Tags to filter tasks by."
        )
    ] = None,
    uuids_only: t.Annotated[
        bool,
        typer.Option(
            "--uuids-only",
            help="List task UUIDs only."
        )
    ] = False,
) -> None:
    """List tasks, started and finished.

    Displayed tasks can be filtered by status or deployment.  By
    default 'rally task list' will display tasks from the active
    deployment without filtering by status.
    """
    api = cliutils.get_api()
    filters: dict = {}
    headers = ["UUID", "Deployment name", "Created at", "Load duration",
               "Status", "Tag(s)"]

    if status in consts.TaskStatus:
        filters["status"] = status
    elif status:
        print("Error: Invalid task status '%s'.\nAvailable statuses: %s"
              % (status, ", ".join(consts.TaskStatus)), file=sys.stderr)
        raise typer.Exit(code=1)

    if not all_deployments:
        filters["deployment"] = deployment

    if tags:
        filters["tags"] = tags

    task_list = api.task.list(**filters)

    if uuids_only:
        if task_list:
            print("\n".join([t["uuid"] for t in task_list]))
    elif task_list:
        def tags_formatter(task: dict) -> str:
            if not task["tags"]:
                return ""
            return "'%s'" % "', '".join(task["tags"])

        formatters = {
            "Tag(s)": tags_formatter,
            "Load duration": cliutils.pretty_float_formatter(
                "task_duration", 3),
            "Created at": lambda t: t["created_at"].replace("T", " ")
        }

        cliutils.print_list(
            task_list, fields=headers, normalize_field_names=True,
            sortby_index=headers.index("Created at"),
            formatters=formatters)
    else:
        if status:
            print("There are no tasks in '%s' status. "
                  "To run a new task, use:\n\trally task start" % status)
        else:
            print("There are no tasks. To run a new task, use:\n"
                  "\trally task start")


@task_app.command()
@cliutils.suppress_warnings
def trends(
    tasks: t.Annotated[
        list[str] | None,
        typer.Argument(
            help="UUIDs of tasks, or JSON files with task results"
        )
    ] = None,
    out: t.Annotated[
        str | None,
        typer.Option(
            help="Path to output file."
        )
    ] = None,
    open_it: t.Annotated[
        bool,
        typer.Option(
            "--open",
            help="Open the output in a browser."
        )
    ] = False,
    html_static: t.Annotated[
        bool,
        typer.Option(
            "--html-static",
            help="Generate static HTML report."
        )
    ] = False,
) -> None:
    """Generate workloads trends HTML report."""
    if not tasks:
        print("ERROR: At least one task must be specified", file=sys.stderr)
        raise typer.Exit(code=1)

    _export(cliutils.get_api(), tasks=tasks,
            output_type=("trends-html-static" if html_static
                         else "trends-html"),
            output_dest=out, open_it=open_it)


@task_app.command()
@cliutils.suppress_warnings
def report(
    tasks: t.Annotated[
        list[str],
        argutils.ArgumentOrKeyword(
            "--uuid",
            envvar=envutils.ENV_TASK,
            help="UUIDs of tasks or json reports of tasks"
        )
    ],
    out: t.Annotated[
        str | None,
        typer.Option(
            help="Report destination. Can be a path to a file (in case of "
                 "HTML, HTML-STATIC, etc. types) to save the report to or a "
                 "connection string."
        )
    ] = None,
    open_it: t.Annotated[
        bool,
        typer.Option(
            "--open",
            help="Open the output in a browser."
        )
    ] = False,
    html: t.Annotated[
        bool,
        typer.Option(
            "--html",
            help="Generate HTML report."
        )
    ] = False,
    html_static: t.Annotated[
        bool,
        typer.Option(
            "--html-static",
            help="Generate static HTML report."
        )
    ] = False,
    to_json: t.Annotated[
        bool,
        typer.Option(
            "--json",
            help="Generate JSON report."
        )
    ] = False,
    deployment: t.Annotated[
        str | None,
        typer.Option(
            help="Report all tasks with defined deployment"
        )
    ] = None,
) -> None:
    """Generate a report for the specified task(s)."""
    out_format = ("json" if to_json
                  else "html-static" if html_static else "html")
    _export(cliutils.get_api(), tasks=tasks, output_type=out_format,
            output_dest=out, open_it=open_it, deployment=deployment)


@task_app.command()
def delete(
    task_id: t.Annotated[
        list[str],
        argutils.ArgumentOrKeyword(
            "--uuid",
            envvar=envutils.ENV_TASK,
            help="UUID of task or a list of task UUIDs."
        )
    ],
    force: t.Annotated[
        bool,
        typer.Option(
            "--force",
            help="force delete"
        )
    ] = False,
) -> None:
    """Delete task and its results."""
    api = cliutils.get_api()

    def _delete_single_task(tid: t.Any, force: bool) -> None:
        try:
            api.task.delete(task_uuid=tid, force=force)
            print("Successfully deleted task `%s`" % tid)
        except exceptions.DBConflict as e:
            print(e)
            print("Use '--force' option to delete the task with vague state.")

    if isinstance(task_id, list):
        for tid in task_id:
            _delete_single_task(tid, force)
    else:
        _delete_single_task(task_id, force)


@task_app.command(name="sla-check")
def sla_check(
    task_id: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--uuid",
            envvar=envutils.ENV_TASK,
            help="UUID of task."
        )
    ],
    tojson: t.Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output in JSON format."
        )
    ] = False,
) -> None:
    """Display SLA check results table."""
    task = cliutils.get_api().task.get(task_id=task_id, detailed=True)
    failed_criteria = 0
    data = []
    STATUS_PASS = "PASS"
    STATUS_FAIL = "FAIL"
    for workload in itertools.chain(
            *[s["workloads"] for s in task["subtasks"]]):
        for sla in sorted(workload["sla_results"].get("sla", []),
                          key=lambda x: x["criterion"]):
            success = sla.pop("success")
            sla["status"] = success and STATUS_PASS or STATUS_FAIL
            sla["benchmark"] = workload["name"]
            sla["pos"] = workload["position"]
            failed_criteria += int(not success)
            data.append(sla if tojson else rutils.Struct(**sla))
    if tojson:
        print(json.dumps(data, sort_keys=False))
    else:
        cliutils.print_list(data, ("benchmark", "pos", "criterion",
                                   "status", "detail"))
    if not data:
        raise typer.Exit(code=2)
    if failed_criteria:
        raise typer.Exit(code=failed_criteria)


@task_app.command()
def use(
    task_id: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--uuid",
            help="UUID of the task"
        )
    ],
) -> None:
    """Set active task."""
    _use(cliutils.get_api(), task_id)


@task_app.command()
@plugins.ensure_plugins_are_loaded
def export(
    tasks: t.Annotated[
        list[str],
        argutils.ArgumentOrKeyword(
            "--uuid",
            envvar=envutils.ENV_TASK,
            help="UUIDs of tasks or json reports of tasks"
        )
    ],
    output_type: t.Annotated[
        str,
        typer.Option(
            "--type",
            help="Report type. Out-of-the-box types: JSON, HTML, HTML-Static, "
                 "Elastic, JUnit-XML. HINT: You can list all types, executing "
                 "`rally plugin list --plugin-base TaskExporter` command."
        )
    ],
    output_dest: t.Annotated[
        str | None,
        typer.Option(
            "--to",
            help="Report destination. Can be a path to a file (in case of "
                 "JSON, HTML, HTML-Static, JUnit-XML, Elastic etc. types) to "
                 "save the report to or a connection string. It depends on "
                 "the report type."
        )
    ] = None,
    deployment: t.Annotated[
        str | None,
        typer.Option(
            help="Report all tasks with defined deployment"
        )
    ] = None,
) -> None:
    """Export task results to the custom task's exporting system."""
    _export(cliutils.get_api(), tasks=tasks, output_type=output_type,
            output_dest=output_dest, deployment=deployment)


@task_app.command(name="import")
@cliutils.suppress_warnings
def import_results(
    task_file: t.Annotated[
        str,
        typer.Option(
            "--file",
            help="JSON file with task results"
        )
    ],
    deployment: t.Annotated[
        str,
        typer.Option(
            envvar=envutils.ENV_ENV,
            help="UUID or name of a deployment."
        )
    ],
    tags: t.Annotated[
        list[str] | None,
        typer.Option(
            "--tag",
            help="Mark the task with a tag or a few tags."
        )
    ] = None,
) -> None:
    """Import json results of a test into rally database."""
    if os.path.exists(os.path.expanduser(task_file)):
        api = cliutils.get_api()
        tasks_results = task_results_loader.load(task_file)
        for task_results in tasks_results:
            task = api.task.import_results(deployment=deployment,
                                           task_results=task_results,
                                           tags=tags)
            print("Task UUID: %s." % task["uuid"])
    else:
        print("ERROR: Invalid file name passed: %s" % task_file,
              file=sys.stderr)
        raise typer.Exit(code=1)
