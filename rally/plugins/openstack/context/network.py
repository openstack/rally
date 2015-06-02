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

import six

from rally.benchmark.context import base
from rally.common.i18n import _
from rally.common import log as logging
from rally.common import utils
from rally import consts
from rally import osclients
from rally.plugins.openstack.wrappers import network as network_wrapper


LOG = logging.getLogger(__name__)


@base.context(name="network", order=350)
class Network(base.Context):
    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "start_cidr": {
                "type": "string"
            },
            "networks_per_tenant": {
                "type": "integer",
                "minimum": 1
            }
        },
        "additionalProperties": False
    }

    DEFAULT_CONFIG = {
        "start_cidr": "10.2.0.0/24",
        "networks_per_tenant": 1
    }

    def __init__(self, context):
        super(Network, self).__init__(context)
        self.net_wrapper = network_wrapper.wrap(
            osclients.Clients(context["admin"]["endpoint"]),
            self.config)

    @utils.log_task_wrapper(LOG.info, _("Enter context: `network`"))
    def setup(self):
        for user, tenant_id in (utils.iterate_per_tenants(
                self.context.get("users", []))):
            self.context["tenants"][tenant_id]["networks"] = []
            for i in range(self.config["networks_per_tenant"]):
                # NOTE(amaretskiy): add_router and subnets_num take effect
                #                   for Neutron only.
                # NOTE(amaretskiy): Do we need neutron subnets_num > 1 ?
                network = self.net_wrapper.create_network(tenant_id,
                                                          add_router=True,
                                                          subnets_num=1)
                self.context["tenants"][tenant_id]["networks"].append(network)

    @utils.log_task_wrapper(LOG.info, _("Exit context: `network`"))
    def cleanup(self):
        for tenant_id, tenant_ctx in six.iteritems(self.context["tenants"]):
            for network in tenant_ctx.get("networks", []):
                with logging.ExceptionLogger(
                        LOG,
                        _("Failed to delete network for tenant %s")
                        % tenant_id):
                    self.net_wrapper.delete_network(network)
