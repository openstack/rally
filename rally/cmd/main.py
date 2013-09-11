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

from rally.cmd import cliutils
from rally import db
from rally import exceptions
from rally.openstack.common.gettextutils import _   # noqa
from rally.orchestrator import api


class TaskCommands(object):

    @cliutils.args('--config', help='Full configuration of ')
    def start(self, config):
        """Run Benchmark task
        :param config: File with json configration
        Returns task_uuid
        """
        try:
            api.start_task(json.load(open(config)))
        except Exception as e:
            print(_("Something went wrong %s") % e)

    @cliutils.args('--task_id', type=str, help='UUID of task')
    def abort(self, task_id):
        """Force abort task

        :param task_uuid: Task uuid
        """
        try:
            api.abort_task(task_id)
        except Exception as e:
            print(_("Something went wrong %s") % e)

    @cliutils.args('--task_id', type=str, help='UUID of task')
    def status(self, task_id):
        """Get status of task

        :param task_uuid: Task uuid
        Returns current status of task
        """
        try:
            task = db.task_get_by_uuid(task_id)
            print(_("Task %(task_id)s is %(status)s.")
                  % {'task_id': task_id, 'status': task['status']})
        except exceptions.TaskNotFound as e:
            print(e)
        except Exception as e:
            print(_("Something went wrong %s") % e)

    def list(self):
        """Get list of all tasks
        Returns list of active tasks
        """
        print(_("Not implemented"))


def main(argv):
    categories = {'task': TaskCommands}
    cliutils.run(argv, categories)


if __name__ == '__main__':
    main(sys.argv)
