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


import copy

import mock

from rally.plugins.openstack.context.magnum import clusters
from tests.unit import test

CTX = "rally.plugins.openstack.context.magnum"
SCN = "rally.plugins.openstack.scenarios"


class ClustersGeneratorTestCase(test.ScenarioTestCase):

    def _gen_tenants(self, count):
        tenants = {}
        for id_ in range(count):
            tenants[str(id_)] = {"name": str(id_)}
        return tenants

    def _gen_tenants_with_cluster_template(self, count):
        tenants = {}
        for id_ in range(count):
            tenants[str(id_)] = {"name": str(id_)}
            tenants[str(id_)]["cluster_template"] = "rally_ct_uuid"
        return tenants

    @mock.patch("%s.magnum.utils.MagnumScenario._create_cluster" % SCN,
                return_value=mock.Mock())
    def test_setup_using_existing_cluster_template(self, mock__create_cluster):
        tenants_count = 2
        users_per_tenant = 5

        tenants = self._gen_tenants(tenants_count)
        users = []
        for ten_id in tenants:
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": ten_id,
                              "credential": mock.MagicMock()})

        self.context.update({
            "config": {
                "users": {
                    "tenants": tenants_count,
                    "users_per_tenant": users_per_tenant,
                    "concurrent": 10,
                },
                "clusters": {
                    "cluster_template_uuid": "123456789",
                    "node_count": 2
                }
            },
            "users": users,
            "tenants": tenants
        })

        mock_cluster = mock__create_cluster.return_value
        new_context = copy.deepcopy(self.context)
        for id_ in new_context["tenants"]:
            new_context["tenants"][id_]["cluster"] = mock_cluster.uuid

        cluster_ctx = clusters.ClusterGenerator(self.context)
        cluster_ctx.setup()

        self.assertEqual(new_context, self.context)
        cluster_ctx_config = self.context["config"]["clusters"]
        node_count = cluster_ctx_config.get("node_count")
        cluster_template_uuid = cluster_ctx_config.get("cluster_template_uuid")
        mock_calls = [mock.call(cluster_template=cluster_template_uuid,
                                node_count=node_count)
                      for i in range(tenants_count)]
        mock__create_cluster.assert_has_calls(mock_calls)

    @mock.patch("%s.magnum.utils.MagnumScenario._create_cluster" % SCN,
                return_value=mock.Mock())
    def test_setup(self, mock__create_cluster):
        tenants_count = 2
        users_per_tenant = 5

        tenants = self._gen_tenants_with_cluster_template(tenants_count)
        users = []
        for ten_id in tenants:
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": ten_id,
                              "credential": mock.MagicMock()})

        self.context.update({
            "config": {
                "users": {
                    "tenants": tenants_count,
                    "users_per_tenant": users_per_tenant,
                    "concurrent": 10,
                },
                "cluster_templates": {
                    "dns_nameserver": "8.8.8.8",
                    "external_network_id": "public",
                    "flavor_id": "m1.small",
                    "docker_volume_size": 5,
                    "coe": "kubernetes",
                    "image_id": "fedora-atomic-latest",
                    "network_driver": "flannel"
                },
                "clusters": {
                    "node_count": 2
                }
            },
            "users": users,
            "tenants": tenants
        })

        mock_cluster = mock__create_cluster.return_value
        new_context = copy.deepcopy(self.context)
        for id_ in new_context["tenants"]:
            new_context["tenants"][id_]["cluster"] = mock_cluster.uuid

        cluster_ctx = clusters.ClusterGenerator(self.context)
        cluster_ctx.setup()

        self.assertEqual(new_context, self.context)
        cluster_ctx_config = self.context["config"]["clusters"]
        node_count = cluster_ctx_config.get("node_count")
        mock_calls = [mock.call(cluster_template="rally_ct_uuid",
                                node_count=node_count)
                      for i in range(tenants_count)]
        mock__create_cluster.assert_has_calls(mock_calls)

    @mock.patch("%s.cluster_templates.resource_manager.cleanup" % CTX)
    def test_cleanup(self, mock_cleanup):
        self.context.update({
            "users": mock.MagicMock()
        })
        clusters_ctx = clusters.ClusterGenerator(self.context)
        clusters_ctx.cleanup()
        mock_cleanup.assert_called_once_with(
            names=["magnum.clusters"],
            users=self.context["users"])
