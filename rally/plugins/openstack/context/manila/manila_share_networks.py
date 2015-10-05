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
from rally import exceptions
from rally.plugins.openstack.context.manila import consts
from rally.plugins.openstack.scenarios.manila import utils as manila_utils
from rally.task import context
from rally.task import utils as bench_utils

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

CONTEXT_NAME = consts.SHARE_NETWORKS_CONTEXT_NAME


@context.configure(name=CONTEXT_NAME, order=450)
class ShareNetworks(context.Context):
    """This context creates resources specific for Manila project."""
    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": rally_consts.JSON_SCHEMA,
        "properties": {
            # NOTE(vponomaryov): specifies whether manila should use
            # share networks for share creation or not.
            "use_share_networks": {"type": "boolean"},

            # NOTE(vponomaryov): this context arg will be used only when
            # context arg "use_share_networks" is set to True.
            # If context arg 'share_networks' has values
            # then they will be used else share networks will be autocreated -
            # one for each tenant network. If networks do not exist then will
            # be created one share network for each tenant without network
            # data.
            # Expected value is dict of lists where tenant Name or ID is key
            # and list of share_network Names or IDs is value. Example:
            # "context": {
            #   "manila_share_networks": {
            #     "use_share_networks": true,
            #     "share_networks": {
            #       "tenant_1_name_or_id": ["share_network_1_name_or_id",
            #                               "share_network_2_name_or_id"],
            #       "tenant_2_name_or_id": ["share_network_3_name_or_id"]
            #     }
            #   }
            # }
            # Also, make sure that all 'existing users' in appropriate
            # registered deployment have share networks if its usage is
            # enabled, else Rally will randomly take users that does not
            # satisfy criteria.
            "share_networks": {"type": "object"},
        },
        "additionalProperties": False
    }
    DEFAULT_CONFIG = {
        "use_share_networks": False,
        "share_networks": {},
    }

    def _setup_for_existing_users(self):
        if (self.config["use_share_networks"] and
                not self.config["share_networks"]):
            msg = _("Usage of share networks was enabled but for deployment "
                    "with existing users share networks also should be "
                    "specified via arg 'share_networks'")
            raise exceptions.ContextSetupFailure(
                ctx_name=self.get_name(), msg=msg)

        # Set flag that says we will not delete/cleanup share networks
        self.context[CONTEXT_NAME]["delete_share_networks"] = False

        for tenant_name_or_id, share_networks in self.config[
                "share_networks"].items():
            # Verify project existence
            for tenant in self.context["tenants"].values():
                if tenant_name_or_id in (tenant["id"], tenant["name"]):
                    tenant_id = tenant["id"]
                    existing_user = None
                    for user in self.context["users"]:
                        if user["tenant_id"] == tenant_id:
                            existing_user = user
                            break
                    break
            else:
                msg = _("Provided tenant Name or ID '%s' was not found in "
                        "existing tenants.") % tenant_name_or_id
                raise exceptions.ContextSetupFailure(
                    ctx_name=self.get_name(), msg=msg)
            self.context["tenants"][tenant_id][CONTEXT_NAME] = {}
            self.context["tenants"][tenant_id][CONTEXT_NAME][
                "share_networks"] = []

            manila_scenario = manila_utils.ManilaScenario({
                "user": existing_user,
                "config": {
                    "api_versions": self.context["config"].get(
                        "api_versions", [])}
            })
            existing_sns = manila_scenario._list_share_networks(
                detailed=False, search_opts={"project_id": tenant_id})

            for sn_name_or_id in share_networks:
                # Verify share network existence
                for sn in existing_sns:
                    if sn_name_or_id in (sn.id, sn.name):
                        break
                else:
                    msg = _("Specified share network '%(sn)s' does not "
                            "exist for tenant '%(tenant_id)s'") % {
                                "sn": sn_name_or_id, "tenant_id": tenant_id}
                    raise exceptions.ContextSetupFailure(
                        ctx_name=self.get_name(), msg=msg)

                # Set share network for project
                self.context["tenants"][tenant_id][CONTEXT_NAME][
                    "share_networks"].append(sn.to_dict())

    def _setup_for_autocreated_users(self):
        # Create share network for each network of tenant
        for user, tenant_id in (utils.iterate_per_tenants(
                self.context.get("users", []))):
            networks = self.context["tenants"][tenant_id].get("networks")
            manila_scenario = manila_utils.ManilaScenario({
                "task": self.task,
                "user": user,
                "config": {
                    "api_versions": self.context["config"].get(
                        "api_versions", [])}
            })
            self.context["tenants"][tenant_id][CONTEXT_NAME] = {
                "share_networks": []}
            data = {}

            def _setup_share_network(tenant_id, data):
                share_network = manila_scenario._create_share_network(
                    **data).to_dict()
                self.context["tenants"][tenant_id][CONTEXT_NAME][
                    "share_networks"].append(share_network)
                for ss in self.context["tenants"][tenant_id].get(
                        consts.SECURITY_SERVICES_CONTEXT_NAME, {}).get(
                            "security_services", []):
                    manila_scenario._add_security_service_to_share_network(
                        share_network["id"], ss["id"])

            if networks:
                for network in networks:
                    if network.get("cidr"):
                        data["nova_net_id"] = network["id"]
                    elif network.get("subnets"):
                        data["neutron_net_id"] = network["id"]
                        data["neutron_subnet_id"] = network["subnets"][0]
                    else:
                        LOG.warning(_(
                            "Can not determine network service provider. "
                            "Share network will have no data."))
                    _setup_share_network(tenant_id, data)
            else:
                _setup_share_network(tenant_id, data)

    @logging.log_task_wrapper(LOG.info, _("Enter context: `%s`")
                              % CONTEXT_NAME)
    def setup(self):
        self.context[CONTEXT_NAME] = {}
        if not self.config["use_share_networks"]:
            self.context[CONTEXT_NAME]["delete_share_networks"] = False
        elif self.context["config"].get("existing_users"):
            self._setup_for_existing_users()
        else:
            self._setup_for_autocreated_users()

    def _cleanup_tenant_resources(self, resources_plural_name,
                                  resources_singular_name):
        """Cleans up tenant resources.

        :param resources_plural_name: plural name for resources
        :param resources_singular_name: singular name for resource. Expected
            to be part of resource deletion method name (obj._delete_%s)
        """
        for user, tenant_id in (utils.iterate_per_tenants(
                self.context.get("users", []))):
            manila_scenario = manila_utils.ManilaScenario({
                "user": user,
                "config": {
                    "api_versions": self.context["config"].get(
                        "api_versions", [])}
            })
            resources = self.context["tenants"][tenant_id][CONTEXT_NAME].get(
                resources_plural_name, [])
            for resource in resources:
                logger = logging.ExceptionLogger(
                    LOG,
                    _("Failed to delete %(name)s %(id)s for tenant %(t)s.") % {
                        "id": resource, "t": tenant_id,
                        "name": resources_singular_name})
                with logger:
                    delete_func = getattr(
                        manila_scenario,
                        "_delete_%s" % resources_singular_name)
                    delete_func(resource)

    def _wait_for_cleanup_of_share_networks(self):
        """Waits for deletion of Manila service resources."""
        for user, tenant_id in (utils.iterate_per_tenants(
                self.context.get("users", []))):
            self._wait_for_resources_deletion(
                self.context["tenants"][tenant_id][CONTEXT_NAME].get("shares"))
            manila_scenario = manila_utils.ManilaScenario({
                "user": user,
                "admin": self.context["admin"],
                "config": {
                    "api_versions": self.context["config"].get(
                        "api_versions", [])}
            })
            for sn in self.context["tenants"][tenant_id][CONTEXT_NAME][
                    "share_networks"]:
                share_servers = manila_scenario._list_share_servers(
                    search_opts={"share_network": sn["id"]})
                self._wait_for_resources_deletion(share_servers)

    def _wait_for_resources_deletion(self, resources):
        """Waiter for resources deletion.

        :param resources: resource or list of resources for deletion
            verification
        """
        if not resources:
            return
        if not isinstance(resources, list):
            resources = [resources]
        for resource in resources:
            bench_utils.wait_for_status(
                resource,
                ready_statuses=["deleted"],
                check_deletion=True,
                update_resource=bench_utils.get_from_manager(),
                timeout=CONF.benchmark.manila_share_delete_timeout,
                check_interval=(
                    CONF.benchmark.manila_share_delete_poll_interval))

    @logging.log_task_wrapper(LOG.info, _("Exit context: `%s`") % CONTEXT_NAME)
    def cleanup(self):
        if self.context[CONTEXT_NAME].get("delete_share_networks", True):
            # NOTE(vponomaryov): Schedule 'share networks' deletion.
            self._cleanup_tenant_resources("share_networks", "share_network")

            # NOTE(vponomaryov): Share network deletion schedules deletion of
            # share servers. So, we should wait for its deletion too to avoid
            # further failures of network resources release.
            # Use separate cycle to make share servers be deleted in parallel.
            self._wait_for_cleanup_of_share_networks()
        else:
            # NOTE(vponomaryov): assume that share networks were not created
            # by test run.
            return
