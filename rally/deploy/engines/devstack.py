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

import jinja2
import os
import subprocess
import tempfile

from rally.deploy import engine
from rally.serverprovider import provider


class DevstackDeployment(engine.EngineFactory):
    '''Deploys Devstack cloud.
    deploy config example:
        "deploy": {
            "template_user": "ubuntu",  # vm user to launch devstack
            "vm_provider": {
                "name": "%name%",
                ...
            }
            "vm_count": 1,
        },
    '''

    def __init__(self, config):
        self._config = config
        self._vms = []
        provider_config = config['vm_provider']
        self._vm_provider = provider.ProviderFactory.get_provider(
            provider_config['name'], provider_config)

    def deploy(self):
        self._vms = self._vm_provider.create_vms(
            amount=int(self._config['vm_count']))
        for vm in self._vms:
            self.patch_devstack(vm)
            self.start_devstack(vm)
            self._vms.append(vm)

        identity_host = {'host': self._vms[0]['ip']}

        return {
            'identity': {
                'url': 'http://%s/' % identity_host,
                'uri': 'http://%s:5000/v2.0/' % identity_host,
                'admin_username': 'admin',
                'admin_password': self._config['services']['admin_password'],
                'admin_tenant_name': 'service',
            }
        }

    def cleanup(self):
        for vm in self._vms:
            self._vm_provider.destroy_vm(vm)

    def patch_devstack(self, vm):
        template_path = os.path.dirname(__file__) + '/devstack/'
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_path))

        config_file, config_path = tempfile.mkstemp()
        config_file = os.fdopen(config_file, 'w')

        config_template = env.get_template('localrc.tpl')
        config_file.write(config_template.render(self._config['services']))
        config_file.close()

        cmd = 'scp %(opts)s %(config)s %(usr)s@%(host)s:~/devstack/localrc' % {
            'opts': '-o StrictHostKeyChecking=no',
            'config': config_path,
            'usr': self._config['template_user'],
            'host': vm['ip']
        }
        subprocess.check_call(cmd, shell=True)

        os.unlink(config_path)
        return True

    def start_devstack(self, vm):
        cmd = 'ssh %(opts)s %(usr)s@%(host)s devstack/stack.sh' % {
            'opts': '-o StrictHostKeyChecking=no',
            'usr': self._config['template_user'],
            'host': vm['ip']
        }
        subprocess.check_call(cmd, shell=True)
        return True
