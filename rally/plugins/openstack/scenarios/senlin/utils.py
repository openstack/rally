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

from oslo_config import cfg

from rally import exceptions
from rally.plugins.openstack import scenario
from rally.task import atomic
from rally.task import utils

SENLIN_BENCHMARK_OPTS = [
    cfg.FloatOpt("senlin_action_timeout",
                 default=3600,
                 help="Time in seconds to wait for senlin action to finish."),
]

CONF = cfg.CONF
benchmark_group = cfg.OptGroup(name="benchmark", title="benchmark options")
CONF.register_opts(SENLIN_BENCHMARK_OPTS, group=benchmark_group)


class SenlinScenario(scenario.OpenStackScenario):
    """Base class for Senlin scenarios with basic atomic actions."""

    @atomic.action_timer("senlin.list_clusters")
    def _list_clusters(self, **queries):
        """Return user cluster list.

        :param kwargs \*\*queries: Optional query parameters to be sent to
            restrict the clusters to be returned. Available parameters include:

            * name: The name of a cluster.
            * status: The current status of a cluster.
            * sort: A list of sorting keys separated by commas. Each sorting
                    key can optionally be attached with a sorting direction
                    modifier which can be ``asc`` or ``desc``.
            * limit: Requests a specified size of returned items from the
                query.  Returns a number of items up to the specified limit
                value.
            * marker: Specifies the ID of the last-seen item. Use the limit
                parameter to make an initial limited request and use the ID of
                the last-seen item from the response as the marker parameter
                value in a subsequent limited request.
            * global_project: A boolean value indicating whether clusters
                from all projects will be returned.

        :returns: list of clusters according to query.
        """
        return list(self.admin_clients("senlin").clusters(**queries))

    @atomic.action_timer("senlin.create_cluster")
    def _create_cluster(self, profile_id, desired_capacity=0, min_size=0,
                        max_size=-1, timeout=60, metadata=None):
        """Create a new cluster from attributes.

        :param profile_id: ID of profile used to create cluster
        :param desired_capacity: The capacity or initial number of nodes
                                 owned by the cluster
        :param min_size: The minimum number of nodes owned by the cluster
        :param max_size: The maximum number of nodes owned by the cluster.
                         -1 means no limit
        :param timeout: The timeout value in minutes for cluster creation
        :param metadata: A set of key value pairs to associate with the cluster

        :returns: object of cluster created.
        """
        attrs = {
            "profile_id": profile_id,
            "name": self.generate_random_name(),
            "desired_capacity": desired_capacity,
            "min_size": min_size,
            "max_size": max_size,
            "metadata": metadata,
            "timeout": timeout
        }

        cluster = self.admin_clients("senlin").create_cluster(**attrs)
        cluster = utils.wait_for_status(
            cluster,
            ready_statuses=["ACTIVE"],
            failure_statuses=["ERROR"],
            update_resource=self._get_cluster,
            timeout=CONF.benchmark.senlin_action_timeout)

        return cluster

    def _get_cluster(self, cluster):
        """Get cluster details.

        :param cluster: cluster to get

        :returns: object of cluster
        """
        try:
            return self.admin_clients("senlin").get_cluster(cluster.id)
        except Exception as e:
            if getattr(e, "code", getattr(e, "http_status", 400)) == 404:
                raise exceptions.GetResourceNotFound(resource=cluster.id)
            raise exceptions.GetResourceFailure(resource=cluster.id, err=e)

    @atomic.action_timer("senlin.delete_cluster")
    def _delete_cluster(self, cluster):
        """Delete given cluster.

        Returns after the cluster is successfully deleted.

        :param cluster: cluster object to delete
        """
        self.admin_clients("senlin").delete_cluster(cluster)
        utils.wait_for_status(
            cluster,
            ready_statuses=["DELETED"],
            failure_statuses=["ERROR"],
            check_deletion=True,
            update_resource=self._get_cluster,
            timeout=CONF.benchmark.senlin_action_timeout)

    @atomic.action_timer("senlin.create_profile")
    def _create_profile(self, spec, metadata=None):
        """Create a new profile from attributes.

        :param spec: spec dictionary used to create profile
        :param metadata: A set of key value pairs to associate with the
                         profile

        :returns: object of profile created
        """
        attrs = {}
        attrs["spec"] = spec
        attrs["name"] = self.generate_random_name()
        if metadata:
            attrs["metadata"] = metadata

        return self.clients("senlin").create_profile(**attrs)

    @atomic.action_timer("senlin.delete_profile")
    def _delete_profile(self, profile):
        """Delete given profile.

        Returns after the profile is successfully deleted.

        :param profile: profile object to be deleted
        """
        self.clients("senlin").delete_profile(profile)
