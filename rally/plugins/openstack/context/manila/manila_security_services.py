# Copyright 2015 Mirantis Inc.
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

from rally.common import cfg
from rally.common import utils
from rally.common import validation
from rally import consts as rally_consts
from rally.plugins.openstack.cleanup import manager as resource_manager
from rally.plugins.openstack.context.manila import consts
from rally.plugins.openstack.scenarios.manila import utils as manila_utils
from rally.task import context

CONF = cfg.CONF
CONTEXT_NAME = consts.SECURITY_SERVICES_CONTEXT_NAME


@validation.add("required_platform", platform="openstack", users=True)
@context.configure(name=CONTEXT_NAME, platform="openstack", order=445)
class SecurityServices(context.Context):
    """This context creates 'security services' for Manila project."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": rally_consts.JSON_SCHEMA,
        "properties": {
            "security_services": {
                "type": "array",
                "description":
                    "It is expected to be list of dicts with data for creation"
                    " of security services.",
                "items": {
                    "type": "object",
                    "properties": {"type": {"enum": ["active_directory",
                                                     "kerberos", "ldap"]}},
                    "required": ["type"],
                    "additionalProperties": True,
                    "description":
                        "Data for creation of security services. \n "
                        "Example:\n\n"
                        "   .. code-block:: json\n\n"
                        "     {'type': 'LDAP', 'dns_ip': 'foo_ip', \n"
                        "      'server': 'bar_ip', 'domain': 'quuz_domain',\n"
                        "      'user': 'ololo', 'password': 'fake_password'}\n"
                }
            },
        },
        "additionalProperties": False
    }
    DEFAULT_CONFIG = {
        "security_services": [],
    }

    def setup(self):
        for user, tenant_id in (utils.iterate_per_tenants(
                self.context.get("users", []))):
            self.context["tenants"][tenant_id][CONTEXT_NAME] = {
                "security_services": [],
            }
            if self.config["security_services"]:
                manila_scenario = manila_utils.ManilaScenario({
                    "task": self.task,
                    "owner_id": self.context["owner_id"],
                    "user": user,
                    "config": {
                        "api_versions": self.context["config"].get(
                            "api_versions", [])}
                })
                for ss in self.config["security_services"]:
                    inst = manila_scenario._create_security_service(
                        **ss).to_dict()
                    self.context["tenants"][tenant_id][CONTEXT_NAME][
                        "security_services"].append(inst)

    def cleanup(self):
        resource_manager.cleanup(
            names=["manila.security_services"],
            users=self.context.get("users", []),
            superclass=manila_utils.ManilaScenario,
            task_id=self.get_owner_id())
