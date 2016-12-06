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

import copy

import ddt
import mock
import six

from rally import consts as rally_consts
from rally import exceptions
from rally.plugins.openstack.context.manila import consts
from rally.plugins.openstack.context.manila import manila_share_networks
from tests.unit import test

MANILA_UTILS_PATH = ("rally.plugins.openstack.scenarios.manila.utils."
                     "ManilaScenario.")


class Fake(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getitem__(self, item):
        return getattr(self, item)

    def to_dict(self):
        return self.__dict__


@ddt.ddt
class ShareNetworksTestCase(test.TestCase):
    TENANTS_AMOUNT = 3
    USERS_PER_TENANT = 4
    SECURITY_SERVICES = [
        {"type": ss_type,
         "dns_ip": "fake_dns_ip_%s" % ss_type,
         "server": "fake_server_%s" % ss_type,
         "domain": "fake_domain_%s" % ss_type,
         "user": "fake_user_%s" % ss_type,
         "password": "fake_password_%s" % ss_type,
         "name": "fake_optional_name_%s" % ss_type}
        for ss_type in ("ldap", "kerberos", "active_directory")
    ]

    def _get_context(self, use_security_services=False, networks_per_tenant=2,
                     neutron_network_provider=True):
        tenants = {}
        for t_id in range(self.TENANTS_AMOUNT):
            tenants[six.text_type(t_id)] = {"name": six.text_type(t_id)}
            tenants[six.text_type(t_id)]["networks"] = []
            for i in range(networks_per_tenant):
                network = {"id": "fake_net_id_%s" % i}
                if neutron_network_provider:
                    network["subnets"] = ["fake_subnet_id_of_net_%s" % i]
                else:
                    network["cidr"] = "101.0.5.0/24"
                tenants[six.text_type(t_id)]["networks"].append(network)
        users = []
        for t_id in tenants.keys():
            for i in range(self.USERS_PER_TENANT):
                users.append(
                    {"id": i, "tenant_id": t_id, "credential": "fake"})
        context = {
            "config": {
                "users": {
                    "tenants": self.TENANTS_AMOUNT,
                    "users_per_tenant": self.USERS_PER_TENANT,
                    "random_user_choice": False,
                },
                consts.SHARE_NETWORKS_CONTEXT_NAME: {
                    "use_share_networks": True,
                    "share_networks": [],
                },
                consts.SECURITY_SERVICES_CONTEXT_NAME: {
                    "security_services": (
                        self.SECURITY_SERVICES
                        if use_security_services else [])
                },
                "network": {
                    "networks_per_tenant": networks_per_tenant,
                    "start_cidr": "101.0.5.0/24",
                },
            },
            "admin": {
                "credential": mock.MagicMock(),
            },
            "task": mock.MagicMock(),
            "users": users,
            "tenants": tenants,
            "user_choice_method": "random",
        }
        return context

    def setUp(self):
        super(self.__class__, self).setUp()
        self.ctxt_use_existing = {
            "task": mock.MagicMock(),
            "config": {
                "existing_users": {"foo": "bar"},
                consts.SHARE_NETWORKS_CONTEXT_NAME: {
                    "use_share_networks": True,
                    "share_networks": {
                        "tenant_1_id": ["sn_1_id", "sn_2_name"],
                        "tenant_2_name": ["sn_3_id", "sn_4_name", "sn_5_id"],
                    },
                },
            },
            "tenants": {
                "tenant_1_id": {"id": "tenant_1_id", "name": "tenant_1_name"},
                "tenant_2_id": {"id": "tenant_2_id", "name": "tenant_2_name"},
            },
            "users": [
                {"tenant_id": "tenant_1_id", "credential": {"c1": "foo"}},
                {"tenant_id": "tenant_2_id", "credential": {"c2": "bar"}},
            ],
        }
        self.existing_sns = [
            Fake(id="sn_%s_id" % i, name="sn_%s_name" % i) for i in range(1, 6)
        ]

    def test_init(self):
        context = {
            "task": mock.MagicMock(),
            "config": {
                consts.SHARE_NETWORKS_CONTEXT_NAME: {"foo": "bar"},
                "not_manila": {"not_manila_key": "not_manila_value"},
            },
        }

        inst = manila_share_networks.ShareNetworks(context)

        self.assertEqual(
            {"foo": "bar", "share_networks": {}, "use_share_networks": False},
            inst.config)
        self.assertIn(
            rally_consts.JSON_SCHEMA, inst.CONFIG_SCHEMA.get("$schema"))
        self.assertFalse(inst.CONFIG_SCHEMA.get("additionalProperties"))
        self.assertEqual("object", inst.CONFIG_SCHEMA.get("type"))
        props = inst.CONFIG_SCHEMA.get("properties", {})
        self.assertEqual({"type": "object"}, props.get("share_networks"))
        self.assertEqual({"type": "boolean"}, props.get("use_share_networks"))
        self.assertEqual(450, inst.get_order())
        self.assertEqual(
            consts.SHARE_NETWORKS_CONTEXT_NAME,
            inst.get_name())

    def test_setup_share_networks_disabled(self):
        ctxt = {
            "task": mock.MagicMock(),
            "config": {
                consts.SHARE_NETWORKS_CONTEXT_NAME: {
                    "use_share_networks": False,
                },
            },
            consts.SHARE_NETWORKS_CONTEXT_NAME: {
                "delete_share_networks": False,
            },
        }
        inst = manila_share_networks.ShareNetworks(ctxt)

        expected_ctxt = copy.deepcopy(inst.context)

        inst.setup()

        self.assertEqual(expected_ctxt, inst.context)

    @mock.patch("rally.osclients.Clients")
    @mock.patch(MANILA_UTILS_PATH + "_list_share_networks")
    def test_setup_use_existing_share_networks(
            self, mock_manila_scenario__list_share_networks, mock_clients):
        existing_sns = self.existing_sns
        expected_ctxt = copy.deepcopy(self.ctxt_use_existing)
        inst = manila_share_networks.ShareNetworks(self.ctxt_use_existing)
        mock_manila_scenario__list_share_networks.return_value = (
            self.existing_sns)
        expected_ctxt.update({
            "delete_share_networks": False,
            "tenants": {
                "tenant_1_id": {
                    "id": "tenant_1_id",
                    "name": "tenant_1_name",
                    consts.SHARE_NETWORKS_CONTEXT_NAME: {
                        "share_networks": [
                            sn.to_dict() for sn in existing_sns[0:2]],
                    },
                },
                "tenant_2_id": {
                    "id": "tenant_2_id",
                    "name": "tenant_2_name",
                    consts.SHARE_NETWORKS_CONTEXT_NAME: {
                        "share_networks": [
                            sn.to_dict() for sn in existing_sns[2:5]],
                    },
                },
            }
        })

        inst.setup()

        self.assertEqual(expected_ctxt["task"], inst.context.get("task"))
        self.assertEqual(expected_ctxt["config"], inst.context.get("config"))
        self.assertEqual(expected_ctxt["users"], inst.context.get("users"))
        self.assertEqual(
            False,
            inst.context.get(consts.SHARE_NETWORKS_CONTEXT_NAME, {}).get(
                "delete_share_networks"))
        self.assertEqual(expected_ctxt["tenants"], inst.context.get("tenants"))

    def test_setup_use_existing_share_networks_tenant_not_found(self):
        ctxt = copy.deepcopy(self.ctxt_use_existing)
        ctxt.update({"tenants": {}})
        inst = manila_share_networks.ShareNetworks(ctxt)

        self.assertRaises(exceptions.ContextSetupFailure, inst.setup)

    @mock.patch("rally.osclients.Clients")
    @mock.patch(MANILA_UTILS_PATH + "_list_share_networks")
    def test_setup_use_existing_share_networks_sn_not_found(
            self, mock_manila_scenario__list_share_networks, mock_clients):
        ctxt = copy.deepcopy(self.ctxt_use_existing)
        ctxt["config"][consts.SHARE_NETWORKS_CONTEXT_NAME][
            "share_networks"] = {"tenant_1_id": ["foo"]}
        inst = manila_share_networks.ShareNetworks(ctxt)
        mock_manila_scenario__list_share_networks.return_value = (
            self.existing_sns)

        self.assertRaises(exceptions.ContextSetupFailure, inst.setup)

    def test_setup_use_existing_share_networks_with_empty_list(self):
        ctxt = copy.deepcopy(self.ctxt_use_existing)
        ctxt["config"][consts.SHARE_NETWORKS_CONTEXT_NAME][
            "share_networks"] = {}
        inst = manila_share_networks.ShareNetworks(ctxt)

        self.assertRaises(exceptions.ContextSetupFailure, inst.setup)

    @ddt.data(True, False)
    @mock.patch("rally.osclients.Clients")
    @mock.patch(MANILA_UTILS_PATH + "_create_share_network")
    @mock.patch(MANILA_UTILS_PATH + "_add_security_service_to_share_network")
    def test_setup_autocreate_share_networks_with_security_services(
            self,
            neutron,
            mock_manila_scenario__add_security_service_to_share_network,
            mock_manila_scenario__create_share_network,
            mock_clients):
        networks_per_tenant = 2
        ctxt = self._get_context(
            networks_per_tenant=networks_per_tenant,
            neutron_network_provider=neutron,
            use_security_services=True,
        )
        inst = manila_share_networks.ShareNetworks(ctxt)
        for tenant_id in list(ctxt["tenants"].keys()):
            inst.context["tenants"][tenant_id][
                consts.SECURITY_SERVICES_CONTEXT_NAME] = {
                    "security_services": [
                        Fake(id="fake_id").to_dict() for i in (1, 2, 3)
                    ]
            }

        inst.setup()

        self.assertEqual(ctxt["task"], inst.context.get("task"))
        self.assertEqual(ctxt["config"], inst.context.get("config"))
        self.assertEqual(ctxt["users"], inst.context.get("users"))
        self.assertEqual(ctxt["tenants"], inst.context.get("tenants"))
        mock_add_security_service_to_share_network = (
            mock_manila_scenario__add_security_service_to_share_network)
        mock_add_security_service_to_share_network.assert_has_calls([
            mock.call(mock.ANY, mock.ANY)
            for i in range(
                self.TENANTS_AMOUNT *
                networks_per_tenant *
                len(self.SECURITY_SERVICES))])
        if neutron:
            sn_args = {
                "neutron_net_id": mock.ANY,
                "neutron_subnet_id": mock.ANY,
            }
        else:
            sn_args = {"nova_net_id": mock.ANY}
        expected_calls = [
            mock.call(**sn_args),
            mock.call().to_dict(),
            mock.ANY,
            mock.ANY,
            mock.ANY,
        ]
        mock_manila_scenario__create_share_network.assert_has_calls(
            expected_calls * (self.TENANTS_AMOUNT * networks_per_tenant))
        mock_clients.assert_has_calls([
            mock.call("fake", {}) for i in range(self.TENANTS_AMOUNT)])

    @ddt.data(True, False)
    @mock.patch("rally.osclients.Clients")
    @mock.patch(MANILA_UTILS_PATH + "_create_share_network")
    @mock.patch(MANILA_UTILS_PATH + "_add_security_service_to_share_network")
    def test_setup_autocreate_share_networks_wo_security_services(
            self,
            neutron,
            mock_manila_scenario__add_security_service_to_share_network,
            mock_manila_scenario__create_share_network,
            mock_clients):
        networks_per_tenant = 2
        ctxt = self._get_context(
            networks_per_tenant=networks_per_tenant,
            neutron_network_provider=neutron,
        )
        inst = manila_share_networks.ShareNetworks(ctxt)

        inst.setup()

        self.assertEqual(ctxt["task"], inst.context.get("task"))
        self.assertEqual(ctxt["config"], inst.context.get("config"))
        self.assertEqual(ctxt["users"], inst.context.get("users"))
        self.assertEqual(ctxt["tenants"], inst.context.get("tenants"))
        self.assertFalse(
            mock_manila_scenario__add_security_service_to_share_network.called)
        if neutron:
            sn_args = {
                "neutron_net_id": mock.ANY,
                "neutron_subnet_id": mock.ANY,
            }
        else:
            sn_args = {"nova_net_id": mock.ANY}
        expected_calls = [mock.call(**sn_args), mock.call().to_dict()]
        mock_manila_scenario__create_share_network.assert_has_calls(
            expected_calls * (self.TENANTS_AMOUNT * networks_per_tenant))
        mock_clients.assert_has_calls([
            mock.call("fake", {}) for i in range(self.TENANTS_AMOUNT)])

    @mock.patch("rally.osclients.Clients")
    @mock.patch(MANILA_UTILS_PATH + "_create_share_network")
    @mock.patch(MANILA_UTILS_PATH + "_add_security_service_to_share_network")
    def test_setup_autocreate_share_networks_wo_networks(
            self,
            mock_manila_scenario__add_security_service_to_share_network,
            mock_manila_scenario__create_share_network,
            mock_clients):
        ctxt = self._get_context(networks_per_tenant=0)
        inst = manila_share_networks.ShareNetworks(ctxt)

        inst.setup()

        self.assertEqual(ctxt["task"], inst.context.get("task"))
        self.assertEqual(ctxt["config"], inst.context.get("config"))
        self.assertEqual(ctxt["users"], inst.context.get("users"))
        self.assertEqual(ctxt["tenants"], inst.context.get("tenants"))
        self.assertFalse(
            mock_manila_scenario__add_security_service_to_share_network.called)
        expected_calls = [mock.call(), mock.call().to_dict()]
        mock_manila_scenario__create_share_network.assert_has_calls(
            expected_calls * self.TENANTS_AMOUNT)
        mock_clients.assert_has_calls([
            mock.call("fake", {}) for i in range(self.TENANTS_AMOUNT)])

    @mock.patch("rally.osclients.Clients")
    @mock.patch(MANILA_UTILS_PATH + "_delete_share_network")
    @mock.patch(MANILA_UTILS_PATH + "_list_share_servers")
    @mock.patch(MANILA_UTILS_PATH + "_list_share_networks")
    def test_cleanup_used_existing_share_networks(
            self,
            mock_manila_scenario__list_share_networks,
            mock_manila_scenario__list_share_servers,
            mock_manila_scenario__delete_share_network,
            mock_clients):
        inst = manila_share_networks.ShareNetworks(self.ctxt_use_existing)
        mock_manila_scenario__list_share_networks.return_value = (
            self.existing_sns)
        inst.setup()

        inst.cleanup()

        self.assertFalse(mock_manila_scenario__list_share_servers.called)
        self.assertFalse(mock_manila_scenario__delete_share_network.called)
        self.assertEqual(2, mock_clients.call_count)
        for user in self.ctxt_use_existing["users"]:
            self.assertIn(mock.call(user["credential"], {}),
                          mock_clients.mock_calls)

    @ddt.data(True, False)
    @mock.patch("rally.task.utils.wait_for_status")
    @mock.patch("rally.osclients.Clients")
    @mock.patch(MANILA_UTILS_PATH + "_delete_share_network")
    @mock.patch(MANILA_UTILS_PATH + "_create_share_network")
    @mock.patch(MANILA_UTILS_PATH + "_add_security_service_to_share_network")
    @mock.patch(MANILA_UTILS_PATH + "_list_share_servers")
    def test_cleanup_autocreated_share_networks(
            self, use_security_services,
            mock_manila_scenario__list_share_servers,
            mock_manila_scenario__add_security_service_to_share_network,
            mock_manila_scenario__create_share_network,
            mock_manila_scenario__delete_share_network,
            mock_clients,
            mock_wait_for_status):
        fake_share_servers = ["fake_share_server"]
        mock_manila_scenario__list_share_servers.return_value = (
            fake_share_servers)
        networks_per_tenant = 2
        ctxt = self._get_context(
            networks_per_tenant=networks_per_tenant,
            use_security_services=use_security_services,
        )
        inst = manila_share_networks.ShareNetworks(ctxt)
        for tenant_id in list(ctxt["tenants"].keys()):
            inst.context["tenants"][tenant_id][
                consts.SECURITY_SERVICES_CONTEXT_NAME] = {
                    "security_services": [
                        Fake(id="fake_id").to_dict() for i in (1, 2, 3)
                    ]
            }
        inst.setup()

        mock_clients.assert_has_calls([
            mock.call("fake", {}) for i in range(self.TENANTS_AMOUNT)])

        inst.cleanup()

        self.assertEqual(self.TENANTS_AMOUNT * 4, mock_clients.call_count)
        self.assertEqual(
            self.TENANTS_AMOUNT * networks_per_tenant,
            mock_manila_scenario__list_share_servers.call_count)
        mock_manila_scenario__list_share_servers.assert_has_calls(
            [mock.call(search_opts=mock.ANY)])
        self.assertEqual(
            self.TENANTS_AMOUNT * networks_per_tenant,
            mock_manila_scenario__delete_share_network.call_count)
        self.assertEqual(
            self.TENANTS_AMOUNT * networks_per_tenant,
            mock_wait_for_status.call_count)
        mock_wait_for_status.assert_has_calls([
            mock.call(
                fake_share_servers[0],
                ready_statuses=["deleted"],
                check_deletion=True,
                update_resource=mock.ANY,
                timeout=180,
                check_interval=2),
        ])
