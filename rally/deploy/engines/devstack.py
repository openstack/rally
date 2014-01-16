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

import os
import StringIO

from rally import consts
from rally.deploy import engine
from rally import objects
from rally.openstack.common.gettextutils import _
from rally.openstack.common import log as logging
from rally.serverprovider import provider
from rally import utils


LOG = logging.getLogger(__name__)
DEVSTACK_REPO = 'https://github.com/openstack-dev/devstack.git'
DEVSTACK_USER = 'rally'


class DevstackEngine(engine.EngineFactory):
    """Deploy Devstack cloud.

    Sample of a configuration:
        {
            "name": "DevstackEngine",
            "devstack_repo": "git://example.com/devstack/",
            "localrc": {
                "ADMIN_PASSWORD": "secret"
            },
            "provider": {
                "name": "DummyProvider",
                "credentials": [{'user': 'root', 'host': '10.2.0.8'}]
            }
        }
    """

    CONFIG_SCHEMA = {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'provider': {'type': 'object'},
            'localrc': {'type': 'object'},
            'devstack_repo': {'type': 'string'},
        },
        'required': ['name', 'provider']
    }

    def __init__(self, deployment):
        super(DevstackEngine, self).__init__(deployment)
        self._vms = []
        self._vm_provider = provider.ProviderFactory.get_provider(
            self.config['provider'], deployment)
        self.localrc = {
            'DATABASE_PASSWORD': 'rally',
            'RABBIT_PASSWORD': 'rally',
            'SERVICE_TOKEN': 'rally',
            'SERVICE_PASSWORD': 'rally',
            'ADMIN_PASSWORD': 'admin',
            'RECLONE': 'yes',
            'SYSLOG': 'yes',
        }
        if 'localrc' in self.config:
            self.localrc.update(self.config['localrc'])

    @utils.log_deploy_wrapper(LOG.info, _("Prepare server for devstack"))
    def prepare_server(self, server):
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                   'devstack', 'install.sh'))
        server.ssh.run('/bin/sh -e', stdin=open(script_path, 'rb'))

    @utils.log_deploy_wrapper(LOG.info, _("Deploy devstack"))
    def deploy(self):
        self.servers = self._vm_provider.create_servers()
        for server in self.servers:
            self.prepare_server(server)
            credentials = server.get_credentials()
            credentials['user'] = DEVSTACK_USER
            devstack_server = provider.Server.from_credentials(credentials)
            self.configure_devstack(devstack_server)
            self.start_devstack(devstack_server)

        admin_endpoint = objects.Endpoint('http://%s:5000/v2.0/' %
                                          self.servers[0].host, 'admin',
                                          self.localrc['ADMIN_PASSWORD'],
                                          'admin',
                                          consts.EndpointPermission.ADMIN)
        return [admin_endpoint]

    def cleanup(self):
        self._vm_provider.destroy_servers()

    @utils.log_deploy_wrapper(LOG.info, _("Configure devstack"))
    def configure_devstack(self, server):
        devstack_repo = self.config.get('devstack_repo', DEVSTACK_REPO)
        server.ssh.run('git clone %s' % devstack_repo)
        localrc = StringIO.StringIO()
        for k, v in self.localrc.iteritems():
            localrc.write('%s=%s\n' % (k, v))
        localrc.seek(0)
        server.ssh.run("cat > ~/devstack/localrc", stdin=localrc)
        return True

    @utils.log_deploy_wrapper(LOG.info, _("Run devstack"))
    def start_devstack(self, server):
        server.ssh.run('~/devstack/stack.sh')
        return True
