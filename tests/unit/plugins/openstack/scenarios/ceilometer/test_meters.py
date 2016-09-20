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


BASE = "rally.plugins.openstack.scenarios.ceilometer"


class CeilometerMetersTestCase(test.ScenarioTestCase):
    @mock.patch("%s.meters.ListMatchedMeters.run" % BASE)
    def test_all_meter_list_queries(
            self, mock_list_matched_meters_run):
        scenario = meters.ListMeters(self.context)
        metadata_query = {"a": "test"}
        limit = 100

        scenario.run(metadata_query, limit)

        mock_list_matched_meters_run.assert_any_call(limit=100)
        mock_list_matched_meters_run.assert_any_call(
            metadata_query=metadata_query)
        mock_list_matched_meters_run.assert_any_call(filter_by_user_id=True)
        mock_list_matched_meters_run.assert_any_call(filter_by_project_id=True)
        mock_list_matched_meters_run.assert_any_call(
            filter_by_resource_id=True)

    @mock.patch("%s.meters.ListMatchedMeters.run" % BASE)
    def test_meter_list_queries_without_limit_and_metadata(
            self, mock_list_matched_meters_run):

        scenario = meters.ListMeters(self.context)
        scenario.run()
        expected_call_args_list = [
            mock.call(filter_by_project_id=True),
            mock.call(filter_by_user_id=True),
            mock.call(filter_by_resource_id=True)
        ]
        self.assertSequenceEqual(
            expected_call_args_list,
            mock_list_matched_meters_run.call_args_list)

    @mock.patch("%s.meters.ListMatchedMeters._list_meters" % BASE)
    def test_list_matched_meters(
            self, mock_list_matched_meters__list_meters):
        mock_func = mock_list_matched_meters__list_meters
        scenario = meters.ListMatchedMeters(self.context)
        context = {"user": {"tenant_id": "fake", "id": "fake_id"},
                   "tenant": {"id": "fake_id",
                              "resources": ["fake_resource"]}}
        scenario.context = context

        metadata_query = {"a": "test"}
        limit = 100
        scenario.run(True, True, True, metadata_query, limit)
        mock_func.assert_called_once_with(
            [{"field": "user_id", "value": "fake_id", "op": "eq"},
             {"field": "project_id", "value": "fake_id", "op": "eq"},
             {"field": "resource_id", "value": "fake_resource", "op": "eq"},
             {"field": "metadata.a", "value": "test", "op": "eq"}],
            100)
