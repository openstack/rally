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
from rally.openstack.common.gettextutils import _
from rally.orchestrator import api
from rally import processing


class DeploymentCommands(object):

    @cliutils.args('--filename', type=str, required=True,
                   help='A path to the configuration file of the deployment.')
    @cliutils.args('--name', type=str, required=True,
                   help='A name of the deployment.')
    def create(self, filename, name):
        """Create a new deployment on the basis of configuration file.

        :param filename: a path to the configuration file
        :param name: a name of the deployment
        """
        with open(filename) as f:
            config = json.load(f)
            api.create_deploy(config, name)

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=True,
                   help='UUID of a deployment.')
    def recreate(self, deploy_id):
        """Destroy and create an existing deployment.

        :param deploy_id: a UUID of the deployment
        """
        api.recreate_deploy(deploy_id)

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=True,
                   help='UUID of a deployment.')
    def destroy(self, deploy_id):
        """Destroy the deployment.

        Release resources that are allocated for the deployment. The
        Deployment, related tasks and their results are also deleted.

        :param deploy_id: a UUID of the deployment
        """
        api.destroy_deploy(deploy_id)

    def list(self):
        """Print list of deployments."""
        headers = ['uuid', 'created_at', 'name', 'status']
        table = prettytable.PrettyTable(headers)

        for t in db.deployment_list():
            r = [str(t[column]) for column in headers]
            table.add_row(r)

        print(table)

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=True,
                   help='UUID of a deployment.')
    def config(self, deploy_id):
        """Print on stdout a config of the deployment in JSON format."""
        deploy = db.deployment_get(deploy_id)
        print(json.dumps(deploy['config']))

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=True,
                   help='UUID of a deployment.')
    def endpoint(self, deploy_id):
        """Print endpoint of the deployment."""
        attribute_map = [
            ('auth_url', 'uri'),
            ('user_name', 'admin_username'),
            ('password', 'admin_password'),
            ('tenant_name', 'admin_tenant_name'),
        ]
        headers = [m[0] for m in attribute_map]
        table = prettytable.PrettyTable(headers)
        endpoint = db.deployment_get(deploy_id)['endpoint']
        identity = endpoint.get('identity', {})
        table.add_row([identity.get(m[1], '') for m in attribute_map])
        print(table)


class TaskCommands(object):

    @cliutils.args('--deploy-id', type=str, dest='deploy_id', required=True,
                   help='UUID of the deployment')
    @cliutils.args('--task',
                   help='Path to the file with full configuration of task')
    def start(self, deploy_id, task):
        """Run a benchmark task.

        :param deploy_id: an UUID of a deployment
        :param config: a file with json configration
        """
        with open(task) as task_file:
            config_dict = json.load(task_file)
            api.start_task(deploy_id, config_dict)

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

    @cliutils.args(
        '--task-id', type=str, dest='task_id',
        help=('uuid of task, if --task-id is "last" results of most '
              'recently created task will be displayed.'))
    def detailed(self, task_id):
        """Get detailed information about task
        :param task_id: Task uuid
        Prints detailed infomration of task.
        """

        if task_id == "last":
            task = db.task_get_detailed_last()
            task_id = task.uuid
        else:
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
            if times:
                table.add_row([max(times), sum(times) / len(times), min(times),
                               float(len(times)) / len(raw)])
            else:
                table.add_row(['n/a', 'n/a', 'n/a', 0])
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

    @cliutils.args('--plot-type', type=str, help='plot type; available types: '
                   ', '.join(processing.PLOTS.keys()))
    @cliutils.args('--field-name', type=str, help='field from the task config '
                   'to aggregate the data on: concurrent/times/...')
    @cliutils.args('--task-id', type=str, help='uuid of task')
    def plot(self, plot_type, aggregated_field, task_id):
        if plot_type in processing.PLOTS:
            processing.PLOTS[plot_type](task_id, aggregated_field)
        else:
            print("Plot type '%s' not supported." % plot_type)


def main():
    categories = {
        'task': TaskCommands,
        'deployment': DeploymentCommands,
    }
    cliutils.run(sys.argv, categories)


if __name__ == '__main__':
    main()
