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

import random

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.cinder import utils as cinder_utils
from rally.task import validation


"""Scenarios for Cinder Volume Type."""


@validation.required_services(consts.Service.CINDER)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["cinder"]},
                    name="CinderVolumeTypes.create_and_delete_volume_type")
class CreateAndDeleteVolumeType(cinder_utils.CinderScenario):

    def run(self, **kwargs):
        """Create and delete a volume Type.

        :param kwargs: Optional parameters used during volume
                       type creation.
        """
        volume_type = self._create_volume_type(**kwargs)
        self._delete_volume_type(volume_type)


@validation.required_services(consts.Service.CINDER)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["cinder"]},
                    name="CinderVolumeTypes.create_volume_type"
                         "_and_encryption_type")
class CreateVolumeTypeAndEncryptionType(cinder_utils.CinderScenario):

    def run(self, specs, **kwargs):
        """Create encryption type

          This scenario first creates a volume type, then creates an encryption
          type for the volume type.

        :param specs: the encryption type specifications to add
        :param kwargs: Optional parameters used during volume
                       type creation.
        """
        volume_type = self._create_volume_type(**kwargs)
        self._create_encryption_type(volume_type, specs)


@validation.required_services(consts.Service.CINDER)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["cinder"]},
                    name="CinderVolumeTypes.create_and_list_"
                         "encryption_type")
class CreateAndListEncryptionType(cinder_utils.CinderScenario):

    def run(self, specs, search_opts=None, **kwargs):
        """Create and list encryption type

          This scenario firstly creates a volume type, secondly creates an
          encryption type for the volume type, thirdly lists all encryption
          types.

        :param specs: the encryption type specifications to add
        :param search_opts: Options used when search for encryption types
        :param kwargs: Optional parameters used during volume
                       type creation.
        """
        volume_type = self._create_volume_type(**kwargs)
        self._create_encryption_type(volume_type, specs)
        self._list_encryption_type(search_opts)


@validation.required_services(consts.Service.CINDER)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["cinder"]},
                    name="CinderVolumeTypes.create_and_set_volume_type_keys")
class CreateAndSetVolumeTypeKeys(cinder_utils.CinderScenario):

    def run(self, volume_type_key, **kwargs):
        """Create and set a volume type's extra specs.

        :param volume_type_key:  A dict of key/value pairs to be set
        :param kwargs: Optional parameters used during volume
                       type creation.
        """
        volume_type = self._create_volume_type(**kwargs)

        self._set_volume_type_keys(volume_type, volume_type_key)


@validation.required_services(consts.Service.CINDER)
@validation.required_contexts("volume_types")
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["cinder"]},
                    name="CinderVolumeTypes.create_and_delete_"
                         "encryption_type")
class CreateAndDeleteEncryptionType(cinder_utils.CinderScenario):

    def run(self, create_specs):
        """Create and delete encryption type

          This scenario firstly creates an encryption type for a given
          volume type, then deletes the created encryption type.

        :param create_specs: the encryption type specifications to add
        """
        volume_type = random.choice(self.context["volume_types"])
        self._create_encryption_type(volume_type["id"], create_specs)
        self._delete_encryption_type(volume_type["id"])
