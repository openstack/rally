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

from rally.common import logging
from rally.common import utils
from rally.common import validation
from rally import consts
from rally.plugins.openstack.cleanup import manager as resource_manager
from rally.plugins.openstack import osclients
from rally.plugins.openstack.services.storage import block
from rally.task import context


LOG = logging.getLogger(__name__)


@validation.add("required_platform", platform="openstack", admin=True)
@context.configure(name="volume_types", platform="openstack", order=410)
class VolumeTypeGenerator(context.Context):
    """Adds cinder volumes types."""

    CONFIG_SCHEMA = {
        "type": "array",
        "$schema": consts.JSON_SCHEMA,
        "items": {"type": "string"}
    }

    def setup(self):
        admin_clients = osclients.Clients(
            self.context.get("admin", {}).get("credential"),
            api_info=self.context["config"].get("api_versions"))
        cinder_service = block.BlockStorage(
            admin_clients,
            name_generator=self.generate_random_name,
            atomic_inst=self.atomic_actions())
        self.context["volume_types"] = []
        for vtype_name in self.config:
            LOG.debug("Creating Cinder volume type %s" % vtype_name)
            vtype = cinder_service.create_volume_type(vtype_name)
            self.context["volume_types"].append({"id": vtype.id,
                                                 "name": vtype_name})

    def cleanup(self):
        mather = utils.make_name_matcher(*self.config)
        resource_manager.cleanup(
            names=["cinder.volume_types"],
            admin=self.context["admin"],
            api_versions=self.context["config"].get("api_versions"),
            superclass=mather,
            task_id=self.get_owner_id())
