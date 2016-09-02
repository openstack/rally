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

from rally.plugins.openstack.scenarios.sahara import clusters
from tests.unit import test

BASE = "rally.plugins.openstack.scenarios.sahara.clusters"


class SaharaClustersTestCase(test.ScenarioTestCase):

    @mock.patch("%s.CreateAndDeleteCluster._delete_cluster" % BASE)
    @mock.patch("%s.CreateAndDeleteCluster._launch_cluster" % BASE,
                return_value=mock.MagicMock(id=42))
    def test_create_and_delete_cluster(self,
                                       mock_launch_cluster,
                                       mock_delete_cluster):
        scenario = clusters.CreateAndDeleteCluster(self.context)

        scenario.context = {
            "tenant": {
                "sahara": {
                    "image": "test_image",
                }
            }
        }

        scenario.run(master_flavor="test_flavor_m",
                     worker_flavor="test_flavor_w",
                     workers_count=5,
                     plugin_name="test_plugin",
                     hadoop_version="test_version")

        mock_launch_cluster.assert_called_once_with(
            flavor_id=None,
            master_flavor_id="test_flavor_m",
            worker_flavor_id="test_flavor_w",
            image_id="test_image",
            workers_count=5,
            plugin_name="test_plugin",
            hadoop_version="test_version",
            floating_ip_pool=None,
            volumes_per_node=None,
            volumes_size=None,
            auto_security_group=None,
            security_groups=None,
            node_configs=None,
            cluster_configs=None,
            enable_anti_affinity=False,
            enable_proxy=False,
            use_autoconfig=True)

        mock_delete_cluster.assert_called_once_with(
            mock_launch_cluster.return_value)

    @mock.patch("%s.CreateAndDeleteCluster._delete_cluster" % BASE)
    @mock.patch("%s.CreateAndDeleteCluster._launch_cluster" % BASE,
                return_value=mock.MagicMock(id=42))
    def test_create_and_delete_cluster_deprecated_flavor(self,
                                                         mock_launch_cluster,
                                                         mock_delete_cluster):
        scenario = clusters.CreateAndDeleteCluster(self.context)

        scenario.context = {
            "tenant": {
                "sahara": {
                    "image": "test_image",
                }
            }
        }
        scenario.run(flavor="test_deprecated_arg",
                     master_flavor=None,
                     worker_flavor=None,
                     workers_count=5,
                     plugin_name="test_plugin",
                     hadoop_version="test_version")

        mock_launch_cluster.assert_called_once_with(
            flavor_id="test_deprecated_arg",
            master_flavor_id=None,
            worker_flavor_id=None,
            image_id="test_image",
            workers_count=5,
            plugin_name="test_plugin",
            hadoop_version="test_version",
            floating_ip_pool=None,
            volumes_per_node=None,
            volumes_size=None,
            auto_security_group=None,
            security_groups=None,
            node_configs=None,
            cluster_configs=None,
            enable_anti_affinity=False,
            enable_proxy=False,
            use_autoconfig=True)

        mock_delete_cluster.assert_called_once_with(
            mock_launch_cluster.return_value)

    @mock.patch("%s.CreateScaleDeleteCluster._delete_cluster" % BASE)
    @mock.patch("%s.CreateScaleDeleteCluster._scale_cluster" % BASE)
    @mock.patch("%s.CreateScaleDeleteCluster._launch_cluster" % BASE,
                return_value=mock.MagicMock(id=42))
    def test_create_scale_delete_cluster(self,
                                         mock_launch_cluster,
                                         mock_scale_cluster,
                                         mock_delete_cluster):
        self.clients("sahara").clusters.get.return_value = mock.MagicMock(
            id=42, status="active"
        )
        scenario = clusters.CreateScaleDeleteCluster(self.context)

        scenario.context = {
            "tenant": {
                "sahara": {
                    "image": "test_image",
                }
            }
        }
        scenario.run(master_flavor="test_flavor_m",
                     worker_flavor="test_flavor_w",
                     workers_count=5,
                     deltas=[1, -1],
                     plugin_name="test_plugin",
                     hadoop_version="test_version")

        mock_launch_cluster.assert_called_once_with(
            flavor_id=None,
            master_flavor_id="test_flavor_m",
            worker_flavor_id="test_flavor_w",
            image_id="test_image",
            workers_count=5,
            plugin_name="test_plugin",
            hadoop_version="test_version",
            floating_ip_pool=None,
            volumes_per_node=None,
            volumes_size=None,
            auto_security_group=None,
            security_groups=None,
            node_configs=None,
            cluster_configs=None,
            enable_anti_affinity=False,
            enable_proxy=False,
            use_autoconfig=True)

        mock_scale_cluster.assert_has_calls([
            mock.call(
                self.clients("sahara").clusters.get.return_value,
                1),
            mock.call(
                self.clients("sahara").clusters.get.return_value,
                -1),
        ])

        mock_delete_cluster.assert_called_once_with(
            self.clients("sahara").clusters.get.return_value)
