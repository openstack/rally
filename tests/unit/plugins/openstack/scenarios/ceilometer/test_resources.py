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
from rally.plugins.openstack.scenarios.ceilometer import resources
from tests.unit import test


BASE = "rally.plugins.openstack.scenarios.ceilometer"


class CeilometerResourcesTestCase(test.ScenarioTestCase):
    @mock.patch("%s.resources.ListMatchedResources.run" % BASE)
    def test_all_resource_list_queries(
            self, mock_list_matched_resources_run):
        metadata_query = {"a": "test"}
        start_time = "fake start time"
        end_time = "fake end time"
        limit = 100

        scenario = resources.ListResources(self.context)
        scenario.run(metadata_query, start_time, end_time, limit)
        mock_list_matched_resources_run.assert_any_call(limit=100)
        mock_list_matched_resources_run.assert_any_call(start_time=start_time,
                                                        end_time=end_time)
        mock_list_matched_resources_run.assert_any_call(end_time=end_time)
        mock_list_matched_resources_run.assert_any_call(start_time=start_time)
        mock_list_matched_resources_run.assert_any_call(
            metadata_query=metadata_query)
        mock_list_matched_resources_run.assert_any_call(
            filter_by_user_id=True)
        mock_list_matched_resources_run.assert_any_call(
            filter_by_project_id=True)
        mock_list_matched_resources_run.assert_any_call(
            filter_by_resource_id=True)

    def test_list_matched_resources(self):
        scenario = resources.ListMatchedResources(self.context)
        scenario._list_resources = mock.MagicMock()
        context = {"user": {"tenant_id": "fake", "id": "fake_id"},
                   "tenant": {"id": "fake_id",
                              "resources": ["fake_resource"]}}
        scenario.context = context

        metadata_query = {"a": "test"}
        start_time = "2015-09-09T00:00:00"
        end_time = "2015-09-10T00:00:00"
        limit = 100
        scenario.run(True, True, True, metadata_query,
                     start_time, end_time, limit)
        scenario._list_resources.assert_called_once_with(
            [{"field": "user_id", "value": "fake_id", "op": "eq"},
             {"field": "project_id", "value": "fake_id", "op": "eq"},
             {"field": "resource_id", "value": "fake_resource", "op": "eq"},
             {"field": "metadata.a", "value": "test", "op": "eq"},
             {"field": "timestamp", "value": "2015-09-09T00:00:00",
              "op": ">="},
             {"field": "timestamp", "value": "2015-09-10T00:00:00",
              "op": "<="}
             ],
            100)

    def test_get_tenant_resources(self):
        scenario = resources.GetTenantResources(self.context)
        resource_list = ["id1", "id2", "id3", "id4"]
        context = {"user": {"tenant_id": "fake"},
                   "tenant": {"id": "fake", "resources": resource_list}}
        scenario.context = context
        scenario._get_resource = mock.MagicMock()
        scenario.run()
        for resource_id in resource_list:
            scenario._get_resource.assert_any_call(resource_id)

    @mock.patch("%s.resources.ListMatchedResources.run" % BASE)
    def test_resource_list_queries_without_limit_and_metadata(
            self, mock_list_matched_resources_run):
        scenario = resources.ListResources()
        scenario.run()
        expected_call_args_list = [
            mock.call(filter_by_project_id=True),
            mock.call(filter_by_user_id=True),
            mock.call(filter_by_resource_id=True)
        ]
        self.assertSequenceEqual(
            expected_call_args_list,
            mock_list_matched_resources_run.call_args_list)

    def test_get_tenant_resources_with_exception(self):
        scenario = resources.GetTenantResources(self.context)
        resource_list = []
        context = {"user": {"tenant_id": "fake"},
                   "tenant": {"id": "fake", "resources": resource_list}}
        scenario.context = context
        self.assertRaises(exceptions.NotFoundException, scenario.run)
