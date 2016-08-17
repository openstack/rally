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

from rally.plugins.openstack.scenarios.ceilometer import samples
from tests.unit import test


BASE = "rally.plugins.openstack.scenarios.ceilometer"


class CeilometerSamplesTestCase(test.ScenarioTestCase):

    @mock.patch("%s.samples.ListMatchedSamples.run" % BASE)
    def test_all_list_samples(self, mock_list_matched_samples_run):
        metadata_query = {"a": "test"}
        limit = 10
        scenario = samples.ListSamples(self.context)
        scenario.run(metadata_query, limit)
        mock_list_matched_samples_run.assert_any_call(limit=10)
        mock_list_matched_samples_run.assert_any_call(
            metadata_query=metadata_query)
        mock_list_matched_samples_run.assert_any_call(
            filter_by_resource_id=True)
        mock_list_matched_samples_run.assert_any_call(
            filter_by_user_id=True)
        mock_list_matched_samples_run.assert_any_call(
            filter_by_project_id=True)

    @mock.patch("%s.samples.ListMatchedSamples.run" % BASE)
    def test_list_samples_without_limit_and_metadata(
            self,
            mock_list_matched_samples_run):
        scenario = samples.ListSamples()
        scenario.run()
        expected_call_args_list = [
            mock.call(filter_by_project_id=True),
            mock.call(filter_by_user_id=True),
            mock.call(filter_by_resource_id=True)
        ]
        self.assertSequenceEqual(
            expected_call_args_list,
            mock_list_matched_samples_run.call_args_list)

    def test_list_matched_samples(self):
        scenario = samples.ListMatchedSamples()
        scenario._list_samples = mock.MagicMock()
        context = {"user": {"tenant_id": "fake", "id": "fake_id"},
                   "tenant": {"id": "fake_id",
                              "resources": ["fake_resource"]}}
        scenario.context = context
        metadata_query = {"a": "test"}
        limit = 10
        scenario.run(True, True, True, metadata_query, limit)
        scenario._list_samples.assert_called_once_with(
            [{"field": "user_id", "value": "fake_id", "op": "eq"},
             {"field": "project_id", "value": "fake_id", "op": "eq"},
             {"field": "resource_id", "value": "fake_resource", "op": "eq"},
             {"field": "metadata.a", "value": "test", "op": "eq"}],
            10)
