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

from rally.plugins.openstack.scenarios.nova import aggregates
from tests.unit import test


class NovaAggregatesTestCase(test.TestCase):

    def test_list_aggregates(self):
        scenario = aggregates.ListAggregates()
        scenario._list_aggregates = mock.Mock()
        scenario.run()
        scenario._list_aggregates.assert_called_once_with()

    def test_create_and_list_aggregates(self):
        scenario = aggregates.CreateAndListAggregates()
        scenario._create_aggregate = mock.Mock()
        scenario._list_aggregates = mock.Mock()
        scenario.run(availability_zone="nova")
        scenario._create_aggregate.assert_called_once_with("nova")
        scenario._list_aggregates.assert_called_once_with()

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
        fake_hosts = [mock.Mock(host_name="fake_host_name")]
        scenario = aggregates.CreateAggregateAddAndRemoveHost()
        scenario._create_aggregate = mock.MagicMock(
            return_value=fake_aggregate)
        scenario._list_hosts = mock.MagicMock(
            return_value=fake_hosts)
        scenario._aggregate_add_host = mock.MagicMock()
        scenario._aggregate_remove_host = mock.MagicMock()
        scenario.run(availability_zone="nova")
        scenario._create_aggregate.assert_called_once_with(
            "nova")
        scenario._list_hosts.assert_called_once_with(zone=None)
        scenario._aggregate_add_host.assert_called_once_with(
            "fake_aggregate", "fake_host_name")
        scenario._aggregate_remove_host.assert_called_once_with(
            "fake_aggregate", "fake_host_name")
