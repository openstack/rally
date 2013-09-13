# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

from rally import exceptions
from rally import utils


class VMProviderFactory(object):
    """rally.vmprovider.provider.VMProviderFactory is base class for providers

    All provider should be added to rally.vmprovider.providers.some_moduule.py
    and implement 4 methods:
        *) upload_image
        *) destroy_image
        *) create_vms
        *) destroy_vms.
    """
    __metaclass__ = abc.ABCMeta

    @staticmethod
    def get_provider(name, config):
        """Returns instance of vm provider by name."""
        for provider in utils.itersubclasses(VMProviderFactory):
            if name == provider.__name__:
                return provider(config)
        raise exceptions.NoSuchVMProvider(vm_provider_name=name)

    @staticmethod
    def get_available_providers():
        """Returns list of names of available engines."""
        return [e.__name__ for e in utils.itersubclasses(VMProviderFactory)]

    def upload_image(self, image):
        """Upload image that could be used in creating new vms.
        :image: Image file
        Returns uuid of added image.
        """
        raise NotImplementedError()

    def destroy_image(self, image_uuid):
        """Destroy image by image_uuid."""
        raise NotImplementedError()

    @abc.abstractmethod
    def create_vms(self, image_uuid=None, amount=1):
        """Create VMs with chosen image.
        :param image_uuid: Indetificator of image
        :param amount: amount of required VMs
        Returns list of VMs uuids.
        """
        pass

    @abc.abstractmethod
    def destroy_vms(self, vm_uuids):
        """Destroy already created vms by vm_uuids."""
        pass
