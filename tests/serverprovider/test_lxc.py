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


import mock
import os

from rally.openstack.common import test
from rally.serverprovider.providers import lxc


class LxcContainerTestCase(test.BaseTestCase):

    def setUp(self):
        super(LxcContainerTestCase, self).setUp()
        self.container = lxc.LxcContainer('user', 'host',
                                          {'ip': '1.2.3.4/24',
                                           'name': 'name'})

    def test_container_construct(self):
        expected_config = {'network_bridge': 'br0', 'name': 'name',
                           'ip': '1.2.3.4/24', 'dhcp': ''}
        self.assertEqual(self.container.config, expected_config)

    def test_container_create(self):
        with mock.patch('rally.serverprovider.providers.lxc.sshutils') as ssh:
            self.container.create('ubuntu')
        expected = [
            mock.call.execute_command('user', 'host', ['lxc-create',
                                                       '-n', 'name',
                                                       '-t', 'ubuntu'])]
        self.assertEqual(ssh.mock_calls, expected)

    def test_container_clone(self):
        with mock.patch('rally.serverprovider.providers.lxc.sshutils') as ssh:
            self.container.clone('src')
        expected = [
            mock.call.execute_command('user', 'host',
                                      ['lxc-clone',
                                       '-o', 'src',
                                       '-n', 'name'])]
        self.assertEqual(expected, ssh.mock_calls)

    def test_container_configure(self):
        with mock.patch('rally.serverprovider.providers.lxc.sshutils') as ssh:
            self.container.configure()
        filename = ssh.mock_calls[0][1][2]
        expected = [
            mock.call.upload_file('user', 'host', filename,
                                  '/var/lib/lxc/name/config'),
            mock.call.execute_command('user', 'host',
                                      ['mkdir',
                                       '/var/lib/lxc/name/rootfs/root/.ssh']),
            mock.call.execute_command('user', 'host',
                                      ['cp', '~/.ssh/authorized_keys',
                                       '/var/lib/lxc/name/rootfs/root/.ssh/'])
        ]
        self.assertEqual(ssh.mock_calls, expected)

    def test_container_start(self):
        with mock.patch('rally.serverprovider.providers.lxc.sshutils') as ssh:
            self.container.start()
        expected = [
            mock.call.execute_command('user', 'host',
                                      ['lxc-start', '-d', '-n', 'name'])
        ]
        self.assertEqual(ssh.mock_calls, expected)

    def test_container_stop(self):
        with mock.patch('rally.serverprovider.providers.lxc.sshutils') as ssh:
            self.container.stop()
        expected = [
            mock.call.execute_command('user', 'host',
                                      ['lxc-stop', '-n', 'name'])
        ]
        self.assertEqual(ssh.mock_calls, expected)

    def test_container_destroy(self):
        with mock.patch('rally.serverprovider.providers.lxc.sshutils') as ssh:
            self.container.destroy()
        expected = [
            mock.call.execute_command('user', 'host',
                                      ['lxc-destroy', '-n', 'name'])
        ]
        self.assertEqual(ssh.mock_calls, expected)


class FakeContainer(lxc.LxcContainer):

    def create(self, *args):
        self.status = ['created']

    def clone(self, src):
        if not hasattr(self, 'status'):
            self.status = []
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
        self.config = {
            'name': 'LxcProvider',
            'containers_per_host': 3,
            'host_provider': {
                'name': 'DummyProvider',
                'credentials': ['root@host1.net', 'root@host2.net']}
        }
        self.provider = lxc.provider.ProviderFactory.get_provider(
            self.config, {"uuid": "fake-uuid"})

    def test_lxc_install(self):
        with mock.patch('rally.serverprovider.providers.lxc.sshutils') as ssh:
            self.provider.lxc_install()
        expected_script = os.path.abspath('rally/serverprovider/providers/'
                                          'lxc/lxc-install.sh')
        expected = [
            mock.call.execute_script('root', 'host1.net', expected_script),
            mock.call.execute_script('root', 'host2.net', expected_script)
        ]
        self.assertEqual(ssh.mock_calls, expected)

    def test_lxc_create_destroy_vms(self):
        mod = 'rally.serverprovider.providers.lxc.'
        with mock.patch(mod + 'sshutils'):
            with mock.patch(mod + 'LxcContainer', new=FakeContainer):
                self.provider.create_vms()
                self.provider.destroy_vms()
        c = self.provider.containers

        name1 = c[0].config['name']
        name2 = c[3].config['name']
        ssd = ['configured', 'started', 'stopped', 'destroyed']

        self.assertEqual(c[0].status, ['created'] + ssd)
        self.assertEqual(c[1].status, ['cloned ' + name1] + ssd)
        self.assertEqual(c[2].status, ['cloned ' + name1] + ssd)

        self.assertEqual(c[3].status, ['created'] + ssd)
        self.assertEqual(c[4].status, ['cloned ' + name2] + ssd)
        self.assertEqual(c[5].status, ['cloned ' + name2] + ssd)

        self.assertEqual(len(c), 6)


class LxcProviderStaticIpTestCase(test.BaseTestCase):

    def test_static_ips(self):
        config = {
            'name': 'LxcProvider',
            'containers_per_host': 3,
            'ipv4_start_address': '1.1.1.1',
            'ipv4_prefixlen': 24,
            'host_provider': {
                'name': 'DummyProvider',
                'credentials': ['root@host1.net', 'root@host2.net']}
        }
        provider = lxc.provider.ProviderFactory.get_provider(
            config, {'uuid': 'fake-task-uuid'})

        mod = 'rally.serverprovider.providers.lxc.'
        with mock.patch(mod + 'sshutils'):
            with mock.patch(mod + 'LxcContainer', new=FakeContainer):
                provider.create_vms()

        ips = [c.config['ip'] for c in provider.containers]
        expected = ['1.1.1.1/24', '1.1.1.2/24', '1.1.1.3/24',
                    '1.1.1.4/24', '1.1.1.5/24', '1.1.1.6/24']
        self.assertEqual(ips, expected)
