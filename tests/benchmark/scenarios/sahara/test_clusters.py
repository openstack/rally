# Copyright 2014: Mirantis Inc.
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

from rally.benchmark.scenarios.sahara import clusters
from tests import test

SAHARA_CLUSTERS = "rally.benchmark.scenarios.sahara.clusters.SaharaClusters"
SAHARA_UTILS = 'rally.benchmark.scenarios.sahara.utils'


class SaharaNodeGroupTemplatesTestCase(test.TestCase):

    @mock.patch(SAHARA_CLUSTERS + "._delete_cluster")
    @mock.patch(SAHARA_CLUSTERS + "._launch_cluster",
                return_value=mock.MagicMock(id=42))
    @mock.patch(SAHARA_UTILS + '.SaharaScenario.clients')
    def test_create_and_delete_cluster(self, mock_clients, mock_launch_cluster,
                                       mock_delete_cluster):

        clusters_scenario = clusters.SaharaClusters()

        clusters_scenario.clients("keystone").tenant_id = "test_tenant"
        clusters_scenario.context = mock.MagicMock(return_value={
            "sahara_images": {"test_tenant": "test_image"}}
        )
        clusters_scenario.create_and_delete_cluster("test_flavor", 5,
                                                    "test_plugin",
                                                    "test_version")

        mock_launch_cluster.assert_called_once_with(
            flavor_id="test_flavor",
            image_id="test_image",
            node_count=5,
            plugin_name="test_plugin",
            hadoop_version="test_version")

        mock_delete_cluster.assert_called_once_with(
            mock_launch_cluster.return_value)
