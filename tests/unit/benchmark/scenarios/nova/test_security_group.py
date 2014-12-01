# Copyright 2014: Mirantis Inc.
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

from rally.benchmark.scenarios.nova import security_group
from rally import consts
from tests.unit import fakes
from tests.unit import test


SECGROUP = "rally.benchmark.scenarios.nova.security_group"


class FakeNeutronScenario():
    def __enter__(self):
        return {}

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class NovaSecurityGroupTestCase(test.TestCase):

    def test_create_and_delete_security_groups(self):
        fake_secgroups = [fakes.FakeSecurityGroup(None, None, 1, "uuid1"),
                          fakes.FakeSecurityGroup(None, None, 2, "uuid2")]

        nova_scenario = security_group.NovaSecGroup()
        nova_scenario._create_security_groups = mock.MagicMock(
            return_value=fake_secgroups)
        nova_scenario._create_rules_for_security_group = mock.MagicMock()
        nova_scenario._delete_security_groups = mock.MagicMock()

        security_group_count = 2
        rules_per_security_group = 10
        nova_scenario.create_and_delete_secgroups(
            security_group_count, rules_per_security_group)

        nova_scenario._create_security_groups.assert_called_once_with(
            security_group_count)
        nova_scenario._create_rules_for_security_group.assert_called_once_with(
            fake_secgroups, rules_per_security_group)
        nova_scenario._delete_security_groups.assert_called_once_with(
            fake_secgroups)

    def test_create_and_list_secgroups(self):
        fake_secgroups = [fakes.FakeSecurityGroup(None, None, 1, "uuid1"),
                          fakes.FakeSecurityGroup(None, None, 2, "uuid2")]

        nova_scenario = security_group.NovaSecGroup()
        nova_scenario._create_security_groups = mock.MagicMock(
            return_value=fake_secgroups)
        nova_scenario._create_rules_for_security_group = mock.MagicMock()
        nova_scenario._list_security_groups = mock.MagicMock()

        security_group_count = 2
        rules_per_security_group = 10
        nova_scenario.create_and_list_secgroups(
            security_group_count, rules_per_security_group)

        nova_scenario._create_security_groups.assert_called_once_with(
            security_group_count)
        nova_scenario._create_rules_for_security_group.assert_called_once_with(
            fake_secgroups, rules_per_security_group)
        nova_scenario._list_security_groups.assert_called_once_with()

    def _generate_fake_server_with_sg(self, number_of_secgroups):
        sg_list = []
        for i in range(number_of_secgroups):
            sg_list.append(
                fakes.FakeSecurityGroup(None, None, i, "uuid%s" % i))

        return mock.MagicMock(
            list_security_group=mock.MagicMock(return_value=sg_list)), sg_list

    @mock.patch("%s.NeutronContext" % SECGROUP, new=FakeNeutronScenario)
    def _test_boot_and_delete_server_with_secgroups(self,
                                                    mock_neutron_context):
        fake_server, sg_list = self._generate_fake_server_with_sg(2)

        nova_scenario = security_group.NovaSecGroup()
        nova_scenario._create_security_groups = mock.MagicMock(
            return_value=sg_list)
        nova_scenario._create_rules_for_security_group = mock.MagicMock()
        nova_scenario._boot_server = mock.MagicMock(return_value=fake_server)
        nova_scenario._generate_random_name = mock.MagicMock(
            return_value="name")
        nova_scenario._delete_server = mock.MagicMock()
        nova_scenario._delete_security_groups = mock.MagicMock()

        image = "img"
        flavor = 1
        security_group_count = 2
        rules_per_security_group = 10

        nova_scenario.boot_and_delete_server_with_secgroups(
            image, flavor, security_group_count, rules_per_security_group)

        nova_scenario._create_security_groups.assert_called_once_with(
            security_group_count)
        self.assertEqual(1, nova_scenario._generate_random_name.call_count)
        nova_scenario._create_rules_for_security_group.assert_called_once_with(
            sg_list, rules_per_security_group)
        nova_scenario._boot_server.assert_called_once_with(
            "name", image, flavor,
            security_groups=[sg.name for sg in sg_list])
        fake_server.list_security_group.assert_called_once_with()
        nova_scenario._delete_server.assert_called_once_with(fake_server)
        nova_scenario._delete_security_groups.assert_called_once_with(sg_list)

    @mock.patch("%s.NeutronContext" % SECGROUP, new=FakeNeutronScenario)
    def _test_boot_and_delete_server_with_sg_not_attached(
            self, mock_neutron_context):
        fake_secgroups = [fakes.FakeSecurityGroup(None, None, 1, "uuid1"),
                          fakes.FakeSecurityGroup(None, None, 2, "uuid2")]

        fake_server, sg_list = self._generate_fake_server_with_sg(1)

        nova_scenario = security_group.NovaSecGroup()
        nova_scenario._create_security_groups = mock.MagicMock(
            return_value=fake_secgroups)
        nova_scenario._create_rules_for_security_group = mock.MagicMock()
        nova_scenario._boot_server = mock.MagicMock(return_value=fake_server)
        nova_scenario._generate_random_name = mock.MagicMock(
            return_value="name")
        nova_scenario._delete_server = mock.MagicMock()
        nova_scenario._delete_security_groups = mock.MagicMock()

        image = "img"
        flavor = 1
        security_group_count = 2
        rules_per_security_group = 10

        self.assertRaises(security_group.NovaSecurityGroupException,
                          nova_scenario.boot_and_delete_server_with_secgroups,
                          image, flavor, security_group_count,
                          rules_per_security_group)

        nova_scenario._create_security_groups.assert_called_once_with(
            security_group_count)
        self.assertEqual(1, nova_scenario._generate_random_name.call_count)
        nova_scenario._create_rules_for_security_group.assert_called_once_with(
            fake_secgroups, rules_per_security_group)
        nova_scenario._boot_server.assert_called_once_with(
            "name", image, flavor,
            security_groups=[sg.name for sg in fake_secgroups])
        fake_server.list_security_group.assert_called_once_with()
        nova_scenario._delete_server.assert_called_once_with(fake_server)
        nova_scenario._delete_security_groups.assert_called_once_with(
            fake_secgroups)


