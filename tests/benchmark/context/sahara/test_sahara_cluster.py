# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock
from oslo.config import cfg

from rally.benchmark.context.sahara import sahara_cluster
from tests import test

CONF = cfg.CONF

BASE_CTX = "rally.benchmark.context"
CTX = "rally.benchmark.context.sahara"
SCN = "rally.benchmark.scenarios"


class SaharaClusterTestCase(test.TestCase):

    def setUp(self):
        super(SaharaClusterTestCase, self).setUp()
        self.tenants_num = 2
        self.users_per_tenant = 2
        self.users = self.tenants_num * self.users_per_tenant
        self.task = mock.MagicMock()

        self.user_key = [{'id': i, 'tenant_id': j, 'endpoint': 'endpoint'}
                         for j in range(self.tenants_num)
                         for i in range(self.users_per_tenant)]
        self.images = dict((i, "42") for i in range(self.tenants_num))

        CONF.set_override("cluster_check_interval", 0, "benchmark")

    @property
    def context_without_cluster_keys(self):
        return {
            "config": {
                "users": {
                    "tenants": self.tenants_num,
                    "users_per_tenant": self.users_per_tenant,
                },
                "sahara_cluster": {
                    "flavor_id": "test_flavor",
                    "node_count": 2,
                    "plugin_name": "test_plugin",
                    "hadoop_version": "test_version"
                }
            },
            "admin": {"endpoint": mock.MagicMock()},
            "task": mock.MagicMock(),
            "users": self.user_key,
            "sahara_images": self.images
        }

    @mock.patch("%s.sahara_cluster.cleanup_utils" % CTX)
    @mock.patch("%s.sahara_cluster.utils.SaharaScenario._launch_cluster" % CTX,
                return_value=mock.MagicMock(id=42))
    @mock.patch("%s.sahara_cluster.osclients" % CTX)
    def test_setup_and_cleanup(self, mock_osclients,
                               mock_launch, mock_cleanup_utils):

        mock_sahara = mock_osclients.Clients(mock.MagicMock()).sahara()

        ctx = self.context_without_cluster_keys
        sahara_ctx = sahara_cluster.SaharaCluster(ctx)

        launch_cluster_calls = []

        for i in range(self.tenants_num):
            launch_cluster_calls.append(mock.call(
                plugin_name="test_plugin",
                hadoop_version="test_version",
                flavor_id="test_flavor",
                node_count=2,
                image_id=ctx["sahara_images"][i],
                floating_ip_pool=None,
                neutron_net_id=None,
                wait_active=False
            ))

        mock_sahara.clusters.get.side_effect = [
            mock.MagicMock(status="not-active"),
            mock.MagicMock(status="active")]
        sahara_ctx.setup()

        mock_launch.assert_has_calls(launch_cluster_calls)
        sahara_ctx.cleanup()
        self.assertEqual(
            self.tenants_num,
            len(mock_cleanup_utils.delete_clusters.mock_calls))
