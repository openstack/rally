# Copyright 2014: Mirantis Inc.
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

from rally.common import logging
from rally.common import utils as rutils
from rally.common import validation
from rally import consts
from rally.plugins.openstack.cleanup import manager as resource_manager
from rally.plugins.openstack import osclients
from rally.task import context

LOG = logging.getLogger(__name__)


@validation.add("required_platform", platform="openstack", admin=True)
@context.configure(name="flavors", platform="openstack", order=340)
class FlavorsGenerator(context.Context):
    """Context creates a list of flavors."""

    CONFIG_SCHEMA = {
        "type": "array",
        "$schema": consts.JSON_SCHEMA,
        "items": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                },
                "ram": {
                    "type": "integer",
                    "minimum": 1
                },
                "vcpus": {
                    "type": "integer",
                    "minimum": 1
                },
                "disk": {
                    "type": "integer",
                    "minimum": 0
                },
                "swap": {
                    "type": "integer",
                    "minimum": 0
                },
                "ephemeral": {
                    "type": "integer",
                    "minimum": 0
                },
                "extra_specs": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "string"
                    }
                }
            },
            "additionalProperties": False,
            "required": ["name", "ram"]
        }
    }

    def setup(self):
        """Create list of flavors."""
        from novaclient import exceptions as nova_exceptions

        self.context["flavors"] = {}

        clients = osclients.Clients(self.context["admin"]["credential"])
        for flavor_config in self.config:

            extra_specs = flavor_config.get("extra_specs")

            flavor_config = FlavorConfig(**flavor_config)
            try:
                flavor = clients.nova().flavors.create(**flavor_config)
            except nova_exceptions.Conflict:
                msg = "Using existing flavor %s" % flavor_config["name"]
                if logging.is_debug():
                    LOG.exception(msg)
                else:
                    LOG.warning(msg)
                continue

            if extra_specs:
                flavor.set_keys(extra_specs)

            self.context["flavors"][flavor_config["name"]] = flavor.to_dict()
            LOG.debug("Created flavor with id '%s'" % flavor.id)

    def cleanup(self):
        """Delete created flavors."""
        mather = rutils.make_name_matcher(*[f["name"] for f in self.config])
        resource_manager.cleanup(
            names=["nova.flavors"],
            admin=self.context["admin"],
            api_versions=self.context["config"].get("api_versions"),
            superclass=mather,
            task_id=self.get_owner_id())


class FlavorConfig(dict):
    def __init__(self, name, ram, vcpus=1, disk=0, swap=0, ephemeral=0,
                 extra_specs=None):
        """Flavor configuration for context and flavor & image validation code.

        Context code uses this code to provide default values for flavor
        creation.  Validation code uses this class as a Flavor instance to
        check image validity against a flavor that is to be created by
        the context.

        :param name: name of the newly created flavor
        :param ram: RAM amount for the flavor (MBs)
        :param vcpus: VCPUs amount for the flavor
        :param disk: disk amount for the flavor (GBs)
        :param swap: swap amount for the flavor (MBs)
        :param ephemeral: ephemeral disk amount for the flavor (GBs)
        :param extra_specs: is ignored
        """
        super(FlavorConfig, self).__init__(
            name=name, ram=ram, vcpus=vcpus, disk=disk,
            swap=swap, ephemeral=ephemeral)
        self.__dict__.update(self)
