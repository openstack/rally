# Copyright 2013 Huawei Technologies Co.,LTD.
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

from rally.benchmark.scenarios import base
from rally.benchmark.scenarios.cinder import utils
from rally.benchmark.scenarios.nova import utils as nova_utils
from rally.benchmark import types as types
from rally.benchmark import validation
from rally import consts


class CinderVolumes(utils.CinderScenario,
                    nova_utils.NovaScenario):

    @validation.required_services(consts.Service.CINDER)
    @base.scenario(context={"cleanup": ["cinder"]})
    def create_and_list_volume(self, size, detailed=True, **kwargs):
        """Tests creating a volume and listing volumes.

           This scenario is a very useful tool to measure
           the "cinder volume-list" command performance.

           If you have only 1 user in your context, you will
           add 1 volume on every iteration. So you will have more
           and more volumes and will be able to measure the
           performance of the "cinder volume-list" command depending on
           the number of images owned by users.
        """

        self._create_volume(size, **kwargs)
        self._list_volumes(detailed)

    @validation.required_services(consts.Service.CINDER)
    @base.scenario(context={"cleanup": ["cinder"]})
    def create_and_delete_volume(self, size, min_sleep=0, max_sleep=0,
                                 **kwargs):
        """Tests creating and then deleting a volume.

        Good for testing a maximal bandwidth of cloud.
        """

        volume = self._create_volume(size, **kwargs)
        self.sleep_between(min_sleep, max_sleep)
        self._delete_volume(volume)

    @validation.required_services(consts.Service.CINDER)
    @base.scenario(context={"cleanup": ["cinder"]})
    def create_volume(self, size, **kwargs):
        """Test creating volumes perfromance.

        Good test to check how influence amount of active volumes on
        performance of creating new.
        """
        self._create_volume(size, **kwargs)

    @base.scenario(context={"cleanup": ["cinder"]})
    @validation.required_services(consts.Service.CINDER)
    @validation.required_contexts("volumes")
    def create_and_delete_snapshot(self, force=False, min_sleep=0,
                                   max_sleep=0, **kwargs):
        """Tests creating and then deleting a volume-snapshot."""
        tenant_id = self.context()["user"]["tenant_id"]
        volumes = self.context()["volumes"]
        for volume in volumes:
            if tenant_id == volume["tenant_id"]:
                volume_id = volume["volume_id"]

        snapshot = self._create_snapshot(volume_id, force=force, **kwargs)
        self.sleep_between(min_sleep, max_sleep)
        self._delete_snapshot(snapshot)

    @types.set(image=types.ImageResourceType,
               flavor=types.FlavorResourceType)
    @validation.image_valid_on_flavor("flavor", "image")
    @validation.required_services(consts.Service.NOVA, consts.Service.CINDER)
    @base.scenario(context={"cleanup": ["cinder", "nova"]})
    def create_and_attach_volume(self, volume_size, image, flavor,
                                 min_sleep=0, max_sleep=0, **kwargs):

        """Tests creating a VM and attaching a volume.

        Simple test to create a vm and attach a volume, then
        detach the volume and cleanup.

        :param volume_size: The size of the volume to create
        :param image: The glance image name to use for the vm
        :param flavor: the VM flavor name

        """

        server = self._boot_server(
            self._generate_random_name(), image, flavor, **kwargs)
        volume = self._create_volume(volume_size, **kwargs)

        self._attach_volume(server, volume)
        self._detach_volume(server, volume)

        self._delete_volume(volume)
        self._delete_server(server)
