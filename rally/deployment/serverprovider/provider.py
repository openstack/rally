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

import abc

import jsonschema
import six

from rally.common.plugin import plugin
from rally.common import sshutils
from rally.common import utils

configure = plugin.configure


class Server(utils.ImmutableMixin):
    """Represent information about created Server.

    Provider.create_servers should return list of instance of Server
    """
    def __init__(self, host, user, key=None, password=None, port=22):
        self.host = host
        self.port = port
        self.user = user
        self.key = key
        self.password = password
        self.ssh = sshutils.SSH(user, host, key_filename=key, port=port,
                                password=password)
        super(Server, self).__init__()

    def get_credentials(self):
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "key": self.key,
            "password": self.password,
        }

    @classmethod
    def from_credentials(cls, creds):
        return cls(creds["host"], creds["user"], key=creds["key"],
                   port=creds["port"], password=creds["password"])


class ResourceManager(object):
    """Supervise resources of a deployment.

    :param deployment: a dict with data on a deployment
    :param provider_name: a string of a name of the provider
    """
    def __init__(self, deployment, provider_name):
        self.deployment = deployment
        self.provider_name = provider_name

    def create(self, info, type=None):
        """Create a resource.

        :param info: a payload of a resource
        :param type: a string of a resource or None
        :returns: a list of dicts with data on a resource
        """
        return self.deployment.add_resource(self.provider_name, type=type,
                                            info=info)

    def get_all(self, type=None):
        """Return registered resources.

        :param type: a string to filter by a type, if is None, then
                     returns all
        :returns: a list of dicts with data on a resource
        """
        return self.deployment.get_resources(provider_name=self.provider_name,
                                             type=type)

    def delete(self, resource_id):
        """Delete a resource.

        :param resource_id: an ID of a resource
        """
        self.deployment.delete_resource(resource_id)


@plugin.base()
@six.add_metaclass(abc.ABCMeta)
class ProviderFactory(plugin.Plugin):
    """Base class of all server providers.

    It's a base class with self-discovery of subclasses. Each subclass
    has to implement create_servers() and destroy_servers() methods.
    By default, each server provider located as a submodule of the package
    rally.deployment.serverprovider.providers is auto-discovered.

    Each provider supervises its own resources using a ResourceManager.

    Example of usage with a simple provider:

    .. code-block:: python

        # Add new provider with __name__ == "A"
        class A(ProviderFactory):
            def __init__(self, deployment, config):
                # do something

            def create_servers(self, image_uuid, type_id, amount):
                # Create the requested number of servers of a given type from
                # the image passed as the first parameter.
                return [server_1, server_2, ...]

            def destroy_servers(self):
                # Destroy servers created in create_servers().
    """

    def __init__(self, deployment, config):
        self.deployment = deployment
        self.config = config
        self.resources = ResourceManager(deployment,
                                         self.__class__.__name__)
        self.validate()

    def validate(self):
        # TODO(miarmak): remove this checking, when config schema is done for
        # all available providers
        if hasattr(self, "CONFIG_SCHEMA"):
            jsonschema.validate(self.config, self.CONFIG_SCHEMA)

    # FIXME(boris-42): Remove this method. And explicit create provider
    @staticmethod
    def get_provider(config, deployment):
        """Returns instance of server provider by name."""
        provider_cls = ProviderFactory.get(config["type"])
        return provider_cls(deployment, config)

    @abc.abstractmethod
    def create_servers(self, image_uuid=None, type_id=None, amount=1):
        """Create VMs with chosen image.

        :param image_uuid: Identificator of image
        :param type_id: Vm type identificator
        :param amount: amount of required VMs
        :returns: list of Server instances.
        """
        pass

    @abc.abstractmethod
    def destroy_servers(self):
        """Destroy already created vms."""
        pass
