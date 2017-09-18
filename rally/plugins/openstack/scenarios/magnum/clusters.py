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

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.magnum import utils
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.task import validation

"""Scenarios for Magnum clusters."""


@validation.add("required_services", services=[consts.Service.MAGNUM])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["magnum.clusters"]},
                    name="MagnumClusters.list_clusters",
                    platform="openstack")
class ListClusters(utils.MagnumScenario):

    def run(self, **kwargs):
        """List all clusters.

        Measure the "magnum clusters-list" command performance.
        :param limit: (Optional) The maximum number of results to return
                      per request, if:

            1) limit > 0, the maximum number of clusters to return.
            2) limit param is NOT specified (None), the number of items
               returned respect the maximum imposed by the Magnum API
               (see Magnum's api.max_limit option).

        :param kwargs: optional additional arguments for clusters listing
        """
        self._list_clusters(**kwargs)


@validation.add("required_services", services=[consts.Service.MAGNUM])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(
    context={"cleanup@openstack": ["magnum.clusters", "nova.keypairs"]},
    name="MagnumClusters.create_and_list_clusters",
    platform="openstack")
class CreateAndListClusters(utils.MagnumScenario):

    def run(self, node_count, **kwargs):
        """create cluster and then list all clusters.

        :param node_count: the cluster node count.
        :param cluster_template_uuid: optional, if user want to use an existing
               cluster_template
        :param kwargs: optional additional arguments for cluster creation
        """
        cluster_template_uuid = kwargs.get("cluster_template_uuid", None)
        if cluster_template_uuid is None:
            cluster_template_uuid = self.context["tenant"]["cluster_template"]
        else:
            del kwargs["cluster_template_uuid"]

        nova_scenario = nova_utils.NovaScenario({
            "user": self.context["user"],
            "task": self.context["task"],
            "config": {"api_versions": self.context["config"].get(
                "api_versions", [])}
        })
        keypair = nova_scenario._create_keypair()

        new_cluster = self._create_cluster(cluster_template_uuid, node_count,
                                           keypair=keypair, **kwargs)
        self.assertTrue(new_cluster, "Failed to create new cluster")
        clusters = self._list_clusters(**kwargs)
        self.assertIn(new_cluster.uuid, [cluster.uuid for cluster in clusters],
                      "New cluster not found in a list of clusters")
