# Copyright 2013: Mirantis Inc.
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


from rally.deployment.serverprovider import provider


@provider.configure(name="ExistingServers")
class ExistingServers(provider.ProviderFactory):
    """Just return endpoints from its own configuration.

    Sample configuration:

    .. code-block:: json

        {
            "type": "ExistingServers",
            "credentials": [{"user": "root", "host": "localhost"}]
        }
    """

    CREDENTIALS_SCHEMA = {
        "type": "object",
        "properties": {
            "host": {"type": "string"},
            "port": {"type": "integer"},
            "user": {"type": "string"},
            "key": {"type": "string"},
            "password": {"type": "string"}
        },
        "required": ["host", "user"]
    }

    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "type": {"type": "string"},
            "credentials": {
                "type": "array",
                "items": CREDENTIALS_SCHEMA
            },
        },
        "required": ["credentials"]
    }

    def __init__(self, deployment, config):
        super(ExistingServers, self).__init__(deployment, config)
        self.credentials = config["credentials"]

    def create_servers(self):
        servers = []
        for credential in self.credentials:
            servers.append(provider.Server(host=credential["host"],
                                           user=credential["user"],
                                           key=credential.get("key"),
                                           password=credential.get("password"),
                                           port=credential.get("port", 22)))
        return servers

    def destroy_servers(self):
        pass
