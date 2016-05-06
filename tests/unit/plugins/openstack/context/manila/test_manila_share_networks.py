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

import mock

from rally.common import utils
from rally import consts as rally_consts
from rally import exceptions
from rally.plugins.openstack.context.manila import consts
from rally.plugins.openstack.context.manila import manila_share_networks
from tests.unit import test

MANILA_UTILS_PATH = ("rally.plugins.openstack.scenarios.manila.utils."
                     "ManilaScenario.")


class ManilaSampleGeneratorTestCase(test.TestCase):
    def setUp(self):
        super(ManilaSampleGeneratorTestCase, self).setUp()
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
            type("ShareNetwork", (object, ), {
                "id": "sn_%s_id" % i, "name": "sn_%s_name" % i})()
            for i in range(1, 6)
        ]

    def test_init(self):
        context = {
            "task": mock.MagicMock(),
            "config": {
                consts.SHARE_NETWORKS_CONTEXT_NAME: {"foo": "bar"},
                "not_manila": {"not_manila_key": "not_manila_value"},
            },
        }

        inst = manila_share_networks.ManilaShareNetworks(context)

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
            consts.SHARE_NETWORKS_CONTEXT_NAME: {},
        }
        inst = manila_share_networks.ManilaShareNetworks(ctxt)

        expected_ctxt = copy.deepcopy(inst.context)

        inst.setup()

        self.assertEqual(expected_ctxt, inst.context)

    @mock.patch("rally.osclients.Clients")
    @mock.patch(MANILA_UTILS_PATH + "_list_share_networks")
    def test_setup_use_existing_share_networks(
            self, mock_manila_scenario__list_share_networks, mock_clients):
        existing_sns = self.existing_sns
        expected_ctxt = copy.deepcopy(self.ctxt_use_existing)
        inst = manila_share_networks.ManilaShareNetworks(
            self.ctxt_use_existing)
        mock_manila_scenario__list_share_networks.return_value = (
            self.existing_sns)
        expected_ctxt.update({
            "delete_share_networks": False,
            "tenants": {
                "tenant_1_id": {
                    "id": "tenant_1_id",
                    "name": "tenant_1_name",
                    consts.SHARE_NETWORKS_CONTEXT_NAME: {
                        "share_networks": [sn for sn in existing_sns[0:2]],
                        "sn_iterator": mock.ANY,
                    },
                },
                "tenant_2_id": {
                    "id": "tenant_2_id",
                    "name": "tenant_2_name",
                    consts.SHARE_NETWORKS_CONTEXT_NAME: {
                        "share_networks": [sn for sn in existing_sns[2:5]],
                        "sn_iterator": mock.ANY,
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
        for i, sns in ((1, existing_sns[0:2]), (2, existing_sns[2:5])):
            self.assertIsInstance(
                inst.context["tenants"]["tenant_%s_id" % i][
                    consts.SHARE_NETWORKS_CONTEXT_NAME]["sn_iterator"],
                utils.RAMInt)
            for j in range(12):
                self.assertEqual(
                    j,
                    next(inst.context["tenants"]["tenant_%s_id" % i][
                        consts.SHARE_NETWORKS_CONTEXT_NAME]["sn_iterator"]))

    def test_setup_use_existing_share_networks_tenant_not_found(self):
        ctxt = copy.deepcopy(self.ctxt_use_existing)
        ctxt.update({"tenants": {}})
        inst = manila_share_networks.ManilaShareNetworks(ctxt)

        self.assertRaises(exceptions.ContextSetupFailure, inst.setup)

    @mock.patch("rally.osclients.Clients")
    @mock.patch(MANILA_UTILS_PATH + "_list_share_networks")
    def test_setup_use_existing_share_networks_sn_not_found(
            self, mock_manila_scenario__list_share_networks, mock_clients):
        ctxt = copy.deepcopy(self.ctxt_use_existing)
        ctxt["config"][consts.SHARE_NETWORKS_CONTEXT_NAME][
            "share_networks"] = {"tenant_1_id": ["foo"]}
        inst = manila_share_networks.ManilaShareNetworks(ctxt)
        mock_manila_scenario__list_share_networks.return_value = (
            self.existing_sns)

        self.assertRaises(exceptions.ContextSetupFailure, inst.setup)

    def test_setup_use_existing_share_networks_with_empty_list(self):
        ctxt = copy.deepcopy(self.ctxt_use_existing)
        ctxt["config"][consts.SHARE_NETWORKS_CONTEXT_NAME][
            "share_networks"] = {}
        inst = manila_share_networks.ManilaShareNetworks(ctxt)

        self.assertRaises(exceptions.ContextSetupFailure, inst.setup)
