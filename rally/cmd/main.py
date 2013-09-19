# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

    @cliutils.args('--task_id', type=str, help='UUID of task')
    def abort(self, task_id):
        """Force abort task

        :param task_uuid: Task uuid
        """
        api.abort_task(task_id)

    @cliutils.args('--task_id', type=str, help='UUID of task')
    def status(self, task_id):
        """Get status of task

        :param task_uuid: Task uuid
        Returns current status of task
        """
        task = db.task_get_by_uuid(task_id)
        print(_("Task %(task_id)s is %(status)s.")
              % {'task_id': task_id, 'status': task['status']})

    def list(self):
        """Get list of all tasks
        Returns list of active tasks
        """

        headers = ['uuid', 'created_at', 'status', 'failed']
        table = prettytable.PrettyTable(headers)

        for t in db.task_list():
            r = [t['uuid'], str(t['created_at']), t['status'], t['failed']]
            table.add_row(r)

        print(table)


def main():
    categories = {'task': TaskCommands}
    cliutils.run(sys.argv, categories)


if __name__ == '__main__':
    main()
