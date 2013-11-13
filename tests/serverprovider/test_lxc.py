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

import contextlib
import mock

from rally.openstack.common import test
from rally.serverprovider.providers import lxc


class LxcContainerTestCase(test.BaseTestCase):

    def setUp(self):
        super(LxcContainerTestCase, self).setUp()
        self.server = mock.MagicMock()
        config = {'ip': '1.2.3.4/24',
                  'gateway': '1.2.3.1',
                  'nameserver': '1.2.3.1',
                  'name': 'name'}
        self.container = lxc.LxcContainer(self.server, config)

    def test_container_construct(self):
        expected = {'ip': '1.2.3.4/24',
                    'gateway': '1.2.3.1',
                    'name': 'name',
                    'nameserver': '1.2.3.1',
                    'network_bridge': 'br0'}
        self.assertEqual(expected, self.container.config)
        self.assertIsInstance(self.container.server, lxc.provider.ServerDTO)

    def test_container_create(self):
        with mock.patch.object(lxc.LxcContainer, 'configure') as configure:
            self.container.create('ubuntu')
        expected = [mock.call.ssh.execute('lxc-create',
                                          '-B', 'btrfs',
                                          '-n', 'name',
                                          '-t', 'ubuntu')]
        self.assertEqual(expected, self.server.mock_calls)
        configure.assert_called_once()

    def test_container_clone(self):
        with mock.patch.object(lxc.LxcContainer, 'configure') as configure:
            self.container.clone('src')
        expected = [mock.call.ssh.execute('lxc-clone',
                                          '--snapshot',
                                          '-o', 'src',
                                          '-n', 'name')]
        self.assertEqual(expected, self.server.mock_calls)
        configure.assert_called_once()

    def test_container_configure(self):
        self.container.configure()
        s_filename = self.server.mock_calls[0][1][0]
        expected = [
            mock.call.ssh.upload(s_filename, '/tmp/.rally_cont_conf.sh'),
            mock.call.ssh.execute('/bin/sh', '/tmp/.rally_cont_conf.sh',
                                  '/var/lib/lxc/name/rootfs/', '1.2.3.4',
                                  '255.255.255.0', '1.2.3.1', '1.2.3.1')
        ]
        self.assertEqual(expected, self.server.mock_calls)

    def test_container_start(self):
        self.container.start()
        expected = [
            mock.call.ssh.execute('lxc-start', '-d', '-n', 'name')
        ]
        self.assertEqual(expected, self.server.mock_calls)

    def test_container_stop(self):
        self.container.stop()
        expected = [
            mock.call.ssh.execute('lxc-stop', '-n', 'name')
        ]
        self.assertEqual(expected, self.server.mock_calls)

    def test_container_destroy(self):
        self.container.destroy()
        expected = [
            mock.call.ssh.execute('lxc-destroy', '-n', 'name')
        ]
        self.assertEqual(expected, self.server.mock_calls)


class FakeContainer(lxc.LxcContainer):

    def __init__(self, *args, **kwargs):
        super(FakeContainer, self).__init__(*args, **kwargs)
        self.status = []

    def prepare_host(self, *args):
        self.status.append('prepared')

    def create(self, *args):
        self.status.append('created')

    def clone(self, src):
        self.status.append('cloned ' + src)

    def start(self, *args):
        self.status.append('started')

    def stop(self, *args):
        self.status.append('stopped')

    def destroy(self, *args):
        self.status.append('destroyed')

    def configure(self, *args):
        self.status.append('configured')


class LxcProviderTestCase(test.BaseTestCase):

    def setUp(self):
        super(LxcProviderTestCase, self).setUp()
        self.mod = 'rally.serverprovider.providers.lxc.'
        self.config = {
            'name': 'LxcProvider',
            'containers_per_host': 3,
            'distribution': 'ubuntu',
            'start_ip_address': '192.168.0.10/24',
            'container_config': {
                'nameserver': '192.168.0.1',
                'gateway': '192.168.0.1',
            },
            'host_provider': {
                'name': 'DummyProvider',
                'credentials': ['root@host1.net', 'root@host2.net']}
        }
        self.provider = lxc.provider.ProviderFactory.get_provider(
            self.config, {'uuid': 'fake-uuid'})

    def test_create_vms(self):
        s1 = mock.Mock()
        s2 = mock.Mock()
        provider = mock.Mock()
        provider.create_vms = mock.Mock(return_value=[s1, s2])
        get_provider = mock.Mock(return_value=provider)
        with contextlib.nested(
            mock.patch(self.mod + 'provider.ServerDTO'),
            mock.patch(self.mod + 'LxcContainer', new=FakeContainer),
            mock.patch(self.mod + 'provider.ProviderFactory.get_provider',
                       new=get_provider)):
            self.provider.create_vms()
        name = self.provider.containers[0].config['name']
        s_first = ['prepared', 'created', 'started']
        s_clone = ['cloned ' + name, 'started']
        statuses = [c.status for c in self.provider.containers]
        self.assertEqual(6, len(statuses))
        self.assertEqual(([s_first] + [s_clone] * 2) * 2, statuses)

        expected_ips = ['192.168.0.%d/24' % i for i in range(10, 16)]
        ips = [c.config['ip'] for c in self.provider.containers]
        self.assertEqual(expected_ips, ips)

        get_provider.assert_called_once_with(self.config['host_provider'],
                                             {'uuid': 'fake-uuid'})
