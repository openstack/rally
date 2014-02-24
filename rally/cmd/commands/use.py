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

""" Rally command: use """

import os

from rally import db
from rally import fileutils


class UseCommands(object):

    def _update_openrc_deployment_file(self, deploy_id):
        openrc_path = os.path.expanduser('~/.rally/openrc-%s' % deploy_id)
        endpoints = db.deployment_get(deploy_id)['endpoints']
        # NOTE(msdubov): In case of multiple endpoints write the first one.
        with open(openrc_path, 'w+') as env_file:
            env_file.write('export OS_AUTH_URL=%(auth_url)s\n'
                           'export OS_USERNAME=%(username)s\n'
                           'export OS_PASSWORD=%(password)s\n'
                           'export OS_TENANT_NAME=%(tenant_name)s\n'
                           % endpoints[0])
        expanded_path = os.path.expanduser('~/.rally/openrc')
        if os.path.exists(expanded_path):
            os.remove(expanded_path)
        os.symlink(openrc_path, expanded_path)

    def _update_rally_deployment_file(self, deploy_id):
        expanded_path = os.path.expanduser('~/.rally/deployment')
        fileutils.update_env_file(expanded_path, 'RALLY_DEPLOYMENT', deploy_id)

    def deployment(self, deploy_id):
        """Set the RALLY_DEPLOYMENT env var to be used by all CLI commands

        :param deploy_id: a UUID of a deployment
        """
        print('Using deployment: %s' % deploy_id)
        if not os.path.exists(os.path.expanduser('~/.rally/')):
            os.makedirs(os.path.expanduser('~/.rally/'))
        self._update_rally_deployment_file(deploy_id)
        self._update_openrc_deployment_file(deploy_id)
