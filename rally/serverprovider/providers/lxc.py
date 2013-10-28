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
import tempfile
import uuid

from rally.openstack.common.gettextutils import _  # noqa
from rally.openstack.common import log as logging
from rally.serverprovider import provider
from rally import utils

LOG = logging.getLogger(__name__)


class LxcContainer(object):
    path = '/var/lib/lxc/%s/'

    def __init__(self, server, config):
        self.server = server
        self.config = {'network_bridge': 'br0', 'dhcp': ''}
        self.config.update(config)
        if self.config['ip'] == 'dhcp':
            self.config['dhcp'] = '#'

    def ssh(self, *args):
        return self.server.ssh.execute(*args)

    def configure(self):
        template_filename = os.path.join(os.path.dirname(__file__),
                                         'lxc',
                                         'container_config_template')
        template = open(template_filename, 'r').read()
        fd, config_path = tempfile.mkstemp()
        with os.fdopen(fd, 'w') as config_file:
            config_file.write(template.format(**self.config))
        self.server.ssh.upload(config_path,
                               self.path % self.config['name'] +
                               'config')
        self.ssh('mkdir', self.path % self.config['name'] + 'rootfs/root/.ssh')
        self.ssh('cp', '~/.ssh/authorized_keys',
                 self.path % self.config['name'] + 'rootfs/root/.ssh/')
        os.unlink(config_path)

    def create(self, distribution):
        self.ssh('lxc-create', '-n', self.config['name'], '-t', distribution)

    def clone(self, source):
        self.ssh('lxc-clone', '-o', source, '-n', self.config['name'])

    def start(self):
        self.ssh('lxc-start', '-d', '-n', self.config['name'])

    def stop(self):
        self.ssh('lxc-stop', '-n', self.config['name'])

    def destroy(self):
        self.ssh('lxc-destroy', '-n', self.config['name'])


def ipgen(ip, prefixlen):
    if ip != 'dhcp':
        net = netaddr.IPNetwork('%s/%d' % (ip, prefixlen))
        ip = netaddr.IPAddress(ip)
        while ip in net:
            yield '%s/%d' % (ip, prefixlen)
            ip += 1
    else:
        while True:
            yield ip


class LxcProvider(provider.ProviderFactory):
    """Provide lxc container(s) on given host.

    Sample configuration:
    {
        'name': 'LxcProvider',
        'network_bridge': 'br0',
        'distribution': 'ubuntu',
        'ipv4_start_address': '10.0.0.1',
        'ipv4_prefix_len': '24',
        'host_provider': {
            'name': 'DummyProvider',
            'credentials': ['root@host.net']
        }
    }

    """

    def __init__(self, config):
        self.config = config
        self.containers = []

    @utils.log_task_wrapper(LOG.info, _("Install lxc on host"))
    def lxc_install(self):
        host_provider = provider.ProviderFactory.get_provider(
            self.config['host_provider'], self.task)
        self.connections = host_provider.create_vms()
        script = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                              'lxc', 'lxc-install.sh'))
        for conn in self.connections:
            conn.ssh.execute_script(script)

    @utils.log_task_wrapper(LOG.info, _("Create lxc containers"))
    def create_vms(self):
        self.lxc_install()
        ip = ipgen(self.config.get('ipv4_start_address', 'dhcp'),
                   self.config.get('ipv4_prefixlen', None))
        for conn in self.connections:
            name = str(uuid.uuid4())
            base_container = LxcContainer(conn, {'name': name,
                                                 'ip': ip.next()})
            base_container.create(self.config.get('distribution', 'ubuntu'))
            self.containers.append(base_container)
            for i in range(self.config['containers_per_host'] - 1):
                name = str(uuid.uuid4())
                container = LxcContainer(conn, {'name': name,
                                                'ip': ip.next()})
                container.clone(base_container.config['name'])
                self.containers.append(container)
        for container in self.containers:
            container.configure()
            container.start()

        servers = []
        for c in self.containers:
            server = provider.ServerDTO(self.config['name'],
                                        c.config['ip'].split('/')[0],
                                        'root', None, None)
            server.ssh.wait()
            servers.append(server)
        return servers

    @utils.log_task_wrapper(LOG.info, _("Destroy lxc containers"))
    def destroy_vms(self):
        for c in self.containers:
            c.stop()
            c.destroy()
