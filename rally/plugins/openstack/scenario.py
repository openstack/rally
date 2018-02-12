# Copyright 2015: Mirantis Inc.
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

import functools
import random

from osprofiler import profiler

from rally.common import cfg
from rally.common.plugin import plugin
from rally.plugins.openstack import osclients
from rally.task import context
from rally.task import scenario

configure = functools.partial(scenario.configure, platform="openstack")

CONF = cfg.CONF


@context.add_default_context("users@openstack", {})
@plugin.default_meta(inherit=False)
class OpenStackScenario(scenario.Scenario):
    """Base class for all OpenStack scenarios."""

    def __init__(self, context=None, admin_clients=None, clients=None):
        super(OpenStackScenario, self).__init__(context)
        if context:
            api_info = {}
            if "api_versions@openstack" in context.get("config", {}):
                api_versions = context["config"]["api_versions@openstack"]
                for service in api_versions:
                    api_info[service] = {
                        "version": api_versions[service].get("version"),
                        "service_type": api_versions[service].get(
                            "service_type")}

            if admin_clients is None and "admin" in context:
                self._admin_clients = osclients.Clients(
                    context["admin"]["credential"], api_info)
            if clients is None:
                if "users" in context and "user" not in context:
                    self._choose_user(context)

                if "user" in context:
                    self._clients = osclients.Clients(
                        context["user"]["credential"], api_info)

        if admin_clients:
            self._admin_clients = admin_clients

        if clients:
            self._clients = clients

        self._init_profiler(context)

    def _choose_user(self, context):
        """Choose one user from users context

        We are choosing on each iteration one user

        """
        if context["user_choice_method"] == "random":
            user = random.choice(context["users"])
            tenant = context["tenants"][user["tenant_id"]]
        else:
            # Second and last case - 'round_robin'.
            tenants_amount = len(context["tenants"])
            # NOTE(amaretskiy): iteration is subtracted by `1' because it
            #                   starts from `1' but we count from `0'
            iteration = context["iteration"] - 1
            tenant_index = int(iteration % tenants_amount)
            tenant_id = sorted(context["tenants"].keys())[tenant_index]
            tenant = context["tenants"][tenant_id]
            users = context["tenants"][tenant_id]["users"]
            user_index = int((iteration / tenants_amount) % len(users))
            user = users[user_index]

        context["user"], context["tenant"] = user, tenant

    def clients(self, client_type, version=None):
        """Returns a python openstack client of the requested type.

        Only one non-admin user is used per every run of scenario.

        :param client_type: Client type ("nova"/"glance" etc.)
        :param version: client version ("1"/"2" etc.)

        :returns: Standard python OpenStack client instance
        """
        client = getattr(self._clients, client_type)

        return client(version) if version is not None else client()

    def admin_clients(self, client_type, version=None):
        """Returns a python admin openstack client of the requested type.

        :param client_type: Client type ("nova"/"glance" etc.)
        :param version: client version ("1"/"2" etc.)

        :returns: Python openstack client object
        """
        client = getattr(self._admin_clients, client_type)

        return client(version) if version is not None else client()

    def _init_profiler(self, context):
        """Inits the profiler."""
        if not CONF.openstack.enable_profiler:
            return
        if context is not None:
            cred = None
            profiler_hmac_key = None
            profiler_conn_str = None
            if context.get("admin"):
                cred = context["admin"]["credential"]
                if cred.profiler_hmac_key is not None:
                    profiler_hmac_key = cred.profiler_hmac_key
                    profiler_conn_str = cred.profiler_conn_str
            if context.get("user"):
                cred = context["user"]["credential"]
                if cred.profiler_hmac_key is not None:
                    profiler_hmac_key = cred.profiler_hmac_key
                    profiler_conn_str = cred.profiler_conn_str
            if profiler_hmac_key is None:
                return
            profiler.init(profiler_hmac_key)
            trace_id = profiler.get().get_base_id()
            complete_data = {"title": "OSProfiler Trace-ID",
                             "chart_plugin": "OSProfiler",
                             "data": {"trace_id": [trace_id],
                                      "conn_str": profiler_conn_str}}
            self.add_output(complete=complete_data)
