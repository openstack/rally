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

import random

from rally.common import logging
from rally import consts
from rally import exceptions
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.cinder import utils as cinder_utils
from rally.plugins.openstack.scenarios.glance import utils as glance_utils
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.task import atomic
from rally.task import types
from rally.task import validation


class CinderVolumes(cinder_utils.CinderScenario,
                    nova_utils.NovaScenario,
                    glance_utils.GlanceScenario):
    """Benchmark scenarios for Cinder Volumes."""

    @types.convert(image={"type": "glance_image"})
    @validation.image_exists("image", nullable=True)
    @validation.required_services(consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["cinder"]})
    def create_and_list_volume(self, size, detailed=True,
                               image=None, **kwargs):
        """Create a volume and list all volumes.

        Measure the "cinder volume-list" command performance.

        If you have only 1 user in your context, you will
        add 1 volume on every iteration. So you will have more
        and more volumes and will be able to measure the
        performance of the "cinder volume-list" command depending on
        the number of images owned by users.

        :param size: volume size (integer, in GB) or
                     dictionary, must contain two values:
                         min - minimum size volumes will be created as;
                         max - maximum size volumes will be created as.
        :param detailed: determines whether the volume listing should contain
                         detailed information about all of them
        :param image: image to be used to create volume
        :param kwargs: optional args to create a volume
        """
        if image:
            kwargs["imageRef"] = image

        self._create_volume(size, **kwargs)
        self._list_volumes(detailed)

    @validation.required_services(consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["cinder"]})
    def list_volumes(self, detailed=True):
        """List all volumes.

        This simple scenario tests the cinder list command by listing
        all the volumes.

        :param detailed: True if detailed information about volumes
                         should be listed
        """

        self._list_volumes(detailed)

    @types.convert(image={"type": "glance_image"})
    @validation.image_exists("image", nullable=True)
    @validation.required_services(consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["cinder"]})
    def create_and_update_volume(self, size, image=None,
                                 create_volume_kwargs=None,
                                 update_volume_kwargs=None):
        """Create a volume and update its name and description.

        :param size: volume size (integer, in GB)
        :param image: image to be used to create volume
        :param create_volume_kwargs: dict, to be used to create volume
        :param update_volume_kwargs: dict, to be used to update volume
        """
        create_volume_kwargs = create_volume_kwargs or {}
        update_volume_kwargs = update_volume_kwargs or {}
        if image:
            create_volume_kwargs["imageRef"] = image
        volume = self._create_volume(size, **create_volume_kwargs)
        self._update_volume(volume, **update_volume_kwargs)

    @types.convert(image={"type": "glance_image"})
    @validation.image_exists("image", nullable=True)
    @validation.required_services(consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["cinder"]})
    def create_and_delete_volume(self, size, image=None,
                                 min_sleep=0, max_sleep=0,
                                 **kwargs):
        """Create and then delete a volume.

        Good for testing a maximal bandwidth of cloud. Optional 'min_sleep'
        and 'max_sleep' parameters allow the scenario to simulate a pause
        between volume creation and deletion (of random duration from
        [min_sleep, max_sleep]).

        :param size: volume size (integer, in GB) or
                     dictionary, must contain two values:
                         min - minimum size volumes will be created as;
                         max - maximum size volumes will be created as.
        :param image: image to be used to create volume
        :param min_sleep: minimum sleep time between volume creation and
                          deletion (in seconds)
        :param max_sleep: maximum sleep time between volume creation and
                          deletion (in seconds)
        :param kwargs: optional args to create a volume
        """
        if image:
            kwargs["imageRef"] = image

        volume = self._create_volume(size, **kwargs)
        self.sleep_between(min_sleep, max_sleep)
        self._delete_volume(volume)

    @types.convert(image={"type": "glance_image"})
    @validation.image_exists("image", nullable=True)
    @validation.required_services(consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["cinder"]})
    def create_volume(self, size, image=None, **kwargs):
        """Create a volume.

        Good test to check how influence amount of active volumes on
        performance of creating new.

        :param size: volume size (integer, in GB) or
                     dictionary, must contain two values:
                         min - minimum size volumes will be created as;
                         max - maximum size volumes will be created as.
        :param image: image to be used to create volume
        :param kwargs: optional args to create a volume
        """
        if image:
            kwargs["imageRef"] = image

        self._create_volume(size, **kwargs)

    @validation.required_services(consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @validation.required_contexts("volumes")
    @scenario.configure(context={"cleanup": ["cinder"]})
    def modify_volume_metadata(self, sets=10, set_size=3,
                               deletes=5, delete_size=3):
        """Modify a volume's metadata.

        This requires a volume to be created with the volumes
        context. Additionally, ``sets * set_size`` must be greater
        than or equal to ``deletes * delete_size``.

        :param sets: how many set_metadata operations to perform
        :param set_size: number of metadata keys to set in each
                         set_metadata operation
        :param deletes: how many delete_metadata operations to perform
        :param delete_size: number of metadata keys to delete in each
                            delete_metadata operation
        """
        if sets * set_size < deletes * delete_size:
            raise exceptions.InvalidArgumentsException(
                "Not enough metadata keys will be created: "
                "Setting %(num_keys)s keys, but deleting %(num_deletes)s" %
                {"num_keys": sets * set_size,
                 "num_deletes": deletes * delete_size})

        volume = random.choice(self.context["tenant"]["volumes"])
        keys = self._set_metadata(volume["id"], sets, set_size)
        self._delete_metadata(volume["id"], keys, deletes, delete_size)

    @validation.required_services(consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["cinder"]})
    def create_and_extend_volume(self, size, new_size, min_sleep=0,
                                 max_sleep=0, **kwargs):
        """Create and extend a volume and then delete it.


        :param size: volume size (in GB) or
                     dictionary, must contain two values:
                         min - minimum size volumes will be created as;
                         max - maximum size volumes will be created as.
        :param new_size: volume new size (in GB) or
                        dictionary, must contain two values:
                             min - minimum size volumes will be created as;
                             max - maximum size volumes will be created as.
                        to extend.
                        Notice: should be bigger volume size
        :param min_sleep: minimum sleep time between volume extension and
                          deletion (in seconds)
        :param max_sleep: maximum sleep time between volume extension and
                          deletion (in seconds)
        :param kwargs: optional args to extend the volume
        """
        volume = self._create_volume(size, **kwargs)
        self._extend_volume(volume, new_size)
        self.sleep_between(min_sleep, max_sleep)
        self._delete_volume(volume)

    @validation.required_services(consts.Service.CINDER)
    @validation.required_contexts("volumes")
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["cinder"]})
    def create_from_volume_and_delete_volume(self, size, min_sleep=0,
                                             max_sleep=0, **kwargs):
        """Create volume from volume and then delete it.

        Scenario for testing volume clone.Optional 'min_sleep' and 'max_sleep'
        parameters allow the scenario to simulate a pause between volume
        creation and deletion (of random duration from [min_sleep, max_sleep]).

        :param size: volume size (in GB), or
                     dictionary, must contain two values:
                         min - minimum size volumes will be created as;
                         max - maximum size volumes will be created as.
                     Should be equal or bigger source volume size

        :param min_sleep: minimum sleep time between volume creation and
                          deletion (in seconds)
        :param max_sleep: maximum sleep time between volume creation and
                          deletion (in seconds)
        :param kwargs: optional args to create a volume
        """
        source_vol = random.choice(self.context["tenant"]["volumes"])
        volume = self._create_volume(size, source_volid=source_vol["id"],
                                     **kwargs)
        self.sleep_between(min_sleep, max_sleep)
        self._delete_volume(volume)

    @validation.required_services(consts.Service.CINDER)
    @validation.required_contexts("volumes")
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["cinder"]})
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
        :param kwargs: optional args to create a snapshot
        """
        volume = random.choice(self.context["tenant"]["volumes"])
        snapshot = self._create_snapshot(volume["id"], force=force, **kwargs)
        self.sleep_between(min_sleep, max_sleep)
        self._delete_snapshot(snapshot)

    @types.convert(image={"type": "glance_image"},
                   flavor={"type": "nova_flavor"})
    @validation.image_valid_on_flavor("flavor", "image")
    @validation.required_services(consts.Service.NOVA, consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["cinder", "nova"]})
    @logging.log_deprecated_args(
        "Use 'create_vm_params' for additional instance parameters.",
        "0.2.0", ["kwargs"], once=True)
    def create_and_attach_volume(self, size, image, flavor,
                                 create_volume_params=None,
                                 create_vm_params=None, **kwargs):
        """Create a VM and attach a volume to it.

        Simple test to create a VM and attach a volume, then
        detach the volume and delete volume/VM.

        :param size: volume size (integer, in GB) or
                     dictionary, must contain two values:
                         min - minimum size volumes will be created as;
                         max - maximum size volumes will be created as.
        :param image: Glance image name to use for the VM
        :param flavor: VM flavor name
        :param create_volume_params: optional arguments for volume creation
        :param create_vm_params: optional arguments for VM creation
        :param kwargs: (deprecated) optional arguments for VM creation
        """

        create_volume_params = create_volume_params or {}

        if kwargs and create_vm_params:
            raise ValueError("You can not set both 'kwargs'"
                             "and 'create_vm_params' attributes."
                             "Please use 'create_vm_params'.")

        create_vm_params = create_vm_params or kwargs or {}

        server = self._boot_server(image, flavor, **create_vm_params)
        volume = self._create_volume(size, **create_volume_params)

        attachment = self._attach_volume(server, volume)
        self._detach_volume(server, volume, attachment)

        self._delete_volume(volume)
        self._delete_server(server)

    @validation.volume_type_exists("volume_type")
    @validation.required_services(consts.Service.NOVA, consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["cinder", "nova"]})
    def create_snapshot_and_attach_volume(self, volume_type=False,
                                          size=None, **kwargs):

        """Create volume, snapshot and attach/detach volume.

        This scenario is based on the standalone qaStressTest.py
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
        if size is None:
            size = {"min": 1, "max": 5}
        selected_type = None
        volume_types = [None]

        if volume_type:
            volume_types_list = self.clients("cinder").volume_types.list()
            for s in volume_types_list:
                volume_types.append(s.name)
            selected_type = random.choice(volume_types)

        volume = self._create_volume(size, volume_type=selected_type)
        snapshot = self._create_snapshot(volume.id, False, **kwargs)

        server = self.get_random_server()

        attachment = self._attach_volume(server, volume)
        self._detach_volume(server, volume, attachment)

        self._delete_snapshot(snapshot)
        self._delete_volume(volume)

    @validation.required_services(consts.Service.NOVA, consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["cinder", "nova"]})
    @logging.log_deprecated_args(
        "Use 'create_snapshot_kwargs' for additional snapshot kwargs.",
        "0.4.1", ["kwargs"], once=True)
    def create_nested_snapshots_and_attach_volume(self,
                                                  size=None,
                                                  nested_level=1,
                                                  create_volume_kwargs=None,
                                                  create_snapshot_kwargs=None,
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
        :param nested_level: amount of nested levels
        :param create_volume_kwargs: optional args to create a volume
        :param create_snapshot_kwargs: optional args to create a snapshot
        :param kwargs: Optional parameters used during volume
                       snapshot creation.
        """
        if size is None:
            size = {"min": 1, "max": 5}

        # NOTE: Volume size cannot be smaller than the snapshot size, so
        #       volume with specified size should be created to avoid
        #       size mismatching between volume and snapshot due random
        #       size in _create_volume method.
        size = random.randint(size["min"], size["max"])

        create_volume_kwargs = create_volume_kwargs or {}
        create_snapshot_kwargs = create_snapshot_kwargs or kwargs or {}
        server = self.get_random_server()

        source_vol = self._create_volume(size, **create_volume_kwargs)
        snapshot = self._create_snapshot(source_vol.id, False,
                                         **create_snapshot_kwargs)
        attachment = self._attach_volume(server, source_vol)

        nes_objs = [(server, source_vol, snapshot, attachment)]
        for i in range(nested_level - 1):
            volume = self._create_volume(size, snapshot_id=snapshot.id)
            snapshot = self._create_snapshot(volume.id, False,
                                             **create_snapshot_kwargs)
            server = self.get_random_server()
            attachment = self._attach_volume(server, volume)

            nes_objs.append((server, volume, snapshot, attachment))

        nes_objs.reverse()
        for server, volume, snapshot, attachment in nes_objs:
            self._detach_volume(server, volume, attachment)
            self._delete_snapshot(snapshot)
            self._delete_volume(volume)

    @validation.required_services(consts.Service.CINDER)
    @validation.required_contexts("volumes")
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["cinder"]})
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

    @types.convert(image={"type": "glance_image"})
    @validation.required_services(consts.Service.CINDER, consts.Service.GLANCE)
    @validation.required_openstack(users=True)
    @validation.required_parameters("size")
    @scenario.configure(context={"cleanup": ["cinder", "glance"]})
    def create_and_upload_volume_to_image(self, size, image=None, force=False,
                                          container_format="bare",
                                          disk_format="raw",
                                          do_delete=True,
                                          **kwargs):
        """Create and upload a volume to image.

        :param size: volume size (integers, in GB), or
                     dictionary, must contain two values:
                         min - minimum size volumes will be created as;
                         max - maximum size volumes will be created as.
        :param image: image to be used to create volume.
        :param force: when set to True volume that is attached to an instance
                      could be uploaded to image
        :param container_format: image container format
        :param disk_format: disk format for image
        :param do_delete: deletes image and volume after uploading if True
        :param kwargs: optional args to create a volume
        """
        if image:
            kwargs["imageRef"] = image
        volume = self._create_volume(size, **kwargs)
        image = self._upload_volume_to_image(volume, force, container_format,
                                             disk_format)

        if do_delete:
            self._delete_volume(volume)
            self._delete_image(image)

    @validation.required_cinder_services("cinder-backup")
    @validation.required_services(consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["cinder"]})
    def create_volume_backup(self, size, do_delete=True,
                             create_volume_kwargs=None,
                             create_backup_kwargs=None):
        """Create a volume backup.

        :param size: volume size in GB
        :param do_delete: if True, a volume and a volume backup will
                          be deleted after creation.
        :param create_volume_kwargs: optional args to create a volume
        :param create_backup_kwargs: optional args to create a volume backup
        """
        create_volume_kwargs = create_volume_kwargs or {}
        create_backup_kwargs = create_backup_kwargs or {}

        volume = self._create_volume(size, **create_volume_kwargs)
        backup = self._create_backup(volume.id, **create_backup_kwargs)

        if do_delete:
            self._delete_volume(volume)
            self._delete_backup(backup)

    @validation.required_cinder_services("cinder-backup")
    @validation.required_services(consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["cinder"]})
    def create_and_restore_volume_backup(self, size, do_delete=True,
                                         create_volume_kwargs=None,
                                         create_backup_kwargs=None):
        """Restore volume backup.

        :param size: volume size in GB
        :param do_delete: if True, the volume and the volume backup will
                          be deleted after creation.
        :param create_volume_kwargs: optional args to create a volume
        :param create_backup_kwargs: optional args to create a volume backup
        """
        create_volume_kwargs = create_volume_kwargs or {}
        create_backup_kwargs = create_backup_kwargs or {}

        volume = self._create_volume(size, **create_volume_kwargs)
        backup = self._create_backup(volume.id, **create_backup_kwargs)
        self._restore_backup(backup.id)

        if do_delete:
            self._delete_volume(volume)
            self._delete_backup(backup)

    @validation.required_cinder_services("cinder-backup")
    @validation.required_services(consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["cinder"]})
    def create_and_list_volume_backups(self, size, detailed=True,
                                       do_delete=True,
                                       create_volume_kwargs=None,
                                       create_backup_kwargs=None):
        """Create and then list a volume backup.

        :param size: volume size in GB
        :param detailed: True if detailed information about backup
                         should be listed
        :param do_delete: if True, a volume backup will be deleted
        :param create_volume_kwargs: optional args to create a volume
        :param create_backup_kwargs: optional args to create a volume backup
        """
        create_volume_kwargs = create_volume_kwargs or {}
        create_backup_kwargs = create_backup_kwargs or {}

        volume = self._create_volume(size, **create_volume_kwargs)
        backup = self._create_backup(volume.id, **create_backup_kwargs)
        self._list_backups(detailed)

        if do_delete:
            self._delete_volume(volume)
            self._delete_backup(backup)

    @types.convert(image={"type": "glance_image"})
    @validation.image_exists("image", nullable=True)
    @validation.required_services(consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["cinder"]})
    def create_volume_and_clone(self, size, image=None, nested_level=1,
                                **kwargs):
        """Create a volume, then clone it to another volume.

          This creates a volume, then clone it to anothor volume,
          and then clone the new volume to next volume...
           1. create source volume (from image)
           2. clone source volume to volume1
           3. clone volume1 to volume2
           4. clone volume2 to volume3
           5. ...

        :param size: volume size (integer, in GB) or
                     dictionary, must contain two values:
                         min - minimum size volumes will be created as;
                         max - maximum size volumes will be created as.
        :param image: image to be used to create initial volume
        :param nested_level: amount of nested levels
        :param kwargs: optional args to create volumes
        """
        if image:
            kwargs["imageRef"] = image

        source_vol = self._create_volume(size, **kwargs)

        kwargs.pop("imageRef", None)
        for i in range(nested_level):
            with atomic.ActionTimer(self, "cinder.clone_volume"):
                source_vol = self._create_volume(source_vol.size,
                                                 source_volid=source_vol.id,
                                                 atomic_action=False, **kwargs)

    @validation.required_services(consts.Service.CINDER)
    @validation.required_contexts("volumes")
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["cinder"]})
    def create_volume_from_snapshot(self, do_delete=True,
                                    create_snapshot_kwargs=None,
                                    **kwargs):
        """Create a volume-snapshot, then create a volume from this snapshot.

        :param do_delete: if True, a snapshot and a volume will
                          be deleted after creation.
        :param create_snapshot_kwargs: optional args to create a snapshot
        :param kwargs: optional args to create a volume
        """
        create_snapshot_kwargs = create_snapshot_kwargs or {}
        src_volume = random.choice(self.context["tenant"]["volumes"])

        snapshot = self._create_snapshot(src_volume["id"],
                                         **create_snapshot_kwargs)
        volume = self._create_volume(src_volume["size"],
                                     snapshot_id=snapshot.id,
                                     **kwargs)

        if do_delete:
            self._delete_snapshot(snapshot)
            self._delete_volume(volume)
