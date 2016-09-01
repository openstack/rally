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
from rally.plugins.openstack.scenarios.senlin import utils
from rally.task import validation


"""Scenarios for Senlin clusters."""


@validation.required_openstack(admin=True)
@validation.required_services(consts.Service.SENLIN)
@validation.required_contexts("profiles")
@scenario.configure(context={"cleanup": ["senlin"]},
                    name="SenlinClusters.create_and_delete_cluster")
class CreateAndDeleteCluster(utils.SenlinScenario):

    def run(self, desired_capacity=0, min_size=0,
            max_size=-1, timeout=3600, metadata=None):
        """Create a cluster and then delete it.

        Measure the "senlin cluster-create" and "senlin cluster-delete"
        commands performance.

        :param desired_capacity: The capacity or initial number of nodes
                                 owned by the cluster
        :param min_size: The minimum number of nodes owned by the cluster
        :param max_size: The maximum number of nodes owned by the cluster.
                         -1 means no limit
        :param timeout: The timeout value in seconds for cluster creation
        :param metadata: A set of key value pairs to associate with the cluster
        """

        profile_id = self.context["tenant"]["profile"]
        cluster = self._create_cluster(profile_id, desired_capacity,
                                       min_size, max_size, timeout, metadata)
        self._delete_cluster(cluster)