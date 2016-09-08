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

from oslo_config import cfg

from rally.common.i18n import _
from rally.common import logging
from rally.common import utils
from rally import consts as rally_consts
from rally.plugins.openstack.cleanup import manager as resource_manager
from rally.plugins.openstack.context.manila import consts
from rally.plugins.openstack.scenarios.manila import utils as manila_utils
from rally.task import context

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

CONTEXT_NAME = consts.SECURITY_SERVICES_CONTEXT_NAME


@context.configure(name=CONTEXT_NAME, order=445)
class SecurityServices(context.Context):
    """This context creates 'security services' for Manila project."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": rally_consts.JSON_SCHEMA,
        "properties": {
            # NOTE(vponomaryov): context arg 'security_services' is expected
            # to be list of dicts with data for creation of security services.
            # Example:
            # security_services = [
            #     {'type': 'LDAP', 'dns_ip': 'foo_ip', 'server': 'bar_ip',
            #      'domain': 'quuz_domain', 'user': 'ololo',
            #      'password': 'fake_password'}
            # ]
            # Where 'type' is required key and should have one of following
            # values: 'active_directory', 'kerberos' or 'ldap'.
            # This context arg is used only if share networks are used and
            # autocreated.
            "security_services": {"type": "array"},
        },
        "additionalProperties": False
    }
    DEFAULT_CONFIG = {
        "security_services": [],
    }

    @logging.log_task_wrapper(
        LOG.info, _("Enter context: `%s`") % CONTEXT_NAME)
    def setup(self):
        for user, tenant_id in (utils.iterate_per_tenants(
                self.context.get("users", []))):
            self.context["tenants"][tenant_id][CONTEXT_NAME] = {
                "security_services": [],
            }
            if self.config["security_services"]:
                manila_scenario = manila_utils.ManilaScenario({
                    "task": self.task,
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

    @logging.log_task_wrapper(LOG.info, _("Exit context: `%s`") % CONTEXT_NAME)
    def cleanup(self):
        resource_manager.cleanup(
            names=["manila.security_services"],
            users=self.context.get("users", []),
        )
