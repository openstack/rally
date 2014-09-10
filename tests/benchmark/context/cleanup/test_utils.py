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


from rally.benchmark.context.cleanup import utils
from rally.benchmark import scenarios
from tests import fakes
from tests import test


class CleanupUtilsTestCase(test.TestCase):

    def test_delete_neutron_resources(self):
        neutron = fakes.FakeClients().neutron()
        scenario = scenarios.neutron.utils.NeutronScenario()
        scenario.clients = lambda ins: neutron

        network1 = scenario._create_network({})
        subnet1 = scenario._create_subnet(network1, {})
        router1 = scenario._create_router({})
        # This also creates a port
        neutron.add_interface_router(router1["router"]["id"],
                                     {"subnet_id": subnet1["subnet"]["id"]})
        network2 = scenario._create_network({})
        scenario._create_subnet(network2, {})
        scenario._create_router({})
        scenario._create_port(network2, {})

        total = lambda neutron: (len(neutron.list_networks()["networks"])
                                 + len(neutron.list_subnets()["subnets"])
                                 + len(neutron.list_routers()["routers"])
                                 + len(neutron.list_ports()["ports"]))

        self.assertEqual(total(neutron), 8)

        utils.delete_neutron_resources(neutron,
                                       network1["network"]["tenant_id"])

        self.assertEqual(total(neutron), 0)

    def test_delete_sahara_resources(self):

        sahara = fakes.FakeClients().sahara()
        utils.delete_sahara_resources(sahara)

        sahara.job_executions.delete.assert_called_once_with(42)
        sahara.jobs.delete.assert_called_once_with(42)
        sahara.job_binary_internals.delete.assert_called_once_with(42)
        sahara.job_binaries.delete.assert_called_once_with(42)
        sahara.data_sources.delete.assert_called_once_with(42)

        sahara.clusters.delete.assert_called_once_with(42)
        sahara.cluster_templates.delete.assert_called_once_with(42)
        sahara.node_group_templates.delete.assert_called_once_with(42)
