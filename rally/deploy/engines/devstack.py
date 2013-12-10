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
import tempfile

from rally.deploy import engine
from rally.openstack.common.gettextutils import _  # noqa
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
                "credentials": ["root@10.2.0.8"]
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
        server.ssh.execute_script(script_path)

    @utils.log_deploy_wrapper(LOG.info, _("Deploy devstack"))
    def deploy(self):
        self.servers = self._vm_provider.create_vms()
        for server in self.servers:
            self.prepare_server(server)
            devstack_server = provider.Server(server.uuid, server.ip,
                                              DEVSTACK_USER, server.key)
            self.configure_devstack(devstack_server)
            self.start_devstack(devstack_server)

        return {
            'identity': {
                'url': 'http://%s/' % self.servers[0].ip,
                'uri': 'http://%s:5000/v2.0/' % self.servers[0].ip,
                'admin_username': 'admin',
                'admin_password': self.localrc['ADMIN_PASSWORD'],
                'admin_tenant_name': 'admin',
            },
            'compute': {
                'controller_nodes': self.servers[0].ip,
                'compute_nodes': self.servers[0].ip,
                'controller_node_ssh_user': self.servers[0].user,
            }
        }

    def cleanup(self):
        self._vm_provider.destroy_vms()

    @utils.log_deploy_wrapper(LOG.info, _("Configure devstack"))
    def configure_devstack(self, server):
        devstack_repo = self.config.get('devstack_repo', DEVSTACK_REPO)
        server.ssh.execute('git', 'clone', devstack_repo)
        fd, config_path = tempfile.mkstemp()
        config_file = open(config_path, "w")
        for k, v in self.localrc.iteritems():
            config_file.write('%s=%s\n' % (k, v))
        config_file.close()
        os.close(fd)
        server.ssh.upload(config_path, "~/devstack/localrc")
        os.unlink(config_path)
        return True

    @utils.log_deploy_wrapper(LOG.info, _("Run devstack"))
    def start_devstack(self, server):
        server.ssh.execute('~/devstack/stack.sh')
        return True
