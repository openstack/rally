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
import netaddr

from rally.openstack.common.fixture import mockpatch
from rally.openstack.common import test
from rally.serverprovider.providers import virsh


class VirshProviderTestCase(test.BaseTestCase):
    def setUp(self):
        super(VirshProviderTestCase, self).setUp()
        self.deployment = mock.Mock()
        self.config = {
            'name': 'VirshProvider',
            'connection': 'user@host',
            'template_name': 'prefix',
            'template_user': 'user',
            'template_password': 'password',
        }
        self.provider = virsh.VirshProvider(self.deployment, self.config)
        self.useFixture(mockpatch.PatchObject(self.provider, 'resources'))

    @mock.patch('rally.serverprovider.providers.virsh.netaddr.IPAddress')
    @mock.patch('rally.serverprovider.providers.virsh.subprocess')
    def test_create_vm(self, mock_subp, mock_ipaddress):
        mock_subp.check_output.return_value = '10.0.0.1'
        mock_ipaddress.return_value = '10.0.0.2'
        server = self.provider.create_vm('name')
        mock_subp.assert_has_calls([
            mock.call.check_call('virt-clone --connect=qemu+ssh://user@host/'
                                 'system -o prefix -n name --auto-clone',
                                 shell=True),
            mock.call.check_call('virsh --connect=qemu+ssh://user@host/system '
                                 'start name', shell=True),
            mock.call.check_call('scp -o StrictHostKeyChecking=no  rally/serve'
                                 'rprovider/providers/virsh/get_domain_ip.sh u'
                                 'ser@host:~/get_domain_ip.sh', shell=True),
            mock.call.check_output('ssh -o StrictHostKeyChecking=no user@host '
                                   './get_domain_ip.sh name', shell=True),
        ])
        mock_ipaddress.assert_called_once_with('10.0.0.1')
        self.assertEqual(server.uuid, 'name')
        self.assertEqual(server.ip, '10.0.0.2')
        self.assertEqual(server.user, 'user')
        self.assertEqual(server.key, None)
        self.assertEqual(server.password, 'password')
        self.provider.resources.create.assert_called_once_with({
            'name': 'name',
        })

    @mock.patch('rally.serverprovider.providers.virsh.netaddr.IPAddress')
    @mock.patch('rally.serverprovider.providers.virsh.subprocess')
    @mock.patch('time.sleep')
    def test_create_vm_ip_failed(self, mock_sleep, mock_subp, mock_ipaddress):
        mock_ipaddress.side_effect = netaddr.core.AddrFormatError
        server = self.provider.create_vm('name')
        mock_subp.assert_has_calls(3 * [
            mock.call.check_output('ssh -o StrictHostKeyChecking=no user@host '
                                   './get_domain_ip.sh name', shell=True),
        ])
        self.assertEqual(server.ip, 'None')

    @mock.patch('rally.serverprovider.providers.virsh.subprocess')
    def test_destroy_vm(self, mock_subp):
        self.provider.destroy_vm('uuid')
        mock_subp.assert_has_calls([
            mock.call.check_call('virsh --connect=qemu+ssh://user@host/system '
                                 'destroy uuid', shell=True),
            mock.call.check_call('virsh --connect=qemu+ssh://user@host/system '
                                 'undefine uuid --remove-all-storage',
                                 shell=True),
        ])

    @mock.patch('rally.serverprovider.providers.virsh.uuid')
    @mock.patch.object(virsh.VirshProvider, 'create_vm')
    def test_create_vms(self, mock_create, mock_uuid):
        mock_uuid.uuid4.side_effect = ['1', '2', '3']
        mock_create.side_effect = ['s1', 's2', 's3']
        servers = self.provider.create_vms(amount=3)
        self.assertEqual(servers, ['s1', 's2', 's3'])
        mock_create.assert_has_calls([
            mock.call('1'),
            mock.call('2'),
            mock.call('3'),
        ])

    @mock.patch.object(virsh.VirshProvider, 'destroy_vm')
    def test_destroy_vms(self, mock_destroy):
        self.provider.resources.get_all.return_value = [
            {'info': {'name': '1'}},
            {'info': {'name': '2'}},
            {'info': {'name': '3'}},
        ]
        self.provider.destroy_vms()
        mock_destroy.assert_has_calls([
            mock.call('1'),
            mock.call('2'),
            mock.call('3'),
        ])
        self.provider.resources.get_all.assert_called_once_with()
