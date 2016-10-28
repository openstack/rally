# Copyright 2013 Cisco Systems Inc.
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

from rally.plugins.openstack.scenarios.nova import hypervisors
from tests.unit import test


class NovaHypervisorsTestCase(test.ScenarioTestCase):
    def test_list_hypervisors(self):
        scenario = hypervisors.ListHypervisors(self.context)
        scenario._list_hypervisors = mock.Mock()
        scenario.run(detailed=False)
        scenario._list_hypervisors.assert_called_once_with(False)

    def test_list_and_get_hypervisors(self):
        scenario = hypervisors.ListAndGetHypervisors(self.context)
        scenario._list_hypervisors = mock.MagicMock(detailed=False)
        scenario._get_hypervisor = mock.MagicMock()
        scenario.run(detailed=False)

        scenario._list_hypervisors.assert_called_once_with(False)
        for hypervisor in scenario._list_hypervisors.return_value:
            scenario._get_hypervisor.assert_called_once_with(hypervisor)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "nova.get_hypervisor")

    def test_statistics_hypervisors(self):
        scenario = hypervisors.StatisticsHypervisors(self.context)
        scenario._statistics_hypervisors = mock.Mock()
        scenario.run()
        scenario._statistics_hypervisors.assert_called_once_with()

    def test_list_and_get_uptime_hypervisors(self):
        scenario = hypervisors.ListAndGetUptimeHypervisors(self.context)
        scenario._list_hypervisors = mock.MagicMock(detailed=False)
        scenario._uptime_hypervisor = mock.MagicMock()
        scenario.run(detailed=False)

        scenario._list_hypervisors.assert_called_once_with(False)
        for hypervisor in scenario._list_hypervisors.return_value:
            scenario._uptime_hypervisor.assert_called_once_with(hypervisor)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "nova.uptime_hypervisor")

    def test_list_and_search_hypervisors(self):
        fake_hypervisors = [mock.Mock(hypervisor_hostname="fake_hostname")]
        scenario = hypervisors.ListAndSearchHypervisors(self.context)
        scenario._list_hypervisors = mock.MagicMock(
            return_value=fake_hypervisors)
        scenario._search_hypervisors = mock.MagicMock()
        scenario.run(detailed=False)

        scenario._list_hypervisors.assert_called_once_with(False)
        scenario._search_hypervisors.assert_called_once_with(
            "fake_hostname", atomic_action=False)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "nova.search_1_hypervisors")
