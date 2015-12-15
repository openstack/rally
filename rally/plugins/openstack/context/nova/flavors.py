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

from novaclient import exceptions as nova_exceptions

from rally.common.i18n import _
from rally.common import logging
from rally.common import utils as rutils
from rally import consts
from rally import osclients
from rally.task import context

LOG = logging.getLogger(__name__)


@context.configure(name="flavors", order=340)
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

    @logging.log_task_wrapper(LOG.info, _("Enter context: `flavors`"))
    def setup(self):
        """Create list of flavors."""
        self.context["flavors"] = {}

        clients = osclients.Clients(self.context["admin"]["credential"])
        for flavor_config in self.config:

            extra_specs = flavor_config.get("extra_specs")

            flavor_config = FlavorConfig(**flavor_config)
            try:
                flavor = clients.nova().flavors.create(**flavor_config)
            except nova_exceptions.Conflict as e:
                LOG.warning("Using already existing flavor %s" %
                            flavor_config["name"])
                if logging.is_debug():
                    LOG.exception(e)
                continue

            if extra_specs:
                flavor.set_keys(extra_specs)

            self.context["flavors"][flavor_config["name"]] = flavor.to_dict()
            LOG.debug("Created flavor with id '%s'" % flavor.id)

    @logging.log_task_wrapper(LOG.info, _("Exit context: `flavors`"))
    def cleanup(self):
        """Delete created flavors."""
        clients = osclients.Clients(self.context["admin"]["credential"])
        for flavor in self.context["flavors"].values():
            with logging.ExceptionLogger(
                    LOG, _("Can't delete flavor %s") % flavor["id"]):
                rutils.retry(3, clients.nova().flavors.delete, flavor["id"])
                LOG.debug("Flavor is deleted %s" % flavor["id"])


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
