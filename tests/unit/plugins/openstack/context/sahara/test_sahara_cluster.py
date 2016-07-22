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
from oslo_config import cfg

from rally import exceptions
from rally.plugins.openstack.context.sahara import sahara_cluster
from tests.unit import test

CONF = cfg.CONF

CTX = "rally.plugins.openstack.context.sahara"


class SaharaClusterTestCase(test.ScenarioTestCase):

    patch_benchmark_utils = False

    def setUp(self):
        super(SaharaClusterTestCase, self).setUp()
        self.tenants_num = 2
        self.users_per_tenant = 2
        self.users = self.tenants_num * self.users_per_tenant

        self.tenants = {}
        self.users_key = []

        for i in range(self.tenants_num):
            self.tenants[str(i)] = {"id": str(i), "name": str(i),
                                    "sahara": {"image": "42"}}
            for j in range(self.users_per_tenant):
                self.users_key.append({"id": "%s_%s" % (str(i), str(j)),
                                       "tenant_id": str(i),
                                       "credential": mock.MagicMock()})

        CONF.set_override("sahara_cluster_check_interval", 0, "benchmark",
                          enforce_type=True)

        self.context.update({
            "config": {
                "users": {
                    "tenants": self.tenants_num,
                    "users_per_tenant": self.users_per_tenant
                },
                "sahara_cluster": {
                    "master_flavor_id": "test_flavor_m",
                    "worker_flavor_id": "test_flavor_w",
                    "workers_count": 2,
                    "plugin_name": "test_plugin",
                    "hadoop_version": "test_version"
                }
            },
            "admin": {"credential": mock.MagicMock()},
            "users": self.users_key,
            "tenants": self.tenants
        })

    @mock.patch("%s.sahara_cluster.resource_manager.cleanup" % CTX)
    @mock.patch("%s.sahara_cluster.utils.SaharaScenario._launch_cluster" % CTX,
                return_value=mock.MagicMock(id=42))
    def test_setup_and_cleanup(self, mock_sahara_scenario__launch_cluster,
                               mock_cleanup):
        sahara_ctx = sahara_cluster.SaharaCluster(self.context)

        launch_cluster_calls = []

        for i in self.tenants:
            launch_cluster_calls.append(mock.call(
                flavor_id=None,
                plugin_name="test_plugin",
                hadoop_version="test_version",
                master_flavor_id="test_flavor_m",
                worker_flavor_id="test_flavor_w",
                workers_count=2,
                image_id=self.context["tenants"][i]["sahara"]["image"],
                floating_ip_pool=None,
                volumes_per_node=None,
                volumes_size=1,
                auto_security_group=True,
                security_groups=None,
                node_configs=None,
                cluster_configs=None,
                enable_anti_affinity=False,
                enable_proxy=False,
                wait_active=False,
                use_autoconfig=True
            ))

        self.clients("sahara").clusters.get.side_effect = [
            mock.MagicMock(status="not-active"),
            mock.MagicMock(status="active")]
        sahara_ctx.setup()

        mock_sahara_scenario__launch_cluster.assert_has_calls(
            launch_cluster_calls)
        sahara_ctx.cleanup()
        mock_cleanup.assert_called_once_with(names=["sahara.clusters"],
                                             users=self.context["users"])

    @mock.patch("%s.sahara_cluster.utils.SaharaScenario._launch_cluster" % CTX,
                return_value=mock.MagicMock(id=42))
    def test_setup_and_cleanup_error(self,
                                     mock_sahara_scenario__launch_cluster):
        sahara_ctx = sahara_cluster.SaharaCluster(self.context)

        launch_cluster_calls = []

        for i in self.tenants:
            launch_cluster_calls.append(mock.call(
                flavor_id=None,
                plugin_name="test_plugin",
                hadoop_version="test_version",
                master_flavor_id="test_flavor_m",
                worker_flavor_id="test_flavor_w",
                workers_count=2,
                image_id=self.context["tenants"][i]["sahara"]["image"],
                floating_ip_pool=None,
                volumes_per_node=None,
                volumes_size=1,
                auto_security_groups=True,
                security_groups=None,
                node_configs=None,
                cluster_configs=None,
                wait_active=False,
                use_autoconfig=True
            ))

        self.clients("sahara").clusters.get.side_effect = [
            mock.MagicMock(status="not-active"),
            mock.MagicMock(status="error")
        ]

        self.assertRaises(exceptions.SaharaClusterFailure, sahara_ctx.setup)
