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
from rally.common import log as logging
from rally import consts

import random

LOG = logging.getLogger(__name__)


class CinderVolumes(utils.CinderScenario,
                    nova_utils.NovaScenario):
    """Benchmark scenarios for Cinder Volumes."""

    @validation.required_services(consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["cinder"]})
    def create_and_list_volume(self, size, detailed=True, **kwargs):
        """Create a volume and list all volumes.

        Measure the "cinder volume-list" command performance.

        If you have only 1 user in your context, you will
        add 1 volume on every iteration. So you will have more
        and more volumes and will be able to measure the
        performance of the "cinder volume-list" command depending on
        the number of images owned by users.

        :param size: volume size (in GB)
        :param detailed: determines whether the volume listing should contain
                         detailed information about all of them
        :param kwargs: optional args to create a volume
        """
        self._create_volume(size, **kwargs)
        self._list_volumes(detailed)

    @validation.required_services(consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["cinder"]})
    def list_volumes(self, detailed=True):
        """List all volumes.

        This simple scenario tests the cinder list command by listing
        all the volumes.

        :param detailed: True if detailed information about volumes
                         should be listed
        """

        self._list_volumes(detailed)

    @validation.required_services(consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["cinder"]})
    def create_and_delete_volume(self, size, min_sleep=0, max_sleep=0,
                                 **kwargs):
        """Create and then delete a volume.

        Good for testing a maximal bandwidth of cloud. Optional 'min_sleep'
        and 'max_sleep' parameters allow the scenario to simulate a pause
        between volume creation and deletion (of random duration from
        [min_sleep, max_sleep]).

        :param size: volume size (in GB)
        :param min_sleep: minimum sleep time between volume creation and
                          deletion (in seconds)
        :param max_sleep: maximum sleep time between volume creation and
                          deletion (in seconds)
        :param kwargs: optional args to create a volume
        """
        volume = self._create_volume(size, **kwargs)
        self.sleep_between(min_sleep, max_sleep)
        self._delete_volume(volume)

    @validation.required_services(consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["cinder"]})
    def create_volume(self, size, **kwargs):
        """Create a volume.

        Good test to check how influence amount of active volumes on
        performance of creating new.

        :param size: volume size (in GB)
        :param kwargs: optional args to create a volume
        """
        self._create_volume(size, **kwargs)

    @validation.required_services(consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["cinder"]})
    def create_and_extend_volume(self, size, new_size, min_sleep=0,
                                 max_sleep=0, **kwargs):
        """Create and extend a volume and then delete it.


        :param size: volume size (in GB)
        :param new_size: volume new size (in GB) to extend
        :param min_sleep: minimum sleep time between volume extension and
                          deletion (in seconds)
        :param max_sleep: maximum sleep time between volume extension and
                          deletion (in seconds)
        :param kwargs: optinal args to extend the volume
        """
        volume = self._create_volume(size, **kwargs)
        self._extend_volume(volume, new_size)
        self.sleep_between(min_sleep, max_sleep)
        self._delete_volume(volume)

    @validation.required_services(consts.Service.CINDER)
    @validation.required_contexts("volumes")
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["cinder"]})
    def create_and_delete_snapshot(self, force=False, min_sleep=0,
                                   max_sleep=0, **kwargs):
        """Create and then delete a volume-snapshot.

        Optional 'min_sleep' and 'max_sleep' parameters allow the scenario
        to simulate a pause between snapshot creation and deletion
        (of random duration from [min_sleep, max_sleep]).

        :param force: when set to True, allows snapshot of a volume when
                      the volume is attached to an instance
        :param min_sleep: minimum sleep time between snapshot creation and
                          deletion (in seconds)
        :param max_sleep: maximum sleep time between snapshot creation and
                          deletion (in seconds)
        :param kwargs: optional args to create a shapshot
        """
        volume = random.choice(self.context["tenant"]["volumes"])
        snapshot = self._create_snapshot(volume["id"], force=force, **kwargs)
        self.sleep_between(min_sleep, max_sleep)
        self._delete_snapshot(snapshot)

    @types.set(image=types.ImageResourceType,
               flavor=types.FlavorResourceType)
    @validation.image_valid_on_flavor("flavor", "image")
    @validation.required_services(consts.Service.NOVA, consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["cinder", "nova"]})
    def create_and_attach_volume(self, size, image, flavor, **kwargs):
        """Create a VM and attach a volume to it.

        Simple test to create a VM and attach a volume, then
        detach the volume and delete volume/VM.

        :param size: volume size (in GB)
        :param image: Glance image name to use for the VM
        :param flavor: VM flavor name
        :param kwargs: optional arguments for VM/volume creation
        """
        if "volume_size" in kwargs:
            import warnings
            warnings.warn("'volume_size' argument is deprecated. You should "
                          "use 'size' instead.")
            size = kwargs["volume_size"]

        server = self._boot_server(
            self._generate_random_name(), image, flavor, **kwargs)
        volume = self._create_volume(size, **kwargs)

        self._attach_volume(server, volume)
        self._detach_volume(server, volume)

        self._delete_volume(volume)
        self._delete_server(server)

    @validation.volume_type_exists("volume_type")
    @validation.required_services(consts.Service.NOVA, consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["cinder", "nova"]})
    def create_snapshot_and_attach_volume(self, volume_type=False,
                                          size=None, **kwargs):

        """Create volume, snapshot and attach/detach volume.

        This scenario is based off of the standalone qaStressTest.py
        (https://github.com/WaltHP/cinder-stress).

        :param volume_type: Whether or not to specify volume type when creating
                            volumes.
        :param size: Volume size - dictionary, contains two values:
                        min - minimum size volumes will be created as;
                        max - maximum size volumes will be created as.
                     default values: {"min": 1, "max": 5}
        :param kwargs: Optional parameters used during volume
                       snapshot creation.
        """
        if "min_size" in kwargs or "max_size" in kwargs:
            import warnings
            warnings.warn("'min_size' and 'max_size' arguments "
                          "are deprecated. You should use 'size', with "
                          "keys 'min' and 'max' instead.")
        if "volume_size" in kwargs:
            import warnings
            warnings.warn("'volume_size' argument is deprecated. You should "
                          "use 'size' instead.")
            size = kwargs["volume_size"]

        if size is None:
            size = {"min": 1, "max": 5}
        selected_type = None
        volume_types = [None]

        if volume_type:
            volume_types_list = self.clients("cinder").volume_types.list()
            for s in volume_types_list:
                volume_types.append(s.name)
            selected_type = random.choice(volume_types)

        size = random.randint(size['min'], size['max'])

        volume = self._create_volume(size, volume_type=selected_type)
        snapshot = self._create_snapshot(volume.id, False, **kwargs)

        server = self.get_random_server()

        self._attach_volume(server, volume)
        self._detach_volume(server, volume)

        self._delete_snapshot(snapshot)
        self._delete_volume(volume)

    @validation.required_services(consts.Service.NOVA, consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["cinder", "nova"]})
    def create_nested_snapshots_and_attach_volume(self,
                                                  size=None,
                                                  nested_level=None,
                                                  **kwargs):

        """Create a volume from snapshot and attach/detach the volume

        This scenario create volume, create it's snapshot, attach volume,
        then create new volume from existing snapshot and so on,
        with defined nested level, after all detach and delete them.
        volume->snapshot->volume->snapshot->volume ...

        :param size: Volume size - dictionary, contains two values:
                        min - minimum size volumes will be created as;
                        max - maximum size volumes will be created as.
                     default values: {"min": 1, "max": 5}
        :param nested_level: Nested level - dictionary, contains two values:
                               min - minimum number of volumes will be created
                                     from snapshot;
                               max - maximum number of volumes will be created
                                     from snapshot.
                             default values: {"min": 5, "max": 10}
        :param kwargs: Optional parameters used during volume
                       snapshot creation.
        """
        if "volume_size" in kwargs:
            import warnings
            warnings.warn("'volume_size' argument is deprecated. You should "
                          "use 'size' instead.")
            size = kwargs["volume_size"]

        if size is None:
            size = {"min": 1, "max": 5}
        if nested_level is None:
            nested_level = {"min": 5, "max": 10}

        size = random.randint(size['min'], size['max'])
        nested_level = random.randint(nested_level['min'], nested_level['max'])

        servers = [self.get_random_server()]
        volumes = [self._create_volume(size)]
        snapshots = [self._create_snapshot(volumes[0].id, False, **kwargs)]

        self._attach_volume(servers[0], volumes[0])

        snapshot = snapshots[0]
        for i in range(nested_level - 1):
            volume = self._create_volume(size, snapshot_id=snapshot.id)
            snapshot = self._create_snapshot(volume.id, False, **kwargs)
            server = self.get_random_server()

            servers.append(server)
            volumes.append(volume)
            snapshots.append(snapshot)

            self._attach_volume(server, volume)

        for server, volume, snapshot in zip(servers, volumes, snapshots):
            self._detach_volume(server, volume)
            self._delete_snapshot(snapshot)
            self._delete_volume(volume)

    @validation.required_services(consts.Service.CINDER)
    @validation.required_contexts("volumes")
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["cinder"]})
    def create_and_list_snapshots(self, force=False, detailed=True, **kwargs):
        """Create and then list a volume-snapshot.


        :param force: when set to True, allows snapshot of a volume when
                      the volume is attached to an instance
        :param detailed: True if detailed information about snapshots
                         should be listed
        :param kwargs: optional args to create a snapshot
        """
        volume = random.choice(self.context["tenant"]["volumes"])
        self._create_snapshot(volume["id"], force=force, **kwargs)
        self._list_snapshots(detailed)
