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

import six.moves.xmlrpc_client as xmlrpclib

from rally.common.i18n import _
from rally.deployment.serverprovider import provider


@provider.configure(name="CobblerProvider")
class CobblerProvider(provider.ProviderFactory):
    """Creates servers via PXE boot from given cobbler selector.

    Cobbler selector may contain a combination of fields
    to select a number of system. It's user responsibility to provide selector
    which selects something. Since cobbler stores servers password encrypted
    the user needs to specify it configuration. All servers selected must have
    the same password.

    Sample configuration:

    .. code-block:: json

        {
            "type": "CobblerProvider",
            "host": "172.29.74.8",
            "user": "cobbler",
            "password": "cobbler",
            "system_password": "password"
            "selector": {"profile": "cobbler_profile_name", "owners": "user1"}
        }

    """

    COBBLER_SELECTOR_SCHEMA = {
        "type": "object",
        "properties": {
            "profile": "string",
            "owners": "string"
        }
    }

    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "host": {"type": "string"},
            "user": {"type": "string"},
            "password": {"type": "string"},
            "system_password": {"type": "string"},
            "selector": {"type": "object", "item": COBBLER_SELECTOR_SCHEMA},
        },
        "required": ["host", "user", "password", "selector"]
    }

    def __init__(self, deployment, config):
        super(CobblerProvider, self).__init__(deployment, config)
        self.config = config
        self.cobbler = xmlrpclib.Server(uri="http://%s/cobbler_api" %
                                            config["host"])

    @staticmethod
    def ip_for_system(rendered_system):
        for key, value in rendered_system.items():
            if "ip_address" in key and value:
                return value
        raise RuntimeError(_("No valid ip address found for system ")
                           + "'%s'" % rendered_system["name"])

    def create_by_rebooting(self, system_name):
        """Ask cobbler to re-boot server which is controlled by given system.

        :param system_name: cobbler object as seen in Cobbler WebGUI
        :returns: rally Server
        """
        token = self.cobbler.login(self.config["user"],
                                   self.config["password"])
        handle = self.cobbler.get_system_handle(system_name, token)
        self.cobbler.power_system(handle, "reboot", token)
        rendered = self.cobbler.get_system_as_rendered(system_name)
        return provider.Server(host=self.ip_for_system(rendered),
                               user=rendered["power_user"],
                               key=rendered.get("redhat_management_key"),
                               password=self.config.get("system_password", ""),
                               port=22)

    def create_servers(self):
        systems = self.cobbler.find_system(dict(self.config["selector"]))
        if not systems:
            raise RuntimeError(_("No associated systems selected by ")
                               + "%s" % self.config["selector"])

        servers = [self.create_by_rebooting(system) for system in systems]
        return servers

    def destroy_servers(self):
        """Don't implement this.

        Since bare metal servers are usually getting out of operation by
        powering off, it's better to allow the user to decide how to do it.
        """
        pass
