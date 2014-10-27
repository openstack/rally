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
import pprint
import webbrowser

from oslo.config import cfg
import yaml

from rally.benchmark.processing import plot
from rally.benchmark.processing import utils
from rally.cmd import cliutils
from rally.cmd.commands import use
from rally.cmd import envutils
from rally import db
from rally import exceptions
from rally.i18n import _
from rally.openstack.common import cliutils as common_cliutils
from rally.orchestrator import api
from rally import utils as rutils


class TaskCommands(object):
    """Task management.

    Set of commands that allow you to manage benchmarking tasks and results.
    """

    @cliutils.args('--deployment', type=str, dest='deployment',
                   required=False, help='UUID or name of the deployment')
    @cliutils.args('--task', '--filename',
                   help='Path to the file with full configuration of task')
    @envutils.with_default_deployment
    def validate(self, task, deployment=None):
        """Validate a task configuration file.

        This will check that task configuration file has valid syntax and
        all required options of scenarios, contexts, SLA and runners are set.

        :param task: a file with yaml/json configration
        :param deployment: UUID or name of a deployment
        """

        task = os.path.expanduser(task)
        with open(task, "rb") as task_file:
            config_dict = yaml.safe_load(task_file.read())
        try:
            api.task_validate(deployment, config_dict)
            print("Task config is valid :)")
        except exceptions.InvalidTaskException as e:
            print("Task config is invalid: \n")
            print(e)

    @cliutils.args('--deployment', type=str, dest='deployment',
                   required=False, help='UUID or name of the deployment')
    @cliutils.args('--task', '--filename',
                   help='Path to the file with full configuration of task')
    @cliutils.args('--tag',
                   help='Tag for this task')
    @cliutils.args('--no-use', action='store_false', dest='do_use',
                   help='Don\'t set new task as default for future operations')
    @envutils.with_default_deployment
    def start(self, task, deployment=None, tag=None, do_use=False):
        """Start benchmark task.

        :param task: a file with yaml/json configration
        :param deployment: UUID or name of a deployment
        :param tag: optional tag for this task
        """
        task = os.path.expanduser(task)
        with open(task, 'rb') as task_file:
            config_dict = yaml.safe_load(task_file.read())
            try:
                task = api.create_task(deployment, tag)
                print("=" * 80)
                print(_("Task %(tag)s %(uuid)s is started")
                      % {"uuid": task["uuid"], "tag": task["tag"]})
                print("-" * 80)
                api.start_task(deployment, config_dict, task=task)
                self.detailed(task_id=task['uuid'])
                if do_use:
                    use.UseCommands().task(task['uuid'])
            except exceptions.InvalidConfigException:
                return(1)
            except KeyboardInterrupt:
                api.abort_task(task['uuid'])
                raise

    @cliutils.args('--uuid', type=str, dest='task_id', help='UUID of task')
    @envutils.with_default_task_id
    def abort(self, task_id=None):
        """Abort started benchmarking task.

        :param task_id: Task uuid
        """

        api.abort_task(task_id)

    @cliutils.args('--uuid', type=str, dest='task_id', help='UUID of task')
    @envutils.with_default_task_id
    def status(self, task_id=None):
        """Display current status of task.

        :param task_id: Task uuid
        Returns current status of task
        """

        task = db.task_get(task_id)
        print(_("Task %(task_id)s is %(status)s.")
              % {'task_id': task_id, 'status': task['status']})

    @cliutils.args(
        '--uuid', type=str, dest='task_id',
        help=('uuid of task, if --uuid is "last" results of most '
              'recently created task will be displayed.'))
    @cliutils.args('--iterations-data', dest='iterations_data',
                   action='store_true',
                   help='print detailed results for each iteration')
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
                if r["atomic_actions"]:
                    dlist.append(r["duration"])
                    for action in atomic_actions:
                        dlist.append(r["atomic_actions"].get(action) or 0)
                    table_rows.append(rutils.Struct(**dict(zip(headers,
                                                               dlist))))
                else:
                    data = dlist + [None for i in range(1, len(headers))]
                    table_rows.append(rutils.Struct(**dict(zip(headers,
                                                               data))))
            common_cliutils.print_list(table_rows,
                                       fields=headers,
                                       formatters=formatters)
            print()

        if task_id == "last":
            task = db.task_get_detailed_last()
            task_id = task.uuid
        else:
            task = db.task_get_detailed(task_id)

        if task is None:
            print("The task %s can not be found" % task_id)
            return(1)

        print()
        print("=" * 80)
        print(_("Task %(task_id)s is %(status)s.")
              % {"task_id": task_id, "status": task["status"]})

        if task["failed"]:
            print("-" * 80)
            verification = yaml.safe_load(task["verification_log"])

            if not cfg.CONF.debug:
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
            pprint.pprint(key["kw"])

            scenario_time = result["data"]["scenario_duration"]
            raw = result["data"]["raw"]
            table_cols = ["action", "min (sec)", "avg (sec)", "max (sec)",
                          "90 percentile", "95 percentile", "success",
                          "count"]
            float_cols = ["min (sec)", "avg (sec)", "max (sec)",
                          "90 percentile", "95 percentile"]
            formatters = dict(zip(float_cols,
                                  [cliutils.pretty_float_formatter(col, 3)
                                   for col in float_cols]))
            table_rows = []

            actions_data = utils.get_atomic_actions_data(raw)
            for action in actions_data:
                durations = actions_data[action]
                if durations:
                    data = [action,
                            min(durations),
                            utils.mean(durations),
                            max(durations),
                            utils.percentile(durations, 0.90),
                            utils.percentile(durations, 0.95),
                            "%.1f%%" % (len(durations) * 100.0 / len(raw)),
                            len(raw)]
                else:
                    data = [action, None, None, None, None, None,
                            "0.0%", len(raw)]
                table_rows.append(rutils.Struct(**dict(zip(table_cols, data))))

            common_cliutils.print_list(table_rows, fields=table_cols,
                                       formatters=formatters)

            if iterations_data:
                _print_iterations_data(raw)

            print(_("Whole scenario time without context preparation: "),
                  scenario_time)

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
                headers = ["key", "max", "avg", "min",
                           "90 pecentile", "95 pecentile"]
                float_cols = ["max", "avg", "min",
                              "90 pecentile", "95 pecentile"]
                formatters = dict(zip(float_cols,
                                  [cliutils.pretty_float_formatter(col, 3)
                                   for col in float_cols]))
                table_rows = []
                for key in keys:
                    values = [float(ssr[key]) for ssr in ssrs if key in ssr]

                    if values:
                        row = [str(key),
                               max(values),
                               utils.mean(values),
                               min(values),
                               utils.percentile(values, 0.90),
                               utils.percentile(values, 0.95)]
                    else:
                        row = [str(key)] + ['n/a'] * 5
                    table_rows.append(rutils.Struct(**dict(zip(headers, row))))
                print("\nScenario Specific Results\n")
                common_cliutils.print_list(table_rows,
                                           fields=headers,
                                           formatters=formatters)

                for result in raw:
                    errors = result["scenario_output"].get("errors")
                    if errors:
                        print(errors)

        print()
        print("HINTS:")
        print(_("* To plot HTML graphics with this data, run:"))
        print("\trally task report %s --out output.html" % task["uuid"])
        print()
        print(_("* To get raw JSON output of task results, run:"))
        print("\trally task results %s\n" % task["uuid"])

    @cliutils.args('--uuid', type=str, dest='task_id', help='uuid of task')
    @envutils.with_default_task_id
    def results(self, task_id=None):
        """Display raw task results.

        This will produce a lot of output data about every iteration.

        :param task_id: Task uuid
        """

        results = map(lambda x: {"key": x["key"], 'result': x['data']['raw'],
                                 "sla": x["data"]["sla"]},
                      db.task_result_get_all_by_uuid(task_id))

        if results:
            print(json.dumps(results, sort_keys=True, indent=4))
        else:
            print(_("The task %s can not be found") % task_id)
            return(1)

    def list(self, task_list=None):
        """List all tasks, started and finished."""

        headers = ['uuid', 'created_at', 'status', 'failed', 'tag']
        task_list = task_list or db.task_list()
        if task_list:
            common_cliutils.print_list(task_list, headers,
                                       sortby_index=headers.index(
                                           'created_at'))
        else:
            print(_("There are no tasks. To run a new task, use:"
                    "\nrally task start"))

    @cliutils.args('--uuid', type=str, dest='task_id', help='uuid of task')
    @cliutils.args('--out', type=str, dest='out', required=False,
                   help='Path to output file.')
    @cliutils.args('--open', dest='open_it', action='store_true',
                   help='Open it in browser.')
    @envutils.with_default_task_id
    def report(self, task_id=None, out=None, open_it=False):
        """Generate HTML report file for specified task.

        :param task_id: int, task identifier
        :param out: str, output html file name
        :param open_it: bool, whether to open output file in web browser
        """
        results = map(lambda x: {"key": x["key"],
                                 "result": x["data"]["raw"]},
                      db.task_result_get_all_by_uuid(task_id))
        if out:
            out = os.path.expanduser(out)
        output_file = out or ("%s.html" % task_id)
        with open(output_file, "w+") as f:
            f.write(plot.plot(results))

        if open_it:
            webbrowser.open_new_tab("file://" + os.path.realpath(output_file))

    # NOTE(maretskiy): plot2html is deprecated by `report'
    #                  and should be removed later
    @cliutils.args('--uuid', type=str, dest='task_id', help='uuid of task')
    @cliutils.args('--out', type=str, dest='out', required=False,
                   help='Path to output file.')
    @cliutils.args('--open', dest='open_it', action='store_true',
                   help='Open it in browser.')
    @envutils.with_default_task_id
    def plot2html(self, task_id=None, out=None, open_it=False):
        """Deprecated, use `task report' instead."""
        print(self.plot2html.__doc__)
        return self.report(task_id=task_id, out=out, open_it=open_it)

    @cliutils.args('--force', action='store_true', help='force delete')
    @cliutils.args('--uuid', type=str, dest='task_id', nargs="*",
                   metavar="TASK_ID",
                   help='uuid of task or a list of task uuids')
    @envutils.with_default_task_id
    def delete(self, task_id=None, force=False):
        """Delete task and its results.

        :param task_id: Task uuid or a list of task uuids
        :param force: Force delete or not
        """

        if isinstance(task_id, list):
            for tid in task_id:
                api.delete_task(tid, force=force)
        else:
            api.delete_task(task_id, force=force)

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
        task = db.task_result_get_all_by_uuid(task_id)
        failed_criteria = 0
        results = []
        for result in task:
            key = result["key"]
            for sla in result["data"]["sla"]:
                sla["benchmark"] = key["name"]
                sla["pos"] = key["pos"]
                failed_criteria += 0 if sla['success'] else 1
                results.append(sla if tojson else rutils.Struct(**sla))
        if tojson:
            print(json.dumps(results))
        else:
            common_cliutils.print_list(results, ('benchmark', 'pos',
                                                 'criterion', 'success',
                                                 'detail'))
        return failed_criteria
