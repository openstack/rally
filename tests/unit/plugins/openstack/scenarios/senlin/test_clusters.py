# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock

from rally.plugins.openstack.scenarios.senlin import clusters
from tests.unit import test


class SenlinClustersTestCase(test.ScenarioTestCase):

    def test_create_and_delete_cluster(self):
        profile_spec = {"k1": "v1"}
        mock_profile = mock.Mock(id="fake_profile_id")
        mock_cluster = mock.Mock()
        scenario = clusters.SenlinClusters(self.context)
        scenario._create_cluster = mock.Mock(return_value=mock_cluster)
        scenario._create_profile = mock.Mock(return_value=mock_profile)
        scenario._delete_cluster = mock.Mock()
        scenario._delete_profile = mock.Mock()

        scenario.create_and_delete_profile_cluster(profile_spec,
                                                   desired_capacity=1,
                                                   min_size=0,
                                                   max_size=3,
                                                   timeout=60,
                                                   metadata={"k2": "v2"})

        scenario._create_profile.assert_called_once_with(profile_spec)
        scenario._create_cluster.assert_called_once_with("fake_profile_id",
                                                         1, 0, 3, 60,
                                                         {"k2": "v2"})
        scenario._delete_cluster.assert_called_once_with(mock_cluster)
        scenario._delete_profile.assert_called_once_with(mock_profile)
