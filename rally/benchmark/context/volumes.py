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

from rally.benchmark.context import base
from rally.benchmark.context.cleanup import utils as cleanup_utils
from rally.benchmark.scenarios.cinder import utils as cinder_utils
from rally.openstack.common import log as logging
from rally import osclients
from rally import utils as rutils


LOG = logging.getLogger(__name__)


class VolumeGenerator(base.Context):
    """Context class for adding volumes to each user for benchmarks."""

    __ctx_name__ = "volumes"
    __ctx_order__ = 500
    __ctx_hidden__ = False

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": rutils.JSON_SCHEMA,
        "properties": {
            "size": {
                "type": "integer",
                "minimum": 1
            },
        },
        'required': ['size'],
        "additionalProperties": False
    }

    def __init__(self, context):
        super(VolumeGenerator, self).__init__(context)
        self.context.setdefault("volumes", [])

    @rutils.log_task_wrapper(LOG.info, _("Enter context: `Volumes`"))
    def setup(self):
        size = self.config["size"]
        current_tenants = []

        for user in self.context["users"]:
            if user["tenant_id"] not in current_tenants:
                current_tenants.append(user["tenant_id"])
                clients = osclients.Clients(user["endpoint"])
                cinder_util = cinder_utils.CinderScenario(clients=clients)
                volume = cinder_util._create_volume(size)
                self.context["volumes"].append({"volume_id": volume.id,
                                                "endpoint": user["endpoint"],
                                                "tenant_id": user[
                                                    "tenant_id"]})

    @rutils.log_task_wrapper(LOG.info, _("Exit context: `Volumes`"))
    def cleanup(self):
        for volume in self.context["volumes"]:
            try:
                cinder = osclients.Clients(volume["endpoint"]).cinder()
                cleanup_utils.delete_cinder_resources(cinder)
            except Exception as ex:
                LOG.warning("Failed to remove volume: %(volume_id)s for user "
                            "%(tenant)s/%(user)s. Exception: %(ex)s" %
                            {"volume_id": volume["volume_id"],
                             "tenant": volume["endpoint"].tenant_name,
                             "user": volume["endpoint"].username,
                             "ex": ex})
