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

from rally.plugins.openstack.scenarios.ceilometer import meters
from tests.unit import test


class CeilometerMetersTestCase(test.ScenarioTestCase):
    def test_all_meter_list_queries(self):
        scenario = meters.CeilometerMeters(self.context)
        scenario.list_matched_meters = mock.MagicMock()
        metadata_query = {"a": "test"}
        limit = 100

        scenario.list_meters(metadata_query, limit)
        scenario.list_matched_meters.assert_any_call(limit=100)
        scenario.list_matched_meters.assert_any_call(
            metadata_query=metadata_query)
        scenario.list_matched_meters.assert_any_call(filter_by_user_id=True)
        scenario.list_matched_meters.assert_any_call(filter_by_project_id=True)
        scenario.list_matched_meters.assert_any_call(
            filter_by_resource_id=True)

    def test_meter_list_queries_without_limit_and_metadata(self):
        scenario = meters.CeilometerMeters(self.context)
        scenario.list_matched_meters = mock.MagicMock()
        scenario.list_meters()
        expected_call_args_list = [
            mock.call(filter_by_project_id=True),
            mock.call(filter_by_user_id=True),
            mock.call(filter_by_resource_id=True)
        ]
        self.assertSequenceEqual(expected_call_args_list,
                                 scenario.list_matched_meters.call_args_list)

    def test_list_matched_meters(self):
        scenario = meters.CeilometerMeters(self.context)
        scenario._list_meters = mock.MagicMock()
        context = {"user": {"tenant_id": "fake", "id": "fake_id"},
                   "tenant": {"id": "fake_id",
                              "resources": ["fake_resource"]}}
        scenario.context = context

        metadata_query = {"a": "test"}
        limit = 100
        scenario.list_matched_meters(True, True, True, metadata_query, limit)
        scenario._list_meters.assert_called_once_with(
            [{"field": "user_id", "value": "fake_id", "op": "eq"},
             {"field": "project_id", "value": "fake_id", "op": "eq"},
             {"field": "resource_id", "value": "fake_resource", "op": "eq"},
             {"field": "metadata.a", "value": "test", "op": "eq"}],
            100)
