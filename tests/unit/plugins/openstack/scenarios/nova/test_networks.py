# Copyright 2015: Mirantis Inc.
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

from rally.plugins.openstack.scenarios.nova import networks
from tests.unit import test


class NovaNetworksTestCase(test.TestCase):

    def test_create_and_list_networks(self):
        scenario = networks.CreateAndListNetworks()
        scenario._create_network = mock.MagicMock()
        scenario._list_networks = mock.MagicMock()
        start_cidr = "10.2.0.0/24"
        scenario.run(start_cidr=start_cidr, fakearg="fakearg")

        scenario._create_network.assert_called_once_with(
            start_cidr, fakearg="fakearg")
        scenario._list_networks.assert_called_once_with()

    def test_create_and_delete_network(self):
        scenario = networks.CreateAndDeleteNetwork()
        fake_network = mock.MagicMock()
        fake_network.cidr = "10.2.0.0/24"
        start_cidr = "10.2.0.0/24"
        scenario._create_network = mock.MagicMock(return_value=fake_network)
        scenario._delete_network = mock.MagicMock()
        scenario.run(start_cidr=start_cidr, fakearg="fakearg")

        scenario._create_network.assert_called_once_with(
            start_cidr, fakearg="fakearg")
        scenario._delete_network.assert_called_once_with(
            fake_network)
