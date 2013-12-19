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
import re
import tempfile
import time

from rally import exceptions
from rally.openstack.common.gettextutils import _
from rally.openstack.common import log as logging
from rally.serverprovider import provider
from rally import utils

LOG = logging.getLogger(__name__)

INET_ADDR_RE = re.compile(r' *inet ((\d+\.){3}\d+)\/\d+ .*')


def _get_script_path(filename):
    return os.path.abspath(os.path.join(os.path.dirname(__file__),
                           'lxc', filename))


def _write_script_from_template(template_filename, **kwargs):
    template = open(_get_script_path(template_filename)).read()
    new_file = tempfile.NamedTemporaryFile(delete=False)
    new_file.write(template.format(**kwargs))
    new_file.close()
    return new_file.name


class LxcHost(object):
    """Represent lxc enabled host."""

    def __init__(self, server, config):
        self.config = config
        if 'network' in config:
            self.network = netaddr.IPNetwork(config['network'])
        else:
            self.network = None
        self.server = server
        self.containers = []
        self.path = '/var/lib/lxc/'

    def _get_server_with_ip(self, ip):
        credentials = self.server.get_credentials()
        credentials['host'] = ip
        return provider.Server.from_credentials(credentials)

    @property
    def backingstore(self):
        if not hasattr(self, '_backingstore'):
            try:
                self.server.ssh.execute('df -t btrfs %s' % self.path)
                self._backingstore = 'btrfs'
            except exceptions.SSHError:
                self._backingstore = 'dir'
        return self._backingstore

    def prepare(self):
        if self.network:
            dhcp_start = str(self.network.network + 2)
            dhcp_end = str(self.network.network + self.network.size - 2)
            dhcp_range = ','.join([dhcp_start, dhcp_end])
            values = {
                'USE_LXC_BRIDGE': "true",
                'LXC_BRIDGE': self.config.get('lxc_bridge', 'lxcbr0'),
                'LXC_ADDR': self.network.network + 1,
                'LXC_NETMASK': self.network.netmask,
                'LXC_NETWORK': self.network,
                'LXC_DHCP_RANGE': dhcp_range,
                'LXC_DHCP_MAX': self.network.size - 3,
            }
            config = tempfile.NamedTemporaryFile(delete=False)
            for name, value in values.iteritems():
                config.write('%(name)s="%(value)s"\n' % {'name': name,
                                                         'value': value})
            config.close()
            self.server.ssh.upload(config.name, '/tmp/.lxc_default')
            os.unlink(config.name)

        script = _get_script_path('lxc-install.sh')
        self.server.ssh.execute_script(script)
        self.create_local_tunnels()
        self.create_remote_tunnels()

    def create_local_tunnels(self):
        """Create tunel on lxc host side."""
        for tunnel_to in self.config['tunnel_to']:
            script = _write_script_from_template('tunnel-local.sh',
                                                 net=self.network,
                                                 local=self.server.host,
                                                 remote=tunnel_to)
            self.server.ssh.execute_script(script)
            os.unlink(script)

    def create_remote_tunnels(self):
        """Create tunel on remote side."""
        for tunnel_to in self.config['tunnel_to']:
            script = _write_script_from_template('tunnel-remote.sh',
                                                 net=self.network,
                                                 local=tunnel_to,
                                                 remote=self.server.host)
            server = self._get_server_with_ip(tunnel_to)
            server.ssh.execute_script(script)
            os.unlink(script)

    def delete_tunnels(self):
        for tunnel_to in self.config['tunnel_to']:
            remote_server = self._get_server_with_ip(tunnel_to)
            remote_server.ssh.execute('ip tun del t%s' % self.network.ip)
            self.server.ssh.execute('ip tun del t%s' % tunnel_to)

    def get_ip(self, name):
        """Get container's ip by name."""

        cmd = 'lxc-attach -n %s ip addr list dev eth0' % name
        for attempt in range(1, 16):
            stdout = self.server.ssh.execute(cmd, get_stdout=True)[0]
            for line in stdout.splitlines():
                m = INET_ADDR_RE.match(line)
                if m:
                    return m.group(1)
            time.sleep(attempt)
        msg = _('Timeout waiting for ip address of container "%s"') % name
        raise exceptions.TimeoutException(msg)

    def create_container(self, name, distribution):
        self.server.ssh.execute('lxc-create', '-B', self.backingstore,
                                '-n', name,
                                '-t', distribution)
        self.configure_container(name)
        self.containers.append(name)

    def create_clone(self, name, source):
        cmd = ['lxc-clone']

        if self.backingstore == 'btrfs':
            cmd.append('--snapshot')
        cmd.extend(['-o', source, '-n', name])
        self.server.ssh.execute(*cmd)
        self.configure_container(name)
        self.containers.append(name)

    def configure_container(self, name):
        path = os.path.join(self.path, name, 'rootfs')
        configure_script = _get_script_path('configure_container.sh')
        self.server.ssh.upload(configure_script, '/tmp/.rally_cont_conf.sh')
        self.server.ssh.execute('/bin/sh', '/tmp/.rally_cont_conf.sh', path)

    def start_containers(self):
        for name in self.containers:
            self.server.ssh.execute('lxc-start -d -n %s' % name)

    def stop_containers(self):
        for name in self.containers:
            self.server.ssh.execute('lxc-stop -n %s' % name)

    def destroy_containers(self):
        for name in self.containers:
            self.server.ssh.execute('lxc-stop -n %s' % name)
            self.server.ssh.execute('lxc-destroy -n %s' % name)

    def get_server_object(self, name, wait=True):
        """Create Server object for container."""
        server = self._get_server_with_ip(self.get_ip(name))
        if wait:
            server.ssh.wait(timeout=300)
        return server

    def get_server_objects(self, wait=True):
        """Generate Server objects from all containers."""
        for name in self.containers:
            yield self.get_server_object(name, wait)


