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
from rally.benchmark.sla import base as base_sla
from rally.cmd import cliutils
from rally.cmd.commands import use
from rally.cmd import envutils
from rally import db
from rally import exceptions
from rally.openstack.common import cliutils as common_cliutils
from rally.openstack.common.gettextutils import _
from rally.orchestrator import api
from rally import utils as rutils


class TaskCommands(object):

    @cliutils.args('--deploy-id', type=str, dest='deploy_id', required=False,
                   help='UUID of the deployment')
    @cliutils.args('--task', '--filename',
                   help='Path to the file with full configuration of task')
    @cliutils.args('--tag',
                   help='Tag for this task')
    @cliutils.args('--no-use', action='store_false', dest='do_use',
                   help='Don\'t set new task as default for future operations')
    @envutils.with_default_deploy_id
    def start(self, task, deploy_id=None, tag=None, do_use=False):
        """Run a benchmark task.

        :param task: a file with yaml/json configration
        :param deploy_id: a UUID of a deployment
        :param tag: optional tag for this task
        """
        with open(task, 'rb') as task_file:
            config_dict = yaml.safe_load(task_file.read())
            try:
                task = api.create_task(deploy_id, tag)
                print("=" * 80)
                print(_("Task %(tag)s %(uuid)s is started")
                      % {"uuid": task["uuid"], "tag": task["tag"]})
                print("-" * 80)
                api.start_task(deploy_id, config_dict, task=task)
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
        """Force abort task

        :param task_id: Task uuid
        """
        api.abort_task(task_id)

    @cliutils.args('--uuid', type=str, dest='task_id', help='UUID of task')
    @envutils.with_default_task_id
    def status(self, task_id=None):
        """Get status of task

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
        """Get detailed information about task

        :param task_id: Task uuid
        :param iterations_data: print detailed results for each iteration
        Prints detailed information of task.
        """
        def _print_iterations_data(raw):
            headers = ['iteration', "full duration"]
            float_cols = ['full duration']
            for i in range(0, len(raw)):
                if raw[i]['atomic_actions']:
                    for (c, a) in enumerate(raw[i]['atomic_actions'], 1):
                        action = str(c) + "-" + a['action']
                        headers.append(action)
                        float_cols.append(action)
                    break
            table_rows = []
            formatters = dict(zip(float_cols,
                                  [cliutils.pretty_float_formatter(col, 3)
                                   for col in float_cols]))
            for (c, r) in enumerate(raw, 1):
                dlist = [c]
                d = []
                if r['atomic_actions']:
                    for l in r['atomic_actions']:
                        d.append(l['duration'])
                    dlist.append(sum(d))
                    dlist = dlist + d
                    table_rows.append(rutils.Struct(**dict(zip(headers,
                                                               dlist))))
                else:
                    data = dlist + ["N/A" for i in range(1, len(headers))]
                    table_rows.append(rutils.Struct(**dict(zip(headers,
                                                               data))))
            common_cliutils.print_list(table_rows,
                                       fields=headers,
                                       formatters=formatters)
            print()

        def _get_atomic_action_durations(raw):
            atomic_actions_names = []
            for r in raw:
                if 'atomic_actions' in r:
                    for a in r['atomic_actions']:
                        atomic_actions_names.append(a["action"])
                    break
            result = {}
            for atomic_action in atomic_actions_names:
                result[atomic_action] = utils.get_durations(
                    raw,
                    lambda r: next(a["duration"] for a in r["atomic_actions"]
                                   if a["action"] == atomic_action),
                    lambda r: any((a["action"] == atomic_action)
                                  for a in r["atomic_actions"]))
            return result

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

            action_durations = _get_atomic_action_durations(raw)
            actions_list = action_durations.keys()
            action_durations["total"] = utils.get_durations(
                        raw, lambda x: x["duration"], lambda r: not r["error"])
            actions_list.append("total")
            for action in actions_list:
                durations = action_durations[action]
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
                    data = [action, None, None, None, None, None, 0, len(raw)]
                table_rows.append(rutils.Struct(**dict(zip(table_cols, data))))

            common_cliutils.print_list(table_rows, fields=table_cols,
                                       formatters=formatters)

            if iterations_data:
                _print_iterations_data(raw)

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
        print("\trally task plot2html %s --out output.html" % task["uuid"])
        print()
        print(_("* To get raw JSON output of task results, run:"))
        print("\trally task results %s\n" % task["uuid"])

    @cliutils.args('--uuid', type=str, dest='task_id', help='uuid of task')
    @cliutils.args('--pprint', action='store_true', dest='output_pprint',
                   help=('Output in pretty print format'))
    @cliutils.args('--json', action='store_true', dest='output_json',
                   help=('Output in json format(default)'))
    @envutils.with_default_task_id
    def results(self, task_id=None, output_pprint=None, output_json=None):
        """Print raw results of task.

        :param task_id: Task uuid
        :param output_pprint: Output in pretty print format
        :param output_json: Output in json format (Default)
        """
        results = map(lambda x: {"key": x["key"], 'result': x['data']['raw']},
                      db.task_result_get_all_by_uuid(task_id))

        if results:
            if all([output_pprint, output_json]):
                print(_('Please select only one output format'))
                return 1
            elif output_pprint:
                print()
                pprint.pprint(results)
                print()
            else:
                print(json.dumps(results))
        else:
            print(_("The task %s can not be found") % task_id)
            return(1)

    def list(self, task_list=None):
        """Print a list of all tasks."""
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
    def plot2html(self, task_id=None, out=None, open_it=False):
        results = map(lambda x: {"key": x["key"], 'result': x['data']['raw']},
                      db.task_result_get_all_by_uuid(task_id))

        output_file = out or ("%s.html" % task_id)
        with open(output_file, "w+") as f:
            f.write(plot.plot(results))

        if open_it:
            webbrowser.open_new_tab("file://" + os.path.realpath(output_file))

    @cliutils.args('--force', action='store_true', help='force delete')
    @cliutils.args('--uuid', type=str, dest='task_id', nargs="*",
                   metavar="TASK_ID",
                   help='uuid of task or a list of task uuids')
    @envutils.with_default_task_id
    def delete(self, task_id=None, force=False):
        """Delete a specific task and related results.

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
        """Check if task was succeded according to SLA.

        :param task_id: Task uuid.
        :returns: Number of failed criteria.
        """
        task = db.task_get_detailed(task_id)
        failed_criteria = 0
        rows = []
        for row in base_sla.SLA.check_all(task):
            failed_criteria += 0 if row['success'] else 1
            rows.append(row if tojson else rutils.Struct(**row))
        if tojson:
            print(json.dumps(rows))
        else:
            common_cliutils.print_list(rows, ('benchmark', 'pos',
                                              'criterion', 'success'))
        return failed_criteria
