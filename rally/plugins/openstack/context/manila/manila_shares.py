# Copyright 2016 Mirantis Inc.
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

CONTEXT_NAME = consts.SHARES_CONTEXT_NAME


@context.configure(name=CONTEXT_NAME, order=455)
class Shares(context.Context):
    """This context creates shares for Manila project."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": rally_consts.JSON_SCHEMA,
        "properties": {
            "shares_per_tenant": {
                "type": "integer",
                "minimum": 1,
            },
            "size": {
                "type": "integer",
                "minimum": 1
            },
            "share_proto": {
                "type": "string",
            },
            "share_type": {
                "type": "string",
            },
        },
        "additionalProperties": False
    }

    DEFAULT_CONFIG = {
        "shares_per_tenant": 1,
        "size": 1,
        "share_proto": "NFS",
        "share_type": None,
    }

    def _create_shares(self, manila_scenario, tenant_id, share_proto, size=1,
                       share_type=None):
        tenant_ctxt = self.context["tenants"][tenant_id]
        tenant_ctxt.setdefault("shares", [])
        for i in range(self.config["shares_per_tenant"]):
            kwargs = {"share_proto": share_proto, "size": size}
            if share_type:
                kwargs["share_type"] = share_type
            share_networks = tenant_ctxt.get("manila_share_networks", {}).get(
                "share_networks", [])
            if share_networks:
                kwargs["share_network"] = share_networks[
                    i % len(share_networks)]["id"]
            share = manila_scenario._create_share(**kwargs)
            tenant_ctxt["shares"].append(share.to_dict())

    @logging.log_task_wrapper(
        LOG.info, _("Enter context: `%s`") % CONTEXT_NAME)
    def setup(self):
        for user, tenant_id in (
                utils.iterate_per_tenants(self.context.get("users", []))):
            manila_scenario = manila_utils.ManilaScenario({
                "task": self.task,
                "user": user,
                "config": {
                    "api_versions": self.context["config"].get(
                        "api_versions", [])}
            })
            self._create_shares(
                manila_scenario,
                tenant_id,
                self.config["share_proto"],
                self.config["size"],
                self.config["share_type"],
            )

    @logging.log_task_wrapper(LOG.info, _("Exit context: `%s`") % CONTEXT_NAME)
    def cleanup(self):
        resource_manager.cleanup(
            names=["manila.shares"],
            users=self.context.get("users", []),
        )
