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

import netaddr
import os
import uuid

from rally.openstack.common.gettextutils import _  # noqa
from rally.openstack.common import log as logging
from rally.serverprovider import provider
from rally import utils

LOG = logging.getLogger(__name__)


class LxcContainer(object):

    def __init__(self, server, config):
        self.path = '/var/lib/lxc/%s/rootfs/'
        self.host = server
        self.config = {'network_bridge': 'br0'}
        self.config.update(config)
        self.server = provider.Server('', self.config['ip'].split('/')[0],
                                      'root', '')

    def prepare_host(self):
        script = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                              'lxc', 'lxc-install.sh'))
        self.host.ssh.execute_script(script)

    def configure(self):
        path = self.path % self.config['name']
        configure_script = os.path.join(os.path.dirname(__file__),
                                        'lxc',
                                        'configure_container.sh')
        self.host.ssh.upload(configure_script, '/tmp/.rally_cont_conf.sh')
        ip = netaddr.IPNetwork(self.config['ip'])
        netmask = str(ip.netmask)
        ip = str(ip.ip)
        self.host.ssh.execute('/bin/sh', '/tmp/.rally_cont_conf.sh', path,
                              ip, netmask, self.config['gateway'],
                              self.config['nameserver'])

    def create(self, distribution):
        self.host.ssh.execute('lxc-create', '-B', 'btrfs',
                              '-n', self.config['name'],
                              '-t', distribution)
        self.configure()

    def clone(self, source):
        self.host.ssh.execute('lxc-clone', '--snapshot', '-o', source, '-n',
                              self.config['name'])
        self.configure()

    def start(self):
        self.host.ssh.execute('lxc-start', '-d', '-n', self.config['name'])

    def stop(self):
        self.host.ssh.execute('lxc-stop', '-n', self.config['name'])

    def destroy(self):
        self.host.ssh.execute('lxc-destroy', '-n', self.config['name'])


class LxcProvider(provider.ProviderFactory):
    """Provide lxc container(s) on given host.

    Sample configuration:
    {
        'name': 'LxcProvider',
        'distribution': 'ubuntu',
        'start_ip_address': '10.0.0.10/24',
        'containers_per_host': 32,
        'container_config': {
            'network_bridge': 'br0',
            'nameserver': '10.0.0.1',
            'gateway': '10.0.0.1',
        },
        'host_provider': {
            'name': 'DummyProvider',
            'credentials': ['root@host.net']
        }
    }

    """

    def __init__(self, deployment, config):
        super(LxcProvider, self).__init__(deployment, config)
        self.containers = []

    def _next_ip(self):
        self.ip += 1
        return '%s/%d' % (self.ip, self.network.prefixlen)

    @utils.log_deploy_wrapper(LOG.info, _("Create containers on host"))
    def create_vms(self):
        self.host_provider = provider.ProviderFactory.get_provider(
            self.config['host_provider'], self.deployment)
        self.network = netaddr.IPNetwork(self.config['start_ip_address'])
        self.ip = self.network.ip - 1
        config = self.config['container_config']
        first = str(uuid.uuid4())
        for server in self.host_provider.create_vms():
            config.update({'ip': self._next_ip(), 'name': first})
            first_container = LxcContainer(server, config)
            first_container.prepare_host()
            first_container.create(self.config['distribution'])
            self.containers.append(first_container)
            for i in range(1, self.config['containers_per_host']):
                config.update({'ip': self._next_ip(),
                               'name': '%s-%d' % (first, i)})
                container = LxcContainer(server, config)
                container.clone(first)
                container.start()
                self.containers.append(container)
            first_container.start()
        for container in self.containers:
            container.server.ssh.wait()
        return [c.server for c in self.containers]

    @utils.log_deploy_wrapper(LOG.info, _("Destroy host(s)"))
    def destroy_vms(self):
        for c in self.containers:
            c.stop()
        self.host_provider.destroy_vms()
