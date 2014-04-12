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

import collections
import json
import math
import os
import pprint
import prettytable
import sys
import webbrowser
import yaml

from oslo.config import cfg

from rally.benchmark.processing import plot
from rally.cmd import cliutils
from rally.cmd.commands import use
from rally.cmd import envutils
from rally import db
from rally import exceptions
from rally.openstack.common.gettextutils import _
from rally.orchestrator import api


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
                sys.exit(1)

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
    @cliutils.args('--no-aggregation', dest='no_aggregation',
                   action='store_true',
                   help='do not aggregate atomic operation results')
    @envutils.with_default_task_id
    def detailed(self, task_id=None, no_aggregation=False):
        """Get detailed information about task

        :param task_id: Task uuid
        :param no_aggregation: do not aggregate atomic operations
        Prints detailed information of task.
        """
        def _print_atomic_actions_time_no_aggregation(raw):
            headers = ['iteration', "full duration"]
            for i in range(0, len(raw)):
                if raw[i]['atomic_actions_time']:
                    for (c, a) in enumerate(raw[i]['atomic_actions_time'], 1):
                        action = str(c) + "-" + a['action']
                        headers.append(action)
                    break
            atomic_action_table = prettytable.PrettyTable(headers)
            for (c, r) in enumerate(raw, 1):
                dlist = [c]
                d = []
                if r['atomic_actions_time']:
                    for l in r['atomic_actions_time']:
                        d.append(l['duration'])
                    dlist.append(sum(d))
                    dlist = dlist + d
                    atomic_action_table.add_row(dlist)
                else:
                    atomic_action_table.add_row(dlist +
                                                ["N/A" for i in
                                                 range(1, len(headers))])
            print(atomic_action_table)
            print()

        def _print_atomic_actions_time_aggregation(raw):
            atime_merged = []
            for r in raw:
                if 'atomic_actions_time' in r:
                    for a in r['atomic_actions_time']:
                        atime_merged.append(a)

            times_by_action = collections.defaultdict(list)
            for at in atime_merged:
                times_by_action[at['action']].append(at['duration'])
            if times_by_action:
                atomic_action_table = prettytable.PrettyTable(
                                                        ['action',
                                                         'count',
                                                         'max (sec)',
                                                         'avg (sec)',
                                                         'min (sec)',
                                                         '90 percentile',
                                                         '95 percentile'])
                for k, v in times_by_action.iteritems():
                    atomic_action_table.add_row([k,
                                                len(v),
                                                max(v),
                                                sum(v) / len(v),
                                                min(v),
                                                percentile(v, 0.90),
                                                percentile(v, 0.95)])
                print(atomic_action_table)
                print()

        def _print_atomic_actions_time(raw):
            if no_aggregation:
                _print_atomic_actions_time_no_aggregation(raw)
            else:
                _print_atomic_actions_time_aggregation(raw)

        if task_id == "last":
            task = db.task_get_detailed_last()
            task_id = task.uuid
        else:
            task = db.task_get_detailed(task_id)

        if task is None:
            print("The task %s can not be found" % task_id)
            return

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

            _print_atomic_actions_time(result["data"]["raw"])

            raw = result["data"]["raw"]
            times = map(lambda x: x['time'],
                        filter(lambda r: not r['error'], raw))
            table = prettytable.PrettyTable(["max (sec)",
                                             "avg (sec)",
                                             "min (sec)",
                                             "90 pecentile",
                                             "95 percentile",
                                             "success/total",
                                             "total times"])
            if times:
                table.add_row([max(times),
                               sum(times) / len(times),
                               min(times),
                               percentile(times, 0.90),
                               percentile(times, 0.95),
                               float(len(times)) / len(raw),
                               len(raw)])
            else:
                table.add_row(['n/a', 'n/a', 'n/a', 'n/a', 'n/a', 0, len(raw)])
            print(table)

            # NOTE(hughsaunders): ssrs=scenario specific results
            ssrs = []
            for result in raw:
                try:
                    ssrs.append(result['scenario_output']['data'])
                except (KeyError, TypeError):
                    # No SSRs in this result
                    pass
            if ssrs:
                keys = set()
                for ssr in ssrs:
                    keys.update(ssr.keys())

                ssr_table = prettytable.PrettyTable(["Key",
                                                     "max",
                                                     "avg",
                                                     "min",
                                                     "90 pecentile",
                                                     "95 pecentile"])
                for key in keys:
                    values = [float(ssr[key]) for ssr in ssrs if key in ssr]

                    if values:
                        row = [str(key),
                               max(values),
                               sum(values) / len(values),
                               min(values),
                               percentile(values, 0.90),
                               percentile(values, 0.95)]
                    else:
                        row = [str(key)] + ['n/a'] * 5
                    ssr_table.add_row(row)
                print("\nScenario Specific Results\n")
                print(ssr_table)

                for result in raw:
                    if result['scenario_output']['errors']:
                        print(result['scenario_output']['errors'])

        print()
        print("HINTS:")
        print(_("* To plot HTML graphics with this data, run:"))
        print("\trally task plot2html %s --out output.html" % task["uuid"])
        print()
        print(_("* To get raw JSON output of task results, run:"))
        print("\trally task results %s\n" % task["uuid"])

    @cliutils.args('--uuid', type=str, dest='task_id', help='uuid of task')
    @cliutils.args('--pretty', type=str, help=('pretty print (pprint) '
                                               'or json print (json)'))
    @envutils.with_default_task_id
    def results(self, task_id=None, pretty=False):
        """Print raw results of task.

        :param task_id: Task uuid
        :param pretty: Pretty print (pprint) or not (json)
        """
        results = map(lambda x: {"key": x["key"], 'result': x['data']['raw']},
                      db.task_result_get_all_by_uuid(task_id))
        if not pretty or pretty == 'json':
            print(json.dumps(results))
        elif pretty == 'pprint':
            print()
            pprint.pprint(results)
            print()
        else:
            print(_("Wrong value for --pretty=%s") % pretty)

    def list(self, task_list=None):
        """Print a list of all tasks."""
        headers = ['uuid', 'created_at', 'status', 'failed', 'tag']
        task_list = task_list or db.task_list()
        if task_list:
            table = prettytable.PrettyTable(headers)

            for t in task_list:
                r = [t['uuid'],
                     str(t['created_at']),
                     t['status'],
                     t['failed'],
                     t['tag']]
                table.add_row(r)

            print(table)
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
    @cliutils.args('--uuid', type=str, dest='task_id', help='uuid of task')
    @envutils.with_default_task_id
    def delete(self, force, task_id=None):
        """Delete a specific task and related results.

        :param task_id: Task uuid
        :param force: Force delete or not
        """
        api.delete_task(task_id, force=force)


def percentile(N, percent):
    """Find the percentile of a list of values.

    @parameter N - is a list of values.
    @parameter percent - a float value from 0.0 to 1.0.

    @return - the percentile of the values
    """
    if not N:
        return None
    N.sort()
    k = (len(N) - 1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return N[int(k)]
    d0 = N[int(f)] * (c - k)
    d1 = N[int(c)] * (k - f)
    return (d0 + d1)
