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


import os
import random

import six

from rally.common.i18n import _
from rally.common import utils as rutils
from rally import osclients
from rally.plugins.openstack import scenario
from rally.task import atomic


class FuelEnvManager(object):

    def __init__(self, client):
        self.client = client

    def get(self, env_id):
        try:
            return self.client.get_by_id(env_id)
        except BaseException:
            return None

    def list(self):
        """List Fuel environments."""
        try:
            return self.client.get_all()
        except SystemExit:
            raise RuntimeError(_("Can't list environments. "
                                 "Please check server availability."))

    def create(self, name, release_id=1,
               network_provider="neutron",
               deployment_mode="ha_compact",
               net_segment_type="vlan"):
        try:
            env = self.client.create(name, release_id, network_provider,
                                     deployment_mode, net_segment_type)
        except SystemExit:
            raise RuntimeError(_("Something went wrong while creating an "
                                 "environment. This can happen when "
                                 "environment with name %s already exists.")
                               % name)

        if env:
            return env
        raise RuntimeError(_("Environment was not created or was "
                             "created but not returned by server."))

    def delete(self, env_id, retries=5, retry_pause=0.5):
        env = self.get(env_id)
        retry_number = 0
        while env:
            if retry_number > retries:
                raise RuntimeError(_("Can't delete environment "
                                     "id: %s ") % env_id)
            try:
                self.client.delete_by_id(env_id)
            except BaseException:
                rutils.interruptable_sleep(retry_pause)
            env = self.get(env_id)
            retry_number += 1


class FuelClient(object):
    """Thin facade over `fuelclient.get_client'."""

    def __init__(self, version, server_address, server_port, username,
                 password):

        # NOTE(amaretskiy): For now, there are only 2 ways how to
        #   configure fuelclient connection:
        #     * configuration file - this is not convenient to create
        #                            separate file for each benchmark
        #     * env variables - this approach is preferable
        os.environ["SERVER_ADDRESS"] = server_address
        os.environ["LISTEN_PORT"] = str(server_port)
        os.environ["KEYSTONE_USER"] = username
        os.environ["KEYSTONE_PASS"] = password

        import fuelclient
        FuelClient.fuelclient_module = fuelclient

        get_client = fuelclient.get_client

        self.environment = FuelEnvManager(get_client(
            "environment", version=version))
        self.node = get_client("node", version=version)
        self.task = get_client("task", version=version)


@osclients.configure("fuel", default_version="v1")
class Fuel(osclients.OSClient):
    """FuelClient factory for osclients.Clients."""
    def create_client(self, *args, **kwargs):
        auth_url = six.moves.urllib.parse.urlparse(self.credential.auth_url)
        return FuelClient(version=self.choose_version(),
                          server_address=auth_url.hostname,
                          server_port=8000,
                          username=self.credential.username,
                          password=self.credential.password)


class FuelScenario(scenario.OpenStackScenario):
    """Base class for Fuel scenarios."""

    @atomic.action_timer("fuel.list_environments")
    def _list_environments(self):
        return self.admin_clients("fuel").environment.list()

    @atomic.action_timer("fuel.create_environment")
    def _create_environment(self, release_id=1,
                            network_provider="neutron",
                            deployment_mode="ha_compact",
                            net_segment_type="vlan"):
        name = self.generate_random_name()
        env = self.admin_clients("fuel").environment.create(
            name, release_id, network_provider, deployment_mode,
            net_segment_type)
        return env["id"]

    @atomic.action_timer("fuel.delete_environment")
    def _delete_environment(self, env_id, retries=5):
        self.admin_clients("fuel").environment.delete(env_id, retries)

    @atomic.action_timer("fuel.add_node")
    def _add_node(self, env_id, node_ids, node_roles=None):
        """Add node to environment

        :param env_id: environment id
        :param node_ids: list of node ids
        :param node_roles: list of roles
        """

        node_roles = node_roles or ["compute"]

        try:
            self.admin_clients("fuel").environment.client.add_nodes(
                env_id, node_ids, node_roles)
        except BaseException as e:
            raise RuntimeError(
                "Unable to add node(s) to environment. Fuel client exited "
                "with error %s" % e)

    @atomic.action_timer("fuel.delete_node")
    def _remove_node(self, env_id, node_id):

        env = FuelClient.fuelclient_module.objects.environment.Environment(
            env_id)
        try:
            env.unassign([node_id])
        except BaseException as e:
            raise RuntimeError(
                "Unable to add node(s) to environment. Fuel client exited "
                "with error %s" % e)

    @atomic.action_timer("fuel.list_nodes")
    def _list_node_ids(self, env_id=None):
        result = self.admin_clients("fuel").node.get_all(
            environment_id=env_id)
        return [x["id"] for x in result]

    def _node_is_assigned(self, node_id):
        try:
            node = self.admin_clients("fuel").node.get_by_id(node_id)
            return bool(node["cluster"])
        except BaseException as e:
            raise RuntimeError(
                "Unable to add node(s) to environment. Fuel client exited "
                "with error %s" % e)

    def _get_free_node_id(self):
        node_ids = self._list_node_ids()
        random.shuffle(node_ids)

        for node_id in node_ids:
            if not self._node_is_assigned(node_id):
                return node_id
        else:
            raise RuntimeError("Can not found free node.")
