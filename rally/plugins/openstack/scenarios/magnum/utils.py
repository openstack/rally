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

from oslo_config import cfg

from rally.common import utils as common_utils
from rally.plugins.openstack import scenario
from rally.task import atomic
from rally.task import utils

MAGNUM_BENCHMARK_OPTS = [
    cfg.FloatOpt("magnum_cluster_create_prepoll_delay",
                 default=5.0,
                 help="Time(in sec) to sleep after creating a resource before "
                      "polling for the status."),
    cfg.FloatOpt("magnum_cluster_create_timeout",
                 default=1200.0,
                 help="Time(in sec) to wait for magnum cluster to be "
                      "created."),
    cfg.FloatOpt("magnum_cluster_create_poll_interval",
                 default=1.0,
                 help="Time interval(in sec) between checks when waiting for "
                      "cluster creation."),
]

CONF = cfg.CONF
benchmark_group = cfg.OptGroup(name="benchmark", title="benchmark options")
CONF.register_opts(MAGNUM_BENCHMARK_OPTS, group=benchmark_group)


class MagnumScenario(scenario.OpenStackScenario):
    """Base class for Magnum scenarios with basic atomic actions."""

    @atomic.action_timer("magnum.list_cluster_templates")
    def _list_cluster_templates(self, **kwargs):
        """Return list of cluster_templates.

        :param limit: (Optional) The maximum number of results to return
                      per request, if:

            1) limit > 0, the maximum number of cluster_templates to return.
            2) limit param is NOT specified (None), the number of items
               returned respect the maximum imposed by the Magnum API
               (see Magnum's api.max_limit option).
        :param kwargs: Optional additional arguments for cluster_templates
                       listing

        :returns: cluster_templates list
        """

        return self.clients("magnum").cluster_templates.list(**kwargs)

    @atomic.action_timer("magnum.create_cluster_template")
    def _create_cluster_template(self, **kwargs):
        """Create a cluster_template

        :param kwargs: optional additional arguments for cluster_template
                       creation
        :returns: magnum cluster_template
        """

        kwargs["name"] = self.generate_random_name()

        return self.clients("magnum").cluster_templates.create(**kwargs)

    @atomic.action_timer("magnum.list_clusters")
    def _list_clusters(self, limit=None, **kwargs):
        """Return list of clusters.

        :param limit: (Optional) the maximum number of results to return
                      per request, if:

            1) limit > 0, the maximum number of clusters to return.
            2) limit param is NOT specified (None), the number of items
               returned respect the maximum imposed by the Magnum API
               (see Magnum's api.max_limit option).
        :param kwargs: Optional additional arguments for clusters listing

        :returns: clusters list
        """
        return self.clients("magnum").clusters.list(limit=limit, **kwargs)

    @atomic.action_timer("magnum.create_cluster")
    def _create_cluster(self, cluster_template, node_count, **kwargs):
        """Create a cluster

        :param cluster_template: cluster_template for the cluster
        :param node_count: the cluster node count
        :param kwargs: optional additional arguments for cluster creation
        :returns: magnum cluster
        """

        name = self.generate_random_name()
        cluster = self.clients("magnum").clusters.create(
            name=name, cluster_template_id=cluster_template,
            node_count=node_count, **kwargs)

        common_utils.interruptable_sleep(
            CONF.benchmark.magnum_cluster_create_prepoll_delay)
        cluster = utils.wait_for_status(
            cluster,
            ready_statuses=["CREATE_COMPLETE"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.magnum_cluster_create_timeout,
            check_interval=CONF.benchmark.magnum_cluster_create_poll_interval,
            id_attr="uuid"
        )
        return cluster
