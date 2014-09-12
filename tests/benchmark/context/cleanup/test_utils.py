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

from rally.benchmark.context.cleanup import utils
from rally.benchmark import scenarios
from tests import fakes
from tests import test


class CleanupUtilsTestCase(test.TestCase):

    def test_delete_neutron_resources(self):
        neutron = fakes.FakeClients().neutron()
        scenario = scenarios.neutron.utils.NeutronScenario()
        scenario.context = mock.Mock(return_value={"iteration": 1})
        scenario.clients = lambda ins: neutron

        network1 = scenario._create_network({})
        subnet1 = scenario._create_subnet(network1, 1, {})
        router1 = scenario._create_router({})
        # This also creates a port
        neutron.add_interface_router(router1["router"]["id"],
                                     {"subnet_id": subnet1["subnet"]["id"]})
        network2 = scenario._create_network({})
        scenario._create_subnet(network2, 1, {})
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

    def test_delete_cinder_resources(self):
        cinder = fakes.FakeClients().cinder()
        scenario = scenarios.cinder.utils.CinderScenario()
        scenario.clients = lambda ins: cinder
        vol1 = scenario._create_volume(1)
        scenario._create_snapshot(vol1.id)
        cinder.transfers.create("dummy")
        cinder.backups.create("dummy")

        total = lambda cinder: (len(cinder.volumes.list())
                                + len(cinder.volume_snapshots.list(
                                ))
                                + len(cinder.transfers.list())
                                + len(cinder.backups.list()))
        self.assertEqual(total(cinder), 4)
        utils.delete_cinder_resources(cinder)
        self.assertEqual(total(cinder), 0)

    def test_delete_nova_resources(self):
        nova = fakes.FakeClients().nova()
        nova.servers.create("dummy", None, None)
        nova.keypairs.create("dummy")
        nova.security_groups.create("dummy")
        total = lambda nova: (len(nova.servers.list())
                              + len(nova.keypairs.list())
                              + len(nova.security_groups.list()))
        self.assertEqual(total(nova), 4)
        utils.delete_nova_resources(nova)
        self.assertEqual(total(nova), 1)

    def test_delete_heat_resources(self):
        heat = fakes.FakeClients().heat()
        heat.stacks.create("dummy")
        total = lambda heat: (len(heat.stacks.list()))
        self.assertEqual(total(heat), 1)
        utils.delete_heat_resources(heat)
        self.assertEqual(total(heat), 0)

    def test_delete_designate_resources(self):
        designate = fakes.FakeClients().designate()
        designate.domains.create("dummy")
        total = lambda designate: (len(designate.domains.list()))
        self.assertEqual(total(designate), 1)
        utils.delete_designate_resources(designate)
        self.assertEqual(total(designate), 0)

    def test_delete_ceilometer_resources(self):
        ceilometer = fakes.FakeClients().ceilometer()
        ceilometer.alarms.create()
        total = lambda ceilometer: (len(ceilometer.alarms.list()))
        self.assertEqual(total(ceilometer), 1)
        utils.delete_ceilometer_resources(ceilometer, "dummy")
        self.assertEqual(total(ceilometer), 0)

    def test_delete_admin_quotas(self):
        tenant1 = {'id': 1}
        tenant2 = {'id': 2}
        client = fakes.FakeClients()
        utils.delete_admin_quotas(client, [tenant1, tenant2])
        self.assertFalse(client.nova().quotas.list())
        self.assertFalse(client.cinder().quotas.list())

    @mock.patch('rally.benchmark.wrappers.keystone.wrap')
    def test_delete_keystone_resources(self, mock_wrap):
        keystone = fakes.FakeClients().keystone()
        mock_wrap.return_value = keystone
        keystone.users.create("rally_keystone_dummy", None, None, None)
        total = lambda keystone: (len(keystone.users.list()))
        self.assertEqual(total(keystone), 1)
        utils.delete_keystone_resources(keystone)
        self.assertEqual(total(keystone), 0)

    def test_delete_glance_resources(self):
        glance = fakes.FakeClients().glance()
        glance.images.create("dummy", None, None, None)
        total = lambda glance: (len(glance.images.list()))
        self.assertEqual(total(glance), 1)
        utils.delete_glance_resources(glance, "dummy")
        self.assertEqual(total(glance), 0)
