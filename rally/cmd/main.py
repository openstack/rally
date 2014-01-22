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

import os
import prettytable

from rally.cmd import cliutils
from rally.cmd import envutils
from rally import db
from rally import exceptions
from rally import fileutils
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
            deployment = api.create_deploy(config, name)
            self.list(deployment_list=[deployment])

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=False,
                   help='UUID of a deployment.')
    def recreate(self, deploy_id=None):
        """Destroy and create an existing deployment.

        :param deploy_id: a UUID of the deployment
        """
        deploy_id = deploy_id or envutils.default_deployment_id()
        api.recreate_deploy(deploy_id)

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=False,
                   help='UUID of a deployment.')
    def destroy(self, deploy_id=None):
        """Destroy the deployment.

        Release resources that are allocated for the deployment. The
        Deployment, related tasks and their results are also deleted.

        :param deploy_id: a UUID of the deployment
        """
        deploy_id = deploy_id or envutils.default_deployment_id()
        api.destroy_deploy(deploy_id)

    def list(self, deployment_list=None):
        """Print list of deployments."""
        headers = ['uuid', 'created_at', 'name', 'status']
        table = prettytable.PrettyTable(headers)

        deployment_list = deployment_list or db.deployment_list()
        for t in deployment_list:
            r = [str(t[column]) for column in headers]
            table.add_row(r)

        print(table)

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=False,
                   help='UUID of a deployment.')
    def config(self, deploy_id=None):
        """Print on stdout a config of the deployment in JSON format.

        :param deploy_id: a UUID of the deployment
        """
        deploy_id = deploy_id or envutils.default_deployment_id()
        deploy = db.deployment_get(deploy_id)
        print(json.dumps(deploy['config']))

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=False,
                   help='UUID of a deployment.')
    def endpoint(self, deploy_id=None):
        """Print endpoint of the deployment.

        :param deploy_id: a UUID of the deployment
        """
        deploy_id = deploy_id or envutils.default_deployment_id()
        headers = ['auth_url', 'username', 'password', 'tenant_name']
        table = prettytable.PrettyTable(headers)
        endpoint = db.deployment_get(deploy_id)['endpoint']
        table.add_row([endpoint.get(m, '') for m in headers])
        print(table)


class TaskCommands(object):

    @cliutils.args('--deploy-id', type=str, dest='deploy_id', required=False,
                   help='UUID of the deployment')
    @cliutils.args('--task',
                   help='Path to the file with full configuration of task')
    def start(self, task, deploy_id=None):
        """Run a benchmark task.

        :param task: a file with json configration
        :param deploy_id: a UUID of a deployment
        """
        deploy_id = deploy_id or envutils.default_deployment_id()
        with open(task) as task_file:
            config_dict = json.load(task_file)
            try:
                task = api.create_task(deploy_id)
                self.list(task_list=[task])
                api.start_task(deploy_id, config_dict, task=task)
                self.detailed(task_id=task['uuid'])
            except exceptions.InvalidArgumentsException:
                print(_("Reason: %s") % sys.exc_info()[1])

    @cliutils.args('--task-id', type=str, dest='task_id', help='UUID of task')
    def abort(self, task_id):
        """Force abort task

        :param task_id: Task uuid
        """
        api.abort_task(task_id)

    @cliutils.args('--task-id', type=str, dest='task_id', help='UUID of task')
    def status(self, task_id):
        """Get status of task

        :param task_id: Task uuid
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
        Prints detailed information of task.
        """

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

            table = prettytable.PrettyTable(["max (sec)", "avg (sec)",
                                             "min (sec)", "success/total",
                                             "total times"])
            if times:
                table.add_row([max(times), sum(times) / len(times), min(times),
                               float(len(times)) / len(raw), len(raw)])
            else:
                table.add_row(['n/a', 'n/a', 'n/a', 0, len(raw)])
            print(table)

            #NOTE(hughsaunders): ssrs=scenario specific results
            ssrs = []
            for result in raw:
                try:
                    ssrs.append(result['scenario_output']['data'])
                except (KeyError, TypeError):
                    # No SSRs in this result
                    pass
            if ssrs:
                sys.stdout.flush()
                keys = set()
                for ssr in ssrs:
                    keys.update(ssr.keys())

                ssr_table = prettytable.PrettyTable(
                    ["Key", "max", "avg", "min"])
                for key in keys:
                    values = [float(ssr[key]) for ssr in ssrs if key in ssr]

                    if values:
                        row = [str(key),
                               max(values),
                               sum(values) / len(values),
                               min(values)]
                    else:
                        row = [str(key)] + ['n/a'] * 3
                    ssr_table.add_row(row)
                print("\nScenario Specific Results\n")
                print(ssr_table)

                for result in raw:
                    if result['scenario_output']['errors']:
                        print(result['scenario_output']['errors'])

    @cliutils.args('--task-id', type=str, dest='task_id', help='uuid of task')
    @cliutils.args('--pretty', type=str, help=('pretty print (pprint) '
                                               'or json print (json)'))
    def results(self, task_id, pretty=False):
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

        headers = ['uuid', 'created_at', 'status', 'failed']
        table = prettytable.PrettyTable(headers)

        task_list = task_list or db.task_list()

        for t in task_list:
            r = [t['uuid'], str(t['created_at']), t['status'], t['failed']]
            table.add_row(r)

        print(table)

    @cliutils.args('--task-id', type=str, dest='task_id', help='uuid of task')
    @cliutils.args('--force', action='store_true', help='force delete')
    def delete(self, task_id, force):
        """Delete a specific task and related results.

        :param task_id: Task uuid
        :param force: Force delete or not
        """
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


class UseCommands(object):

    def deployment(self, deploy_id):
        """Set the RALLY_DEPLOYMENT env var to be used by all CLI commands

        :param deploy_id: a UUID of a deployment
        """
        print('Using deployment : %s' % deploy_id)
        if not os.path.exists(os.path.expanduser('~/.rally/')):
            os.makedirs(os.path.expanduser('~/.rally/'))
        expanded_path = os.path.expanduser('~/.rally/deployment')
        fileutils.update_env_file(expanded_path, 'RALLY_DEPLOYMENT', deploy_id)


def deprecated():
    print("\n\n---\n\nopenstack-rally and openstack-rally-manage are "
          "deprecated, please use rally and rally-manage\n\n---\n\n")
    main()


def main():
    categories = {
        'task': TaskCommands,
        'deployment': DeploymentCommands,
        'use': UseCommands,
    }
    cliutils.run(sys.argv, categories)


if __name__ == '__main__':
    main()
