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
