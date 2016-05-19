# Copyright 2016: Mirantis Inc.
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

import pkgutil

from rally.common.i18n import _
from rally.common import logging
from rally.common import utils as rutils
from rally import consts
from rally import exceptions
from rally import osclients
from rally.plugins.openstack.cleanup import manager as resource_manager
from rally.plugins.openstack.scenarios.heat import utils as heat_utils
from rally.task import context

LOG = logging.getLogger(__name__)


def get_data(filename_or_resource):
    if isinstance(filename_or_resource, list):
        return pkgutil.get_data(*filename_or_resource)
    return open(filename_or_resource).read()


@context.configure(name="heat_dataplane", order=435)
class HeatDataplane(context.Context):
    """Context class for create stack by given template.

    This context will create stacks by given template for each tenant and
    add details to context. Following details will be added:
        id of stack;
        template file contents;
        files dictionary;
        stack parameters;
    Heat template should define a "gate" node which will interact with Rally
    by ssh and workload nodes by any protocol. To make this possible heat
    template should accept the following parameters:
        network_id: id of public network
        router_id: id of external router to connect "gate" node
        key_name: name of nova ssh keypair to use for "gate" node
    """
    FILE_SCHEMA = {
        "type": "string",
    }
    RESOURCE_SCHEMA = {
        "type": "array",
        "minItems": 2,
        "maxItems": 2,
    }
    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "stacks_per_tenant": {
                "type": "integer",
                "minimum": 1
            },
            "template": {
                "oneOf": [FILE_SCHEMA, RESOURCE_SCHEMA],
            },
            "files": {
                "type": "object",
            },
            "parameters": {
                "type": "object",
            },
            "context_parameters": {
                "type": "object",
            },
        },
        "additionalProperties": False
    }

    DEFAULT_CONFIG = {
        "stacks_per_tenant": 1,
    }

    def _get_context_parameter(self, user, tenant_id, path):
        value = {"user": user, "tenant": self.context["tenants"][tenant_id]}
        for key in path.split("."):
            try:
                # try to cast string to int in order to support integer keys
                # e.g 'spam.1.eggs' will be translated to ["spam"][1]["eggs"]
                key = int(key)
            except ValueError:
                pass
            try:
                value = value[key]
            except KeyError:
                raise exceptions.RallyException(
                    "There is no key %s in context" % path)
        return value

    def _get_public_network_id(self):
        nc = osclients.Clients(self.context["admin"]["credential"]).neutron()
        networks = nc.list_networks(**{"router:external": True})["networks"]
        return networks[0]["id"]

    @logging.log_task_wrapper(LOG.info, _("Enter context: `HeatDataplane`"))
    def setup(self):
        template = get_data(self.config["template"])
        files = {}
        for key, filename in self.config.get("files", {}).items():
            files[key] = get_data(filename)
        parameters = self.config.get("parameters", rutils.LockedDict())
        with parameters.unlocked():
            if "network_id" not in parameters:
                parameters["network_id"] = self._get_public_network_id()
            for user, tenant_id in rutils.iterate_per_tenants(
                    self.context["users"]):
                for name, path in self.config.get("context_parameters",
                                                  {}).items():
                    parameters[name] = self._get_context_parameter(user,
                                                                   tenant_id,
                                                                   path)
                if "router_id" not in parameters:
                    networks = self.context["tenants"][tenant_id]["networks"]
                    parameters["router_id"] = networks[0]["router_id"]
                if "key_name" not in parameters:
                    parameters["key_name"] = user["keypair"]["name"]
                heat_scenario = heat_utils.HeatScenario(
                    {"user": user, "task": self.context["task"]})
                self.context["tenants"][tenant_id]["stack_dataplane"] = []
                for i in range(self.config["stacks_per_tenant"]):
                    stack = heat_scenario._create_stack(template, files=files,
                                                        parameters=parameters)
                    tenant_data = self.context["tenants"][tenant_id]
                    tenant_data["stack_dataplane"].append([stack.id, template,
                                                           files, parameters])

    @logging.log_task_wrapper(LOG.info, _("Exit context: `HeatDataplane`"))
    def cleanup(self):
        resource_manager.cleanup(names=["heat.stacks"],
                                 users=self.context.get("users", []))
