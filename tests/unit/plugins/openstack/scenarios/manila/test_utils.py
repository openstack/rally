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

from rally import exceptions
from rally.plugins.openstack.context.manila import consts
from rally.plugins.openstack.scenarios.manila import utils
from tests.unit import test

BM_UTILS = "rally.task.utils."


@ddt.ddt
class ManilaScenarioTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(ManilaScenarioTestCase, self).setUp()
        self.scenario = utils.ManilaScenario(self.context)

    def test__create_share(self):
        fake_share = mock.Mock()
        self.clients("manila").shares.create.return_value = fake_share
        self.scenario.context = {
            "tenant": {
                consts.SHARE_NETWORKS_CONTEXT_NAME: {
                    "share_networks": [{"id": "sn_1_id"}, {"id": "sn_2_id"}],
                }
            },
            "iteration": 0,
        }
        fake_random_name = "fake_random_name_value"
        self.scenario.generate_random_name = mock.Mock(
            return_value=fake_random_name)

        self.scenario._create_share("nfs")

        self.clients("manila").shares.create.assert_called_once_with(
            "nfs", 1, name=fake_random_name,
            share_network=self.scenario.context["tenant"][
                consts.SHARE_NETWORKS_CONTEXT_NAME]["share_networks"][0]["id"])

        self.mock_wait_for_status.mock.assert_called_once_with(
            fake_share,
            ready_statuses=["available"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            timeout=300, check_interval=3)
        self.mock_get_from_manager.mock.assert_called_once_with()

    @mock.patch(BM_UTILS + "wait_for_status")
    def test__delete_share(self, mock_wait_for_status):
        fake_share = mock.MagicMock()

        self.scenario._delete_share(fake_share)

        fake_share.delete.assert_called_once_with()
        mock_wait_for_status.assert_called_once_with(
            fake_share,
            ready_statuses=["deleted"],
            check_deletion=True,
            update_resource=self.mock_get_from_manager.mock.return_value,
            timeout=180, check_interval=2)
        self.mock_get_from_manager.mock.assert_called_once_with(
            ("error_deleting", ))

    @ddt.data(
        {},
        {"detailed": False, "search_opts": None},
        {"detailed": True, "search_opts": {"name": "foo_sn"}},
        {"search_opts": {"project_id": "fake_project"}},
    )
    def test__list_shares(self, params):
        fake_shares = ["foo", "bar"]
        self.clients("manila").shares.list.return_value = fake_shares

        result = self.scenario._list_shares(**params)

        self.assertEqual(fake_shares, result)
        self.clients("manila").shares.list.assert_called_once_with(
            detailed=params.get("detailed", True),
            search_opts=params.get("search_opts"))

    @ddt.data(
        {"new_size": 5},
        {"new_size": 10}
    )
    def test__extend_share(self, new_size):
        fake_share = mock.MagicMock()

        self.scenario._extend_share(fake_share, new_size)

        fake_share.extend.assert_called_with(new_size)

        self.mock_wait_for_status.mock.assert_called_once_with(
            fake_share,
            ready_statuses=["available"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            timeout=300, check_interval=3)
        self.mock_get_from_manager.mock.assert_called_once_with()

    @ddt.data(
        {"new_size": 5},
        {"new_size": 10}
    )
    def test__shrink_share(self, new_size):
        fake_share = mock.MagicMock()

        self.scenario._shrink_share(fake_share, new_size)

        fake_share.shrink.assert_called_with(new_size)

        self.mock_wait_for_status.mock.assert_called_once_with(
            fake_share,
            ready_statuses=["available"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            timeout=300, check_interval=3)
        self.mock_get_from_manager.mock.assert_called_once_with()

    @ddt.data(
        {
            "access_type": "ip",
            "access": "1.2.3.4",
            "access_level": "rw",
            "access_id": "foo"
        },
        {
            "access_type": "domain",
            "access": "4.3.2.1",
            "access_level": "ro",
            "access_id": "bar"
        }
    )
    @ddt.unpack
    def test__allow_access_share(self, access_type, access, access_level,
                                 access_id):
        fake_allow_result = {"id": access_id}
        fake_access = mock.MagicMock()
        fake_access.id = access_id
        fake_update = mock.MagicMock()
        self.scenario._update_resource_in_allow_access_share = mock.MagicMock(
            return_value=fake_update)

        fake_share = mock.MagicMock()
        fake_share.allow.return_value = fake_allow_result
        fake_share.access_list.return_value = [fake_access]

        self.assertEqual(self.scenario._allow_access_share(
            fake_share, access_type, access, access_level), fake_allow_result)

        self.scenario._update_resource_in_allow_access_share \
            .assert_called_with(fake_share, access_id)
        self.mock_wait_for_status.mock.assert_called_once_with(
            fake_access,
            ready_statuses=["active"],
            update_resource=fake_update,
            check_interval=3.0,
            timeout=300.0)

    def test__get_access_from_share_with_no_access_in_share(self):
        access_id = "foo"
        fake_share = mock.MagicMock()
        fake_access = mock.MagicMock()
        fake_access.id = access_id
        fake_share.access_list.return_value = []

        self.assertRaises(exceptions.GetResourceNotFound,
                          self.scenario._get_access_from_share,
                          fake_share, access_id)

    def test__get_access_from_share(self):
        access_id = "foo"
        fake_share = mock.MagicMock()
        fake_access = mock.MagicMock()
        fake_access.id = access_id
        fake_share.access_list.return_value = [fake_access]

        access = self.scenario._get_access_from_share(fake_share, access_id)

        self.assertEqual(access, fake_access)

    def test__update_resource_in_allow_access_share(self):
        access_id = "foo"
        fake_share = mock.MagicMock()
        fake_resource = mock.MagicMock()
        fake_access = mock.MagicMock()
        fake_access.id = access_id
        fake_share.access_list.return_value = [fake_access]

        fn = self.scenario._update_resource_in_allow_access_share(
            fake_share, access_id)

        self.assertEqual(fn(fake_resource), fake_access)

    def test__deny_access_share(self):
        access_id = "foo"
        fake_access = mock.MagicMock()
        fake_access.id = access_id
        fake_update = mock.MagicMock()
        self.scenario._update_resource_in_deny_access_share = mock.MagicMock(
            return_value=fake_update)

        fake_share = mock.MagicMock()
        fake_share.access_list.return_value = [fake_access]

        self.scenario._deny_access_share(fake_share, access_id)

        self.scenario._update_resource_in_deny_access_share  \
            .assert_called_with(fake_share, access_id)

        self.mock_wait_for_status.mock.assert_called_once_with(
            fake_access,
            check_deletion=True,
            ready_statuses=["deleted"],
            update_resource=fake_update,
            check_interval=2.0,
            timeout=180.0)

    def test__update_resource_in_deny_access_share(self):
        access_id = "foo"
        fake_share = mock.MagicMock()
        fake_resource = mock.MagicMock()
        fake_access = mock.MagicMock()
        fake_access.id = access_id
        fake_share.access_list.return_value = [fake_access]

        fn = self.scenario._update_resource_in_deny_access_share(
            fake_share, access_id)

        assert fn(fake_resource) == fake_access

    def test__update_resource_in_deny_access_share_with_deleted_resource(self):
        access_id = "foo"
        fake_share = mock.MagicMock()
        fake_resource = mock.MagicMock()
        fake_access = mock.MagicMock()
        fake_access.access_id = access_id
        fake_share.access_list.return_value = []

        fn = self.scenario._update_resource_in_deny_access_share(
            fake_share, access_id)

        self.assertRaises(exceptions.GetResourceNotFound,
                          fn, fake_resource)

    def test__create_share_network(self):
        fake_sn = mock.Mock()
        self.scenario.generate_random_name = mock.Mock()
        self.clients("manila").share_networks.create.return_value = fake_sn
        data = {
            "neutron_net_id": "fake_neutron_net_id",
            "neutron_subnet_id": "fake_neutron_subnet_id",
            "nova_net_id": "fake_nova_net_id",
            "description": "fake_description",
        }
        expected = dict(data)
        expected["name"] = self.scenario.generate_random_name.return_value

        result = self.scenario._create_share_network(**data)

        self.assertEqual(fake_sn, result)
        self.clients("manila").share_networks.create.assert_called_once_with(
            **expected)

    @mock.patch(BM_UTILS + "wait_for_status")
    def test__delete_share_network(self, mock_wait_for_status):
        fake_sn = mock.MagicMock()

        self.scenario._delete_share_network(fake_sn)

        fake_sn.delete.assert_called_once_with()
        mock_wait_for_status.assert_called_once_with(
            fake_sn,
            ready_statuses=["deleted"],
            check_deletion=True,
            update_resource=self.mock_get_from_manager.mock.return_value,
            timeout=180, check_interval=2)
        self.mock_get_from_manager.mock.assert_called_once_with()

    @ddt.data(
        {"detailed": True, "search_opts": {"name": "foo_sn"}},
        {"detailed": False, "search_opts": None},
        {},
        {"search_opts": {"project_id": "fake_project"}},
    )
    def test__list_share_networks(self, params):
        fake_share_networks = ["foo", "bar"]
        self.clients("manila").share_networks.list.return_value = (
            fake_share_networks)

        result = self.scenario._list_share_networks(**params)

        self.assertEqual(fake_share_networks, result)
        self.clients("manila").share_networks.list.assert_called_once_with(
            detailed=params.get("detailed", True),
            search_opts=params.get("search_opts"))

    @ddt.data(
        {},
        {"search_opts": None},
        {"search_opts": {"project_id": "fake_project"}},
    )
    def test__list_share_servers(self, params):
        fake_share_servers = ["foo", "bar"]
        self.admin_clients("manila").share_servers.list.return_value = (
            fake_share_servers)

        result = self.scenario._list_share_servers(**params)

        self.assertEqual(fake_share_servers, result)
        self.admin_clients(
            "manila").share_servers.list.assert_called_once_with(
                search_opts=params.get("search_opts"))

    @ddt.data("ldap", "kerberos", "active_directory")
    def test__create_security_service(self, ss_type):
        fake_ss = mock.Mock()
        self.clients("manila").security_services.create.return_value = fake_ss
        self.scenario.generate_random_name = mock.Mock()
        data = {
            "security_service_type": ss_type,
            "dns_ip": "fake_dns_ip",
            "server": "fake_server",
            "domain": "fake_domain",
            "user": "fake_user",
            "password": "fake_password",
            "description": "fake_description",
        }
        expected = dict(data)
        expected["type"] = expected.pop("security_service_type")
        expected["name"] = self.scenario.generate_random_name.return_value

        result = self.scenario._create_security_service(**data)

        self.assertEqual(fake_ss, result)
        self.clients(
            "manila").security_services.create.assert_called_once_with(
                **expected)

    @mock.patch(BM_UTILS + "wait_for_status")
    def test__delete_security_service(self, mock_wait_for_status):
        fake_ss = mock.MagicMock()

        self.scenario._delete_security_service(fake_ss)

        fake_ss.delete.assert_called_once_with()
        mock_wait_for_status.assert_called_once_with(
            fake_ss,
            ready_statuses=["deleted"],
            check_deletion=True,
            update_resource=self.mock_get_from_manager.mock.return_value,
            timeout=180, check_interval=2)
        self.mock_get_from_manager.mock.assert_called_once_with()

    def test__add_security_service_to_share_network(self):
        fake_sn = mock.MagicMock()
        fake_ss = mock.MagicMock()

        result = self.scenario._add_security_service_to_share_network(
            share_network=fake_sn, security_service=fake_ss)

        self.assertEqual(
            self.clients(
                "manila").share_networks.add_security_service.return_value,
            result)
        self.clients(
            "manila").share_networks.add_security_service.assert_has_calls([
                mock.call(fake_sn, fake_ss)])

    @ddt.data(
        {"key_min_length": 5, "key_max_length": 4},
        {"value_min_length": 5, "value_max_length": 4},
    )
    def test__set_metadata_wrong_params(self, params):
        self.assertRaises(
            exceptions.InvalidArgumentsException,
            self.scenario._set_metadata,
            {"id": "fake_share_id"}, **params)

    @ddt.data(
        {},
        {"sets": 0, "set_size": 1},
        {"sets": 1, "set_size": 1},
        {"sets": 5, "set_size": 7},
        {"sets": 5, "set_size": 2},
        {"key_min_length": 1, "key_max_length": 1},
        {"key_min_length": 1, "key_max_length": 2},
        {"key_min_length": 256, "key_max_length": 256},
        {"value_min_length": 1, "value_max_length": 1},
        {"value_min_length": 1, "value_max_length": 2},
        {"value_min_length": 1024, "value_max_length": 1024},
    )
    def test__set_metadata(self, params):
        share = {"id": "fake_share_id"}
        sets = params.get("sets", 1)
        set_size = params.get("set_size", 1)
        gen_name_calls = sets * set_size * 2
        data = range(gen_name_calls)
        generator_data = iter(data)

        def fake_random_name(prefix="fake", length="fake"):
            return next(generator_data)

        scenario = self.scenario
        scenario.clients = mock.MagicMock()
        scenario._generate_random_part = mock.MagicMock(
            side_effect=fake_random_name)

        keys = scenario._set_metadata(share, **params)

        self.assertEqual(
            gen_name_calls,
            scenario._generate_random_part.call_count)
        self.assertEqual(
            params.get("sets", 1),
            scenario.clients.return_value.shares.set_metadata.call_count)
        scenario.clients.return_value.shares.set_metadata.assert_has_calls([
            mock.call(
                share["id"],
                dict([(j, j + 1) for j in data[
                    i * set_size * 2: (i + 1) * set_size * 2: 2]])
            ) for i in range(sets)
        ])
        self.assertEqual([i for i in range(0, gen_name_calls, 2)], keys)

    @ddt.data(None, [], {"fake_set"}, {"fake_key": "fake_value"})
    def test__delete_metadata_wrong_params(self, keys):
        self.assertRaises(
            exceptions.InvalidArgumentsException,
            self.scenario._delete_metadata,
            "fake_share", keys=keys,
        )

    @ddt.data(
        {"keys": [i for i in range(30)]},
        {"keys": list(range(7)), "delete_size": 2},
        {"keys": list(range(7)), "delete_size": 3},
        {"keys": list(range(7)), "delete_size": 4},
    )
    def test__delete_metadata(self, params):
        share = {"id": "fake_share_id"}
        delete_size = params.get("delete_size", 3)
        keys = params.get("keys", [])
        scenario = self.scenario
        scenario.clients = mock.MagicMock()

        scenario._delete_metadata(share, **params)

        scenario.clients.return_value.shares.delete_metadata.assert_has_calls([
            mock.call(share["id"], keys[i:i + delete_size])
            for i in range(0, len(keys), delete_size)
        ])
