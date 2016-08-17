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

    def test_get_stats(self):
        scenario = stats.GetStats(self.context)
        scenario._get_stats = mock.MagicMock()
        context = {"user": {"tenant_id": "fake", "id": "fake_id"},
                   "tenant": {"id": "fake_id",
                              "resources": ["fake_resource"]}}
        metadata_query = {"a": "test"}
        period = 10
        groupby = "user_id"
        aggregates = "sum"
        scenario.context = context
        scenario.run("fake_meter", True, True, True, metadata_query,
                     period, groupby, aggregates)
        scenario._get_stats.assert_called_once_with(
            "fake_meter",
            [{"field": "user_id", "value": "fake_id", "op": "eq"},
             {"field": "project_id", "value": "fake_id", "op": "eq"},
             {"field": "resource_id", "value": "fake_resource", "op": "eq"},
             {"field": "metadata.a", "value": "test", "op": "eq"}],
            10,
            "user_id",
            "sum"
        )
