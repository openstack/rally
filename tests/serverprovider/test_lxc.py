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

from rally.openstack.common.fixture import mockpatch
from rally.openstack.common import test
from rally.serverprovider.providers import lxc


MOD_NAME = 'rally.serverprovider.providers.lxc.'


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
        self.assertIsInstance(self.container.server, lxc.provider.Server)

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


class LxcProviderTestCase(test.BaseTestCase):

    def setUp(self):
        super(LxcProviderTestCase, self).setUp()
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
        self.mock_deployment = mock.MagicMock()
        self.provider = lxc.provider.ProviderFactory.get_provider(
            self.config, self.mock_deployment)
        self.useFixture(mockpatch.PatchObject(self.provider, 'resources'))

    @mock.patch(MOD_NAME + 'uuid')
    @mock.patch('rally.serverprovider.provider.Server')
    @mock.patch(MOD_NAME + 'LxcContainer')
    @mock.patch(MOD_NAME + 'provider.ProviderFactory.get_provider')
    def test_create_vms(self, get_provider, mock_lxc_container, mock_server,
                        mock_uuid):
        def create_config(ip, name):
            conf = self.config['container_config'].copy()
            conf['ip'] = ip
            conf['name'] = name
            return conf

        mock_uuid.uuid4.return_value = 'fakeuuid'
        mock_first_conts = [mock.Mock(), mock.Mock()]
        mock_conts = [mock.Mock() for i in range(4)]
        mock_lxc_container.side_effect = containers = \
            [mock_first_conts[0]] + mock_conts[:2] + \
            [mock_first_conts[1]] + mock_conts[2:]
        for (i, mock_cont_i) in enumerate(containers):
            mock_cont_i.server.get_credentials.return_value = i
        s1 = mock.Mock()
        s2 = mock.Mock()
        provider = mock.Mock()
        provider.create_vms = mock.Mock(return_value=[s1, s2])
        get_provider.return_value = provider

        self.provider.create_vms()

        configs = [
            create_config('192.168.0.10/24', 'fakeuuid'),
            create_config('192.168.0.11/24', 'fakeuuid-1'),
            create_config('192.168.0.12/24', 'fakeuuid-2'),
            create_config('192.168.0.13/24', 'fakeuuid'),
            create_config('192.168.0.14/24', 'fakeuuid-1'),
            create_config('192.168.0.15/24', 'fakeuuid-2'),
        ]

        mock_lxc_container.assert_has_calls(
            [mock.call(*a) for a in zip(3 * [s1] + 3 * [s2], configs)])

        for mock_cont_i in mock_first_conts:
            mock_cont_i.assert_has_calls([
                mock.call.prepare_host(),
                mock.call.create('ubuntu'),
                mock.call.server.get_credentials(),
                mock.call.start(),
                mock.call.server.ssh.wait(),
            ])
        for mock_cont_i in mock_conts:
            mock_cont_i.assert_has_calls([
                mock.call.clone('fakeuuid'),
                mock.call.start(),
                mock.call.server.get_credentials(),
                mock.call.server.ssh.wait(),
            ])
        get_provider.assert_called_once_with(self.config['host_provider'],
                                             self.mock_deployment)
        self.provider.resources.create.assert_has_calls(
            [mock.call({'config': a[0], 'server': a[1]})
             for a in zip(configs, range(6))])

    @mock.patch(MOD_NAME + 'provider.ProviderFactory.get_provider')
    @mock.patch(MOD_NAME + 'provider.Server')
    @mock.patch(MOD_NAME + 'LxcContainer')
    def test_destroy_vms(self, mock_lxc_container, mock_server,
                         mock_get_provider):
        mock_lxc_container.return_value = mock_container = mock.Mock()
        mock_get_provider.return_value = mock_provider = mock.Mock()
        resource = {
            'info': {
                'config': 'fakeconfig',
                'server': 'fakeserver0',
            },
        }
        self.provider.resources.get_all.return_value = [resource]
        mock_server.from_credentials.return_value = 'fakeserver1'
        self.provider.destroy_vms()
        mock_server.from_credentials.assert_called_once_with('fakeserver0')
        mock_lxc_container.assert_called_once_with('fakeserver1', 'fakeconfig')
        mock_container.assert_has_calls([
            mock.call.stop(),
            mock.call.destroy(),
        ])
        self.provider.resources.delete.asert_called_once_with(resource)
        mock_get_provider.assert_called_once_with(self.config['host_provider'],
                                                  self.mock_deployment)
        mock_provider.assert_has_calls([
            mock.call.destroy_vms(),
        ])
