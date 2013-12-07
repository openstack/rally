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

from rally import exceptions
from rally import sshutils
from rally import utils


class Server(utils.ImmutableMixin):
    """Represent information about created Server.
    Provider.create_vms should return list of instance of Server
    """
    def __init__(self, uuid, ip, user, key, password=None):
        self.uuid = uuid
        self.ip = ip
        self.user = user
        self.key = key
        self.password = password
        self.ssh = sshutils.SSH(ip, user)
        super(Server, self).__init__()

    def get_credentials(self):
        return {
            'uuid': self.uuid,
            'ip': self.ip,
            'user': self.user,
            'key': self.key,
            'password': self.password,
        }

    @classmethod
    def from_credentials(cls, creds):
        return cls(creds['uuid'], creds['ip'], creds['user'], creds['key'],
                   password=creds['password'])


class ImageDTO(utils.ImmutableMixin):
    """Represent information about created image.
    ProviderFactory.upload_image should return instance of this class.
    """
    def __init__(self, uuid, image_format, container_format):
        self.uuid = uuid
        self.image_format = image_format
        self.container_format = container_format
        super(ImageDTO, self).__init__()


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


class ProviderFactory(object):
    """ProviderFactory should be base class for all providers.

    Each provider supervises own resources using ResourceManager.

    All provider should be added to rally.vmprovider.providers.some_moduule.py
    and implement 4 methods:
        *) upload_image
        *) destroy_image
        *) create_vms
        *) destroy_vms.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, deployment, config):
        self.deployment = deployment
        self.config = config
        self.resources = ResourceManager(deployment,
                                         self.__class__.__name__)
        self.validate()

    def validate(self):
        # TODO(miarmak): remove this checking, when config schema is done for
        # all available providers
        if hasattr(self, 'CONFIG_SCHEMA'):
            jsonschema.validate(self.config, self.CONFIG_SCHEMA)

    @staticmethod
    def get_provider(config, deployment):
        """Returns instance of vm provider by name."""
        name = config['name']
        for provider in utils.itersubclasses(ProviderFactory):
            if name == provider.__name__:
                return provider(deployment, config)
        raise exceptions.NoSuchVMProvider(vm_provider_name=name)

    @staticmethod
    def get_available_providers():
        """Returns list of names of available engines."""
        return [e.__name__ for e in utils.itersubclasses(ProviderFactory)]

    # TODO(akscram): Unsed method.
    def upload_image(self, file_path, disk_format, container_format):
        """Upload image that could be used in creating new vms.
        :file_path: Path to the file with image
        :disk_format: qcow, qcow2, iso and so on..
        :container_format: bare, ovf, aki and so on..
            For more details about formats take a look at:
            http://docs.openstack.org/developer/glance/formats.html

        :returns: ImageDTO instance
        """
        raise NotImplementedError()

    # TODO(akscram): Unsed method.
    def destroy_image(self, image_uuid):
        """Destroy image by image indentificator."""
        raise NotImplementedError()

    @abc.abstractmethod
    def create_vms(self, image_uuid=None, type_id=None, amount=1):
        """Create VMs with chosen image.
        :param image_uuid: Indetificator of image
        :param type_id: Vm type identificator
        :param amount: amount of required VMs
        :returns: list of Server instances.
        """
        pass

    @abc.abstractmethod
    def destroy_vms(self):
        """Destroy already created vms."""
        pass
