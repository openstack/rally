# Copyright 2016: Mirantis Inc.
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

import functools

import mock

from rally.plugins.openstack.context import dataplane
from tests.unit import test

MOD = "rally.plugins.openstack.context.dataplane.heat."


class TestHeatWorkload(test.ScenarioTestCase):

    @mock.patch(MOD + "pkgutil")
    def test_get_data_resource(self, mock_pkgutil):
        mock_pkgutil.get_data.return_value = "fake_data"
        data = dataplane.heat.get_data([1, 2])
        self.assertEqual("fake_data", data)
        mock_pkgutil.get_data.assert_called_once_with(1, 2)

    @mock.patch(MOD + "open")
    def test_get_data_file(self, mock_open):
        data = dataplane.heat.get_data(1)
        self.assertEqual(mock_open.return_value.read.return_value, data)
        mock_open.assert_called_once_with(1)

    def test__get_context_parameter(self):
        user = [1, 2]
        tenant = [3, 4, {"one": 1}]
        self.context["tenants"] = {1: tenant}
        ctx = dataplane.heat.HeatDataplane(self.context)
        gcp = functools.partial(ctx._get_context_parameter, user, 1)
        self.assertEqual(1, gcp("user.0"))
        self.assertEqual(2, gcp("user.1"))
        self.assertEqual(3, gcp("tenant.0"))
        self.assertEqual(1, gcp("tenant.2.one"))

    @mock.patch(MOD + "osclients.Clients")
    def test__get_public_network_id(self, mock_clients):
        fake_net = {"id": "fake_id"}
        fake_nc = mock.Mock(name="fake_neutronclient")
        fake_nc.list_networks.return_value = {"networks": [fake_net]}
        mock_clients.neutron.return_value = fake_nc
        mock_clients.return_value = mock.Mock(
            neutron=mock.Mock(return_value=fake_nc))
        self.context["admin"] = {"credential": "fake_credential"}
        ctx = dataplane.heat.HeatDataplane(self.context)
        network_id = ctx._get_public_network_id()
        self.assertEqual("fake_id", network_id)
        mock_clients.assert_called_once_with("fake_credential")

    @mock.patch(MOD + "get_data")
    @mock.patch(MOD + "HeatDataplane._get_context_parameter")
    @mock.patch(MOD + "heat_utils")
    def test_setup(self,
                   mock_heat_utils,
                   mock_heat_dataplane__get_context_parameter,
                   mock_get_data):
        self.context.update({
            "config": {
                "heat_dataplane": {
                    "stacks_per_tenant": 1,
                    "template": "tpl.yaml",
                    "files": {"file1": "f1.yaml", "file2": "f2.yaml"},
                    "parameters": {"key": "value"},
                    "context_parameters": {"ctx.key": "ctx.value"},
                }
            },
            "users": [{"tenant_id": "t1", "keypair": {"name": "kp1"}}, ],
            "tenants": {"t1": {"networks": [{"router_id": "rid"}]}},
        })
        mock_heat_dataplane__get_context_parameter.return_value = "gcp"
        mock_get_data.side_effect = ["tpl", "sf1", "sf2"]
        ctx = dataplane.heat.HeatDataplane(self.context)
        ctx._get_public_network_id = mock.Mock(return_value="fake_net")
        ctx.setup()
        workloads = self.context["tenants"]["t1"]["stack_dataplane"]
        self.assertEqual(1, len(workloads))
        wl = workloads[0]
        fake_scenario = mock_heat_utils.HeatScenario.return_value
        self.assertEqual(fake_scenario._create_stack.return_value.id, wl[0])
        self.assertEqual("tpl", wl[1])
        self.assertIn("sf1", wl[2].values())
        self.assertIn("sf2", wl[2].values())
        expected = {
            "ctx.key": "gcp",
            "key": "value",
            "key_name": "kp1",
            "network_id": "fake_net",
            "router_id": "rid"}
        self.assertEqual(expected, wl[3])
