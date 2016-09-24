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

from rally.common.i18n import _
from rally.common import logging
from rally.common import utils as rutils
from rally import consts
from rally.plugins.openstack.cleanup import manager as resource_manager
from rally.plugins.openstack.scenarios.magnum import utils as magnum_utils
from rally.task import context


LOG = logging.getLogger(__name__)


@context.configure(name="clusters", order=480)
class ClusterGenerator(context.Context):
    """Context class for generating temporary cluster for benchmarks."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "cluster_template_uuid": {
                "type": "string"
            },
            "node_count": {
                "type": "integer",
                "minimum": 1,
                "default": 1
            },
        },
        "additionalProperties": False
    }

    @logging.log_task_wrapper(LOG.info, _("Enter context: `Cluster`"))
    def setup(self):
        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):

            magnum_scenario = magnum_utils.MagnumScenario({
                "user": user,
                "task": self.context["task"],
                "config": {"api_versions": self.context["config"].get(
                    "api_versions", [])}
            })

            # create a cluster
            ct_uuid = self.config.get("cluster_template_uuid", None)
            if ct_uuid is None:
                ctx = self.context["tenants"][tenant_id]
                ct_uuid = ctx.get("cluster_template")
            cluster = magnum_scenario._create_cluster(
                cluster_template=ct_uuid,
                node_count=self.config.get("node_count"))
            self.context["tenants"][tenant_id]["cluster"] = cluster.uuid

    @logging.log_task_wrapper(LOG.info, _("Exit context: `Cluster`"))
    def cleanup(self):
        resource_manager.cleanup(
            names=["magnum.clusters"],
            users=self.context.get("users", []))
