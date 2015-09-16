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

from rally.plugins.openstack.scenarios.ceilometer import stats
from tests.unit import test


class CeilometerStatsTestCase(test.ScenarioTestCase):
    def test_create_meter_and_get_stats(self):
        fake_meter = mock.MagicMock()
        kwargs = mock.MagicMock()
        scenario = stats.CeilometerStats(self.context)
        scenario._create_meter = mock.MagicMock(return_value=fake_meter)
        scenario._get_stats = mock.MagicMock()
        scenario.create_meter_and_get_stats(**kwargs)
        scenario._create_meter.assert_called_once_with(**kwargs)
        scenario._get_stats.assert_called_once_with(fake_meter.counter_name)
