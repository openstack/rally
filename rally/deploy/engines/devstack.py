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
from rally import sshutils

LOG = logging.getLogger(__name__)
DEVSTACK_REPO = 'https://github.com/openstack-dev/devstack.git'
DEVSTACK_USER = 'rally'


class DevstackEngine(engine.EngineFactory):
    '''Deploys Devstack cloud.
    deploy config example:
        "deploy": {
            "name": "DevstackEngine",
            "localrc": {
                "ADMIN_PASSWORD": "secret"
            },
            "devstack_repo": "git://example.com/devstack/",
            "provider": {
                "name": "%name%",
                ...
            }
        },
    '''

    def __init__(self, task, config):
        self.task = task
        self._config = config
        self._vms = []
        provider_config = config['provider']
        self._vm_provider = provider.ProviderFactory.get_provider(
            provider_config)
        self.localrc = {
            'DATABASE_PASSWORD': 'rally',
            'RABBIT_PASSWORD': 'rally',
            'SERVICE_TOKEN': 'rally',
            'SERVICE_PASSWORD': 'rally',
            'ADMIN_PASSWORD': 'admin',
            'RECLONE': 'yes',
            'SYSLOG': 'yes',
        }
        if 'localrc' in config:
            self.localrc.update(config['localrc'])

    def install_devstack(self, vm):
        devstack_repo = self._config.get('devstack_repo', DEVSTACK_REPO)
        script_path = os.path.join(os.path.dirname(__file__),
                                   'devstack', 'install.sh')
        sshutils.execute_script(vm.user, vm.ip, script_path)
        sshutils.execute_command(DEVSTACK_USER, vm.ip,
                                 ['git', 'clone', devstack_repo])

    def deploy(self):
        self._vms = self._vm_provider.create_vms()
        for vm in self._vms:
            self.install_devstack(vm)
            self.configure_devstack(vm)
            self.start_devstack(vm)
        self._vms.append(vm)

        identity_host = self._vms[0].ip

        return {
            'identity': {
                'url': 'http://%s/' % identity_host,
                'uri': 'http://%s:5000/v2.0/' % identity_host,
                'admin_username': 'admin',
                'admin_password': self.localrc['ADMIN_PASSWORD'],
                'admin_tenant_name': 'admin',
            },
            'compute': {
                'controller_nodes': self._vms[0].ip,
                'compute_nodes': self._vms[0].ip,
                'controller_node_ssh_user': self._vms[0].user,
            }
        }

    def cleanup(self):
        self._vm_provider.destroy_vms()

    def configure_devstack(self, vm):
        task_uuid = self.task['uuid']
        LOG.info(_('Task %(uuid)s: Patching DevStack for VM %(vm_ip)s...') %
                 {'uuid': task_uuid, 'vm_ip': vm.ip})
        fd, config_path = tempfile.mkstemp()
        config_file = open(config_path, "w")
        for k, v in self.localrc.iteritems():
            config_file.write('%s=%s\n' % (k, v))
        config_file.close()
        os.close(fd)
        sshutils.upload_file(DEVSTACK_USER, vm.ip, config_path,
                             "~/devstack/localrc")
        os.unlink(config_path)
        LOG.info(_('Task %(uuid)s: DevStack for VM %(vm_ip)s successfully '
                   'patched.') % {'uuid': task_uuid, 'vm_ip': vm.ip})
        return True

    def start_devstack(self, vm):
        task_uuid = self.task['uuid']
        LOG.info(_('Task %(uuid)s: Starting DevStack for VM %(vm_ip)s...') %
                 {'uuid': task_uuid, 'vm_ip': vm.ip})
        sshutils.execute_command(DEVSTACK_USER, vm.ip, ['~/devstack/stack.sh'])
        LOG.info(_('Task %(uuid)s: DevStack for VM %(vm_ip)s successfully '
                   'started.') % {'uuid': task_uuid, 'vm_ip': vm.ip})
        return True
