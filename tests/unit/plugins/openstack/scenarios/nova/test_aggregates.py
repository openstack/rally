# Copyright 2016 IBM Corp.
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

from rally import exceptions
from rally.plugins.openstack.scenarios.nova import aggregates
from tests.unit import test


class NovaAggregatesTestCase(test.ScenarioTestCase):

    def test_list_aggregates(self):
        scenario = aggregates.ListAggregates()
        scenario._list_aggregates = mock.Mock()
        scenario.run()
        scenario._list_aggregates.assert_called_once_with()

    def test_create_and_list_aggregates(self):
        # Positive case
        scenario = aggregates.CreateAndListAggregates()
        scenario._create_aggregate = mock.Mock(return_value="agg1")
        scenario._list_aggregates = mock.Mock(return_value=("agg1", "agg2"))
        scenario.run(availability_zone="nova")
        scenario._create_aggregate.assert_called_once_with("nova")
        scenario._list_aggregates.assert_called_once_with()

        # Negative case 1: aggregate isn't created
        scenario._create_aggregate.return_value = None
        self.assertRaises(exceptions.RallyAssertionError,
                          scenario.run, availability_zone="nova")
        scenario._create_aggregate.assert_called_with("nova")

        # Negative case 2: aggregate was created but not included into list
        scenario._create_aggregate.return_value = "agg3"
        self.assertRaises(exceptions.RallyAssertionError,
                          scenario.run, availability_zone="nova")
        scenario._create_aggregate.assert_called_with("nova")
        scenario._list_aggregates.assert_called_with()

    def test_create_and_delete_aggregate(self):
        scenario = aggregates.CreateAndDeleteAggregate()
        scenario._create_aggregate = mock.Mock()
        scenario._delete_aggregate = mock.Mock()
        scenario.run(availability_zone="nova")
        scenario._create_aggregate.assert_called_once_with("nova")
        aggregate = scenario._create_aggregate.return_value
        scenario._delete_aggregate.assert_called_once_with(aggregate)

    def test_create_and_update_aggregate(self):
        scenario = aggregates.CreateAndUpdateAggregate()
        scenario._create_aggregate = mock.Mock()
        scenario._update_aggregate = mock.Mock()
        scenario.run(availability_zone="nova")
        scenario._create_aggregate.assert_called_once_with("nova")
        aggregate = scenario._create_aggregate.return_value
        scenario._update_aggregate.assert_called_once_with(aggregate)

    def test_create_aggregate_add_and_remove_host(self):
        fake_aggregate = "fake_aggregate"
        fake_hosts = [mock.Mock(service={"host": "fake_host_name"})]
        scenario = aggregates.CreateAggregateAddAndRemoveHost()
        scenario._create_aggregate = mock.MagicMock(
            return_value=fake_aggregate)
        scenario._list_hypervisors = mock.MagicMock(return_value=fake_hosts)
        scenario._aggregate_add_host = mock.MagicMock()
        scenario._aggregate_remove_host = mock.MagicMock()
        scenario.run(availability_zone="nova")
        scenario._create_aggregate.assert_called_once_with(
            "nova")
        scenario._list_hypervisors.assert_called_once_with()
        scenario._aggregate_add_host.assert_called_once_with(
            "fake_aggregate", "fake_host_name")
        scenario._aggregate_remove_host.assert_called_once_with(
            "fake_aggregate", "fake_host_name")

    def test_create_and_get_aggregate_details(self):
        scenario = aggregates.CreateAndGetAggregateDetails()
        scenario._create_aggregate = mock.Mock()
        scenario._get_aggregate_details = mock.Mock()
        scenario.run(availability_zone="nova")
        scenario._create_aggregate.assert_called_once_with("nova")
        aggregate = scenario._create_aggregate.return_value
        scenario._get_aggregate_details.assert_called_once_with(aggregate)

    def test_create_aggregate_add_host_and_boot_server(self):
        fake_aggregate = mock.Mock()
        fake_hosts = [mock.Mock(service={"host": "fake_host_name"})]
        fake_flavor = mock.MagicMock(id="flavor-id-0", ram=512, disk=1,
                                     vcpus=1)
        fake_metadata = {"test_metadata": "true"}
        fake_server = mock.MagicMock(id="server-id-0")
        setattr(fake_server, "OS-EXT-SRV-ATTR:hypervisor_hostname",
                "fake_host_name")
        fake_aggregate_kwargs = {"fake_arg1": "f"}

        scenario = aggregates.CreateAggregateAddHostAndBootServer()
        scenario._create_aggregate = mock.MagicMock(
            return_value=fake_aggregate)
        scenario._list_hypervisors = mock.MagicMock(return_value=fake_hosts)
        scenario._aggregate_add_host = mock.MagicMock()
        scenario._aggregate_set_metadata = mock.MagicMock()
        scenario._create_flavor = mock.MagicMock(return_value=fake_flavor)
        scenario._boot_server = mock.MagicMock(return_value=fake_server)
        self.admin_clients("nova").servers.get.return_value = fake_server

        scenario.run("img", fake_metadata, availability_zone="nova",
                     boot_server_kwargs=fake_aggregate_kwargs)
        scenario._create_aggregate.assert_called_once_with("nova")
        scenario._list_hypervisors.assert_called_once_with()
        scenario._aggregate_set_metadata.assert_called_once_with(
            fake_aggregate, fake_metadata)
        scenario._aggregate_add_host(fake_aggregate, "fake_host_name")
        scenario._create_flavor.assert_called_once_with(512, 1, 1)
        fake_flavor.set_keys.assert_called_once_with(fake_metadata)
        scenario._boot_server.assert_called_once_with("img", "flavor-id-0",
                                                      **fake_aggregate_kwargs)
        self.admin_clients("nova").servers.get.assert_called_once_with(
            "server-id-0")

        self.assertEqual(getattr(
            fake_server, "OS-EXT-SRV-ATTR:hypervisor_hostname"),
            "fake_host_name")

    def test_create_aggregate_add_host_and_boot_server_failure(self):
        fake_aggregate = mock.Mock()
        fake_hosts = [mock.Mock(service={"host": "fake_host_name"})]
        fake_flavor = mock.MagicMock(id="flavor-id-0", ram=512, disk=1,
                                     vcpus=1)
        fake_metadata = {"test_metadata": "true"}
        fake_server = mock.MagicMock(id="server-id-0")
        setattr(fake_server, "OS-EXT-SRV-ATTR:hypervisor_hostname",
                "wrong_host_name")
        fake_boot_server_kwargs = {"fake_arg1": "f"}

        scenario = aggregates.CreateAggregateAddHostAndBootServer()
        scenario._create_aggregate = mock.MagicMock(
            return_value=fake_aggregate)
        scenario._list_hypervisors = mock.MagicMock(return_value=fake_hosts)
        scenario._aggregate_add_host = mock.MagicMock()
        scenario._aggregate_set_metadata = mock.MagicMock()
        scenario._create_flavor = mock.MagicMock(return_value=fake_flavor)
        scenario._boot_server = mock.MagicMock(return_value=fake_server)
        self.admin_clients("nova").servers.get.return_value = fake_server

        self.assertRaises(exceptions.RallyException, scenario.run, "img",
                          fake_metadata, "nova", fake_boot_server_kwargs)
