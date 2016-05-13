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
from rally import consts
from rally import osclients
from rally.task import context


LOG = logging.getLogger(__name__)


@context.configure(name="volume_types", order=410)
class VolumeTypeGenerator(context.Context):
    """Context class for adding volumes types for benchmarks."""

    CONFIG_SCHEMA = {
        "type": "array",
        "$schema": consts.JSON_SCHEMA,
        "additionalProperties": False
    }

    @logging.log_task_wrapper(LOG.info, _("Enter context: `volume_types`"))
    def setup(self):
        admin_clients = osclients.Clients(
            self.context.get("admin", {}).get("credential"),
            api_info=self.context["config"].get("api_versions"))
        cinder = admin_clients.cinder()
        self.context["volume_types"] = []
        for vtype_name in self.config:
            LOG.debug("Creating Cinder volume type %s" % vtype_name)
            vtype = cinder.volume_types.create(vtype_name)
            self.context["volume_types"].append({"id": vtype.id,
                                                 "name": vtype_name})

    @logging.log_task_wrapper(LOG.info, _("Exit context: `volume_types`"))
    def cleanup(self):
        admin_clients = osclients.Clients(
            self.context.get("admin", {}).get("credential"),
            api_info=self.context["config"].get("api_versions"))
        cinder = admin_clients.cinder()
        for vtype in self.context["volume_types"]:
            LOG.debug("Deleting Cinder volume type %s" % vtype["name"])
            cinder.volume_types.delete(vtype["id"])
