# Copyright 2015 Mirantis Inc.
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

import ddt
import mock

from rally.plugins.openstack.scenarios.manila import shares
from tests.unit import test


@ddt.ddt
class ManilaSharesTestCase(test.TestCase):

    @ddt.data(
        {"share_proto": "nfs", "size": 3},
        {"share_proto": "cifs", "size": 4,
         "share_network": "foo", "share_type": "bar"},
    )
    def test_create_and_delete_share(self, params):
        fake_share = mock.MagicMock()
        scenario = shares.ManilaShares()
        scenario._create_share = mock.MagicMock(return_value=fake_share)
        scenario.sleep_between = mock.MagicMock()
        scenario._delete_share = mock.MagicMock()

        scenario.create_and_delete_share(min_sleep=3, max_sleep=4, **params)

        scenario._create_share.assert_called_once_with(**params)
        scenario.sleep_between.assert_called_once_with(3, 4)
        scenario._delete_share.assert_called_once_with(fake_share)

    @ddt.data(
        {},
        {"detailed": True},
        {"detailed": False},
        {"search_opts": None},
        {"search_opts": {}},
        {"search_opts": {"foo": "bar"}},
        {"detailed": True, "search_opts": None},
        {"detailed": False, "search_opts": None},
        {"detailed": True, "search_opts": {"foo": "bar"}},
        {"detailed": False, "search_opts": {"quuz": "foo"}},
    )
    @ddt.unpack
    def test_list_shares(self, detailed=True, search_opts=None):
        scenario = shares.ManilaShares()
        scenario._list_shares = mock.MagicMock()

        scenario.list_shares(detailed=detailed, search_opts=search_opts)

        scenario._list_shares.assert_called_once_with(
            detailed=detailed, search_opts=search_opts)

    @ddt.data(
        {},
        {"name": "foo_name"},
        {"description": "foo_description"},
        {"neutron_net_id": "foo_neutron_net_id"},
        {"neutron_subnet_id": "foo_neutron_subnet_id"},
        {"nova_net_id": "foo_nova_net_id"},
        {"name": "foo_name",
         "description": "foo_description",
         "neutron_net_id": "foo_neutron_net_id",
         "neutron_subnet_id": "foo_neutron_subnet_id",
         "nova_net_id": "foo_nova_net_id"},
    )
    def test_create_share_network_and_delete(self, params):
        fake_sn = mock.MagicMock()
        scenario = shares.ManilaShares()
        scenario._create_share_network = mock.MagicMock(return_value=fake_sn)
        scenario._delete_share_network = mock.MagicMock()
        expected_params = {
            "name": None,
            "description": None,
            "neutron_net_id": None,
            "neutron_subnet_id": None,
            "nova_net_id": None,
        }
        expected_params.update(params)

        scenario.create_share_network_and_delete(**params)

        scenario._create_share_network.assert_called_once_with(
            **expected_params)
        scenario._delete_share_network.assert_called_once_with(fake_sn)

    @ddt.data(
        {},
        {"name": "foo_name"},
        {"description": "foo_description"},
        {"neutron_net_id": "foo_neutron_net_id"},
        {"neutron_subnet_id": "foo_neutron_subnet_id"},
        {"nova_net_id": "foo_nova_net_id"},
        {"name": "foo_name",
         "description": "foo_description",
         "neutron_net_id": "foo_neutron_net_id",
         "neutron_subnet_id": "foo_neutron_subnet_id",
         "nova_net_id": "foo_nova_net_id"},
    )
    def test_create_share_network_and_list(self, params):
        scenario = shares.ManilaShares()
        scenario._create_share_network = mock.MagicMock()
        scenario._list_share_networks = mock.MagicMock()
        expected_create_params = {
            "name": params.get("name"),
            "description": params.get("description"),
            "neutron_net_id": params.get("neutron_net_id"),
            "neutron_subnet_id": params.get("neutron_subnet_id"),
            "nova_net_id": params.get("nova_net_id"),
        }
        expected_list_params = {
            "detailed": params.get("detailed", True),
            "search_opts": params.get("search_opts"),
        }
        expected_create_params.update(params)

        scenario.create_share_network_and_list(**params)

        scenario._create_share_network.assert_called_once_with(
            **expected_create_params)
        scenario._list_share_networks.assert_called_once_with(
            **expected_list_params)