class LxcProvider(provider.ProviderFactory):
    """Provide lxc container(s) on given host.

    Sample configuration:
    {
        "name": "LxcProvider",
        "distribution": "ubuntu",
        "start_lxc_network": "10.1.1.0/24",
        "containers_per_host": 32,
        "tunnel_to": ["10.10.10.10"],
        "container_name_prefix": "rally-multinode-02",
        "host_provider": {
            "name": "DummyProvider",
            "credentials": [{"user": "root", "host": "host.net"}]
        }
    }

    """

    CONFIG_SCHEMA = {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'distribution': {'type': 'string'},
            'start_lxc_network': {'type': 'string',
                                  'pattern': '^(\d+\.){3}\d+\/\d+$'},
            'containers_per_host': {'type': 'integer'},
            'tunnel_to': {'type': 'array',
                          'elements': {'type': 'string',
                                       'pattern': '^(\d+\.){3}\d+$'}},
            'container_name_prefix': {'type': 'string'},
            'host_provider': {'type': 'object',
                              'properties': {'name': {'type': 'string'}}},
        },
        'required': ['name', 'containers_per_host',
                     'container_name_prefix', 'host_provider'],

    }

    def validate(self):
        super(LxcProvider, self).validate()
        if 'start_lxc_network' not in self.config:
            return
        lxc_net = netaddr.IPNetwork(self.config['start_lxc_network'])
        num_containers = self.config['containers_per_host']
        if lxc_net.size - 3 < num_containers:
            message = _("Network size is not enough for %d hosts.")
            raise exceptions.InvalidConfigException(message % num_containers)

    @utils.log_deploy_wrapper(LOG.info, _("Create containers on host"))
    def create_servers(self):
        host_provider = provider.ProviderFactory.get_provider(
            self.config['host_provider'], self.deployment)
        name_prefix = self.config['container_name_prefix']
        hosts = []
        if 'start_lxc_network' in self.config:
            network = netaddr.IPNetwork(self.config['start_lxc_network'])
        else:
            network = None
        distribution = self.config.get('distribution', 'ubuntu')

        for server in host_provider.create_servers():
            config = {'tunnel_to': self.config.get('tunnel_to', [])}
            if network:
                config['network'] = str(network)
            host = LxcHost(server, config)
            host.prepare()
            ip = str(network.ip).replace('.', '-') if network else '0'
            first_name = '%s-000-%s' % (name_prefix, ip)
            host.create_container(first_name, distribution)
            for i in range(1, self.config.get('containers_per_host', 1)):
                name = '%s-%03d-%s' % (name_prefix, i, ip)
                host.create_clone(name, first_name)
            host.start_containers()
            hosts.append(host)

            if network:
                network += 1

        servers = []

        for host in hosts:
            containers = []
            for server in host.get_server_objects():
                containers.append(server.get_credentials())
                servers.append(server)
            info = {'host': host.server.get_credentials(),
                    'config': host.config,
                    'container_names': host.containers}
            self.resources.create(info)
        return servers

    @utils.log_deploy_wrapper(LOG.info, _("Destroy host(s)"))
    def destroy_servers(self):
        for resource in self.resources.get_all():
            server = provider.Server.from_credentials(resource['info']['host'])
            lxc_host = LxcHost(server, resource['info']['config'])
            lxc_host.containers = resource['info']['container_names']
            lxc_host.destroy_containers()
            lxc_host.delete_tunnels()
            self.resources.delete(resource['id'])
