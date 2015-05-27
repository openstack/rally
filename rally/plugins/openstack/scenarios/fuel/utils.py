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

import six

from rally.benchmark.scenarios import base
from rally import osclients


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
        get_client = fuelclient.get_client
        self.environment = get_client("environment", version=version)
        self.node = get_client("node", version=version)
        self.task = get_client("task", version=version)


@osclients.Clients.register("fuel")
def fuel(instance):
    """FuelClient factory for osclients.Clients."""
    auth_url = six.moves.urllib.parse.urlparse(instance.endpoint.auth_url)
    return FuelClient(version="v1",
                      server_address=auth_url.hostname,
                      server_port=8000,
                      username=instance.endpoint.username,
                      password=instance.endpoint.password)


class FuelScenario(base.Scenario):
    """Base class for Fuel scenarios."""

    @base.atomic_action_timer("fuel.list_environments")
    def _list_environments(self):
        """List Fuel environments."""
        return self.admin_clients("fuel").environment.get_all()
