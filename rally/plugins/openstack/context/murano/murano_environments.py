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

from rally.common import utils
from rally.common import validation
from rally import consts
from rally.plugins.openstack.cleanup import manager as resource_manager
from rally.plugins.openstack.scenarios.murano import utils as murano_utils
from rally.task import context


@validation.add("required_platform", platform="openstack", users=True)
@context.configure(name="murano_environments", platform="openstack", order=402)
class EnvironmentGenerator(context.Context):
    """Context class for creating murano environments."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "environments_per_tenant": {
                "type": "integer",
                "minimum": 1
            },
        },
        "required": ["environments_per_tenant"],
        "additionalProperties": False
    }

    def setup(self):
        for user, tenant_id in utils.iterate_per_tenants(
                self.context["users"]):
            self.context["tenants"][tenant_id]["environments"] = []
            for i in range(self.config["environments_per_tenant"]):
                murano_util = murano_utils.MuranoScenario(
                    {"user": user,
                     "task": self.context["task"],
                     "owner_id": self.context["owner_id"],
                     "config": self.context["config"]})
                env = murano_util._create_environment()
                self.context["tenants"][tenant_id]["environments"].append(env)

    def cleanup(self):
        resource_manager.cleanup(names=["murano.environments"],
                                 users=self.context.get("users", []),
                                 superclass=murano_utils.MuranoScenario,
                                 task_id=self.get_owner_id())
