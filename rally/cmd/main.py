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

""" CLI interface for Rally. """

from __future__ import print_function

import json
import pprint
import sys

import prettytable

from rally.cmd import cliutils
from rally import db
from rally.openstack.common.gettextutils import _   # noqa
from rally.orchestrator import api


class TaskCommands(object):

    @cliutils.args('--task',
                   help='Path to the file with full configuration of task')
    def start(self, task):
        """Run Benchmark task
        :param config: File with json configration
        Returns task_uuid
        """
        with open(task) as task_file:
            config_dict = json.load(task_file)
            api.start_task(config_dict)

    @cliutils.args('--task-id', type=str, dest='task_id', help='UUID of task')
    def abort(self, task_id):
        """Force abort task

        :param task_uuid: Task uuid
        """
        api.abort_task(task_id)

    @cliutils.args('--task-id', type=str, dest='task_id', help='UUID of task')
    def status(self, task_id):
        """Get status of task

        :param task_uuid: Task uuid
        Returns current status of task
        """
        task = db.task_get(task_id)
        print(_("Task %(task_id)s is %(status)s.")
              % {'task_id': task_id, 'status': task['status']})

    @cliutils.args('--task-id', type=str, dest='task_id', help='uuid of task')
    def detailed(self, task_id):
        """Get detailed information about task
        :param task_id: Task uuid
        Prints detailed infomration of task.
        """
        task = db.task_get_detailed(task_id)

        print()
        print("=" * 80)
        print(_("Task %(task_id)s is %(status)s.")
              % {'task_id': task_id, 'status': task['status']})

        for result in task["results"]:
            key = result["key"]
            print("-" * 80)
            print()
            print("test scenario %s" % key["name"])
            print("args position %s" % key["pos"])
            print("args values:")
            pprint.pprint(key["kw"])

            raw = result["data"]["raw"]
            times = map(lambda x: x['time'],
                        filter(lambda r: not r['error'], raw))

            table = prettytable.PrettyTable(["max", "avg", "min", "ratio"])
            table.add_row([max(times), sum(times) / len(times), min(times),
                           float(len(times)) / len(raw)])
            print(table)

    @cliutils.args('--task-id', type=str, dest='task_id', help='uuid of task')
    @cliutils.args('--pretty', type=str, help='uuid of task')
    def results(self, task_id, pretty=False):
        """Print raw results of task."""
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

    def list(self):
        """Print a list of all tasks."""

        headers = ['uuid', 'created_at', 'status', 'failed']
        table = prettytable.PrettyTable(headers)

        for t in db.task_list():
            r = [t['uuid'], str(t['created_at']), t['status'], t['failed']]
            table.add_row(r)

        print(table)

    @cliutils.args('--task-id', type=str, dest='task_id', help='uuid of task')
    @cliutils.args('--force', action='store_true', help='force delete')
    def delete(self, task_id, force):
        """Delete a specific task and related results."""
        api.delete_task(task_id, force=force)


def main():
    categories = {'task': TaskCommands}
    cliutils.run(sys.argv, categories)


if __name__ == '__main__':
    main()
