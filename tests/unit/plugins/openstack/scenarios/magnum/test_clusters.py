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

from rally import exceptions
from rally.plugins.openstack.scenarios.magnum import clusters
from tests.unit import test


@ddt.ddt
class MagnumClustersTestCase(test.ScenarioTestCase):

    @staticmethod
    def _get_context():
        context = test.get_test_context()
        context.update({
            "tenant": {
                "id": "rally_tenant_id"
            },
            "user": {"id": "fake_user_id",
                     "credential": mock.MagicMock()},
            "config": {}
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
        context = self._get_context()
        scenario = clusters.CreateAndListClusters(context)
        kwargs = {"fakearg": "f"}
        fake_cluster1 = mock.Mock(uuid="a")
        fake_cluster2 = mock.Mock(uuid="b")
        fake_cluster3 = mock.Mock(uuid="c")
        scenario._create_cluster = mock.Mock(return_value=fake_cluster1)
        scenario._list_clusters = mock.Mock(return_value=[fake_cluster1,
                                                          fake_cluster2,
                                                          fake_cluster3])

        run_kwargs = kwargs.copy()
        run_kwargs["cluster_template_uuid"] = "existing_cluster_template_uuid"
        # Positive case
        scenario.run(2, **run_kwargs)

        scenario._create_cluster.assert_called_once_with(
            "existing_cluster_template_uuid", 2, keypair=mock.ANY, **kwargs)
        scenario._list_clusters.assert_called_once_with(**kwargs)

        # Negative case1: cluster isn't created
        scenario._create_cluster.return_value = None
        self.assertRaises(exceptions.RallyAssertionError,
                          scenario.run, 2, **run_kwargs)
        scenario._create_cluster.assert_called_with(
            "existing_cluster_template_uuid", 2, keypair=mock.ANY, **kwargs)

        # Negative case2: created cluster not in the list of available clusters
        scenario._create_cluster.return_value = mock.Mock(uuid="foo")
        self.assertRaises(exceptions.RallyAssertionError,
                          scenario.run, 2, **run_kwargs)
        scenario._create_cluster.assert_called_with(
            "existing_cluster_template_uuid", 2, keypair=mock.ANY, **kwargs)
        scenario._list_clusters.assert_called_with(**kwargs)

    def test_create_and_list_clusters(self):
        context = self._get_context()
        context.update({
            "tenant": {
                "cluster_template": "rally_cluster_template_uuid"
            }
        })

        scenario = clusters.CreateAndListClusters(context)
        fake_cluster1 = mock.Mock(uuid="a")
        fake_cluster2 = mock.Mock(uuid="b")
        fake_cluster3 = mock.Mock(uuid="c")
        kwargs = {"fakearg": "f"}
        scenario._create_cluster = mock.Mock(return_value=fake_cluster1)
        scenario._list_clusters = mock.Mock(return_value=[fake_cluster1,
                                                          fake_cluster2,
                                                          fake_cluster3])

        # Positive case
        scenario.run(2, **kwargs)

        scenario._create_cluster.assert_called_once_with(
            "rally_cluster_template_uuid", 2, keypair=mock.ANY, **kwargs)
        scenario._list_clusters.assert_called_once_with(**kwargs)

        # Negative case1: cluster isn't created
        scenario._create_cluster.return_value = None
        self.assertRaises(exceptions.RallyAssertionError,
                          scenario.run, 2, **kwargs)
        scenario._create_cluster.assert_called_with(
            "rally_cluster_template_uuid", 2, keypair=mock.ANY, **kwargs)

        # Negative case2: created cluster not in the list of available clusters
        scenario._create_cluster.return_value = mock.Mock(uuid="foo")
        self.assertRaises(exceptions.RallyAssertionError,
                          scenario.run, 2, **kwargs)
        scenario._create_cluster.assert_called_with(
            "rally_cluster_template_uuid", 2, keypair=mock.ANY, **kwargs)
        scenario._list_clusters.assert_called_with(**kwargs)
