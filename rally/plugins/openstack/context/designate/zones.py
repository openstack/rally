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
from rally.plugins.openstack.scenarios.designate import utils
from rally.task import context


LOG = logging.getLogger(__name__)


@context.configure(name="zones", order=600)
class ZoneGenerator(context.Context):
    """Context to add `zones_per_tenant` zones for each tenant."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "zones_per_tenant": {
                "type": "integer",
                "minimum": 1
            },
        },
        "additionalProperties": False
    }

    DEFAULT_CONFIG = {
        "zones_per_tenant": 1
    }

    @logging.log_task_wrapper(LOG.info, _("Enter context: `Zones`"))
    def setup(self):
        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):
            self.context["tenants"][tenant_id].setdefault("zones", [])
            designate_util = utils.DesignateScenario(
                {"user": user,
                 "task": self.context["task"]})
            for i in range(self.config["zones_per_tenant"]):
                zone = designate_util._create_zone()
                self.context["tenants"][tenant_id]["zones"].append(zone)

    @logging.log_task_wrapper(LOG.info, _("Exit context: `Zones`"))
    def cleanup(self):
        # TODO(boris-42): Delete only resources created by this context
        resource_manager.cleanup(names=["designate.zones"],
                                 users=self.context.get("users", []))
