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

import ddt
import mock

from rally.plugins.openstack.scenarios.magnum import clusters
from tests.unit import test


@ddt.ddt
class MagnumClustersTestCase(test.ScenarioTestCase):

    @staticmethod
    def _get_context():
        context = test.get_test_context()
        context.update({
            "tenant": {
                "id": "rally_tenant_id",
                "cluster_template": "rally_cluster_template_uuid"
            }
        })
        return context

    @ddt.data(
        {"kwargs": {}},
        {"kwargs": {"fakearg": "f"}})
    def test_list_clusters(self, kwargs):
        scenario = clusters.ListClusters()
        scenario._list_clusters = mock.Mock()

        scenario.run(**kwargs)

        scenario._list_clusters.assert_called_once_with(**kwargs)

    def test_create_cluster_with_existing_ct_and_list_clusters(self):
        scenario = clusters.CreateAndListClusters()
        kwargs = {"cluster_template_uuid": "existing_cluster_template_uuid",
                  "fakearg": "f"}
        fake_cluster = mock.Mock()
        scenario._create_cluster = mock.Mock(return_value=fake_cluster)
        scenario._list_clusters = mock.Mock()

        scenario.run(2, **kwargs)

        scenario._create_cluster.assert_called_once_with(
            "existing_cluster_template_uuid", 2, **kwargs)
        scenario._list_clusters.assert_called_once_with(**kwargs)

    def test_create_and_list_clusters(self):
        context = self._get_context()
        scenario = clusters.CreateAndListClusters(context)
        fake_cluster = mock.Mock()
        kwargs = {"fakearg": "f"}
        scenario._create_cluster = mock.Mock(return_value=fake_cluster)
        scenario._list_clusters = mock.Mock()

        scenario.run(2, **kwargs)

        scenario._create_cluster.assert_called_once_with(
            "rally_cluster_template_uuid", 2, **kwargs)
        scenario._list_clusters.assert_called_once_with(**kwargs)