class NeutronNetworkTestCase(test.TestCase):
    @mock.patch("%s.NeutronNetwork._delete_network" % SECGROUP)
    @mock.patch("%s.NeutronNetwork._create_network_and_subnets" % SECGROUP)
    @mock.patch("%s.NeutronNetwork.clients" % SECGROUP)
    def test_neutron_is_enabled(self, mock_clients, mock_create_net,
                                mock_delete_net):
        fake_net = {"network": {"id": "fake_id"}}
        mock_create_net.return_value = (fake_net, None)
        mock_clients.return_value = {
            consts.ServiceType.NETWORK: consts.Service.NEUTRON}

        with security_group.NeutronNetwork(None, None) as boot_kwargs:
            self.assertEqual({"nics": [{"net-id": fake_net["network"]["id"]}]},
                             boot_kwargs)

        self.assertEqual(2, mock_clients.call_count)
        mock_create_net.assert_called_once_with(network_create_args=None,
                                                subnet_create_args=None,
                                                subnets_per_network=1,
                                                subnet_cidr_start=None)
        mock_delete_net.assert_called_once_with(fake_net["network"])

    @mock.patch("%s.NeutronNetwork._delete_network" % SECGROUP)
    @mock.patch("%s.NeutronNetwork._create_network_and_subnets" % SECGROUP)
    @mock.patch("%s.NeutronNetwork.clients" % SECGROUP, return_value={})
    def test_neutron_is_disabled(self, mock_clients, mock_create_net,
                                 mock_delete_net):

        with security_group.NeutronNetwork(None, None) as boot_kwargs:
            self.assertEqual({}, boot_kwargs)

        self.assertEqual(2, mock_clients.call_count)
        self.assertFalse(mock_create_net.called)
        self.assertFalse(mock_delete_net.called)
