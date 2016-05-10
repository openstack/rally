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
import time

from oslo_config import cfg

from rally import exceptions
from rally.plugins.openstack import scenario
from rally.plugins.openstack.wrappers import cinder as cinder_wrapper
from rally.plugins.openstack.wrappers import glance as glance_wrapper
from rally.task import atomic
from rally.task import utils as bench_utils

CINDER_BENCHMARK_OPTS = [
    cfg.FloatOpt("cinder_volume_create_prepoll_delay",
                 default=2.0,
                 help="Time to sleep after creating a resource before"
                      " polling for it status"),
    cfg.FloatOpt("cinder_volume_create_timeout",
                 default=600.0,
                 help="Time to wait for cinder volume to be created."),
    cfg.FloatOpt("cinder_volume_create_poll_interval",
                 default=2.0,
                 help="Interval between checks when waiting for volume"
                      " creation."),
    cfg.FloatOpt("cinder_volume_delete_timeout",
                 default=600.0,
                 help="Time to wait for cinder volume to be deleted."),
    cfg.FloatOpt("cinder_volume_delete_poll_interval",
                 default=2.0,
                 help="Interval between checks when waiting for volume"
                      " deletion.")
]

CONF = cfg.CONF
benchmark_group = cfg.OptGroup(name="benchmark", title="benchmark options")
CONF.register_opts(CINDER_BENCHMARK_OPTS, group=benchmark_group)


class CinderScenario(scenario.OpenStackScenario):
    """Base class for Cinder scenarios with basic atomic actions."""

    @atomic.action_timer("cinder.list_volumes")
    def _list_volumes(self, detailed=True):
        """Returns user volumes list."""

        return self.clients("cinder").volumes.list(detailed)

    @atomic.action_timer("cinder.list_snapshots")
    def _list_snapshots(self, detailed=True):
        """Returns user snapshots list."""

        return self.clients("cinder").volume_snapshots.list(detailed)

    def _set_metadata(self, volume, sets=10, set_size=3):
        """Set volume metadata.

        :param volume: The volume to set metadata on
        :param sets: how many operations to perform
        :param set_size: number of metadata keys to set in each operation
        :returns: A list of keys that were set
        """
        key = "cinder.set_%s_metadatas_%s_times" % (set_size, sets)
        with atomic.ActionTimer(self, key):
            keys = []
            for i in range(sets):
                metadata = {}
                for j in range(set_size):
                    key = self.generate_random_name()
                    keys.append(key)
                    metadata[key] = self.generate_random_name()

                self.clients("cinder").volumes.set_metadata(volume, metadata)
            return keys

    def _delete_metadata(self, volume, keys, deletes=10, delete_size=3):
        """Delete volume metadata keys.

        Note that ``len(keys)`` must be greater than or equal to
        ``deletes * delete_size``.

        :param volume: The volume to delete metadata from
        :param deletes: how many operations to perform
        :param delete_size: number of metadata keys to delete in each operation
        :param keys: a list of keys to choose deletion candidates from
        """
        if len(keys) < deletes * delete_size:
            raise exceptions.InvalidArgumentsException(
                "Not enough metadata keys to delete: "
                "%(num_keys)s keys, but asked to delete %(num_deletes)s" %
                {"num_keys": len(keys),
                 "num_deletes": deletes * delete_size})
        # make a shallow copy of the list of keys so that, when we pop
        # from it later, we don't modify the original list.
        keys = list(keys)
        random.shuffle(keys)
        action_name = "cinder.delete_%s_metadatas_%s_times" % (delete_size,
                                                               deletes)
        with atomic.ActionTimer(self, action_name):
            for i in range(deletes):
                to_del = keys[i * delete_size:(i + 1) * delete_size]
                self.clients("cinder").volumes.delete_metadata(volume, to_del)

    @atomic.optional_action_timer("cinder.create_volume")
    def _create_volume(self, size, **kwargs):
        """Create one volume.

        Returns when the volume is actually created and is in the "Available"
        state.

        :param size: int be size of volume in GB, or
                     dictionary, must contain two values:
                         min - minimum size volumes will be created as;
                         max - maximum size volumes will be created as.
        :param atomic_action: True if this is an atomic action. added
                              and handled by the
                              optional_action_timer() decorator
        :param kwargs: Other optional parameters to initialize the volume
        :returns: Created volume object
        """
        if isinstance(size, dict):
            size = random.randint(size["min"], size["max"])

        client = cinder_wrapper.wrap(self._clients.cinder, self)
        volume = client.create_volume(size, **kwargs)

        # NOTE(msdubov): It is reasonable to wait 5 secs before starting to
        #                check whether the volume is ready => less API calls.
        time.sleep(CONF.benchmark.cinder_volume_create_prepoll_delay)
        volume = bench_utils.wait_for(
            volume,
            ready_statuses=["available"],
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.cinder_volume_create_timeout,
            check_interval=CONF.benchmark.cinder_volume_create_poll_interval
        )
        return volume

    @atomic.action_timer("cinder.update_volume")
    def _update_volume(self, volume, **update_volume_args):
        """Update name and description for this volume

        This atomic function updates volume information. The volume
        display name is always changed, and additional update
        arguments may also be specified.

        :param volume: volume object
        :param update_volume_args: dict, contains values to be updated.
        """
        client = cinder_wrapper.wrap(self._clients.cinder, self)
        client.update_volume(volume, **update_volume_args)

    @atomic.action_timer("cinder.delete_volume")
    def _delete_volume(self, volume):
        """Delete the given volume.

        Returns when the volume is actually deleted.

        :param volume: volume object
        """
        volume.delete()
        bench_utils.wait_for_status(
            volume,
            ready_statuses=["deleted"],
            check_deletion=True,
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.cinder_volume_delete_timeout,
            check_interval=CONF.benchmark.cinder_volume_delete_poll_interval
        )

    @atomic.action_timer("cinder.extend_volume")
    def _extend_volume(self, volume, new_size):
        """Extend the given volume.

        Returns when the volume is actually extended.

        :param volume: volume object
        :param new_size: new volume size in GB, or
                         dictionary, must contain two values:
                             min - minimum size volumes will be created as;
                             max - maximum size volumes will be created as.
                        Notice: should be bigger volume size
        """

        if isinstance(new_size, dict):
            new_size = random.randint(new_size["min"], new_size["max"])

        volume.extend(volume, new_size)
        volume = bench_utils.wait_for(
            volume,
            ready_statuses=["available"],
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.cinder_volume_create_timeout,
            check_interval=CONF.benchmark.cinder_volume_create_poll_interval
        )

    @atomic.action_timer("cinder.upload_volume_to_image")
    def _upload_volume_to_image(self, volume, force=False,
                                container_format="bare", disk_format="raw"):
        """Upload the given volume to image.

        Returns created image.

        :param volume: volume object
        :param force: flag to indicate whether to snapshot a volume even if
                      it's attached to an instance
        :param container_format: container format of image. Acceptable
                                 formats: ami, ari, aki, bare, and ovf
        :param disk_format: disk format of image. Acceptable formats:
                            ami, ari, aki, vhd, vmdk, raw, qcow2, vdi and iso
        :returns: Returns created image object
        """
        resp, img = volume.upload_to_image(force, self.generate_random_name(),
                                           container_format, disk_format)
        # NOTE (e0ne): upload_to_image changes volume status to uploading so
        # we need to wait until it will be available.
        volume = bench_utils.wait_for(
            volume,
            ready_statuses=["available"],
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.cinder_volume_create_timeout,
            check_interval=CONF.benchmark.cinder_volume_create_poll_interval
        )
        image_id = img["os-volume_upload_image"]["image_id"]
        image = self.clients("glance").images.get(image_id)
        wrapper = glance_wrapper.wrap(self._clients.glance, self)
        image = bench_utils.wait_for(
            image,
            ready_statuses=["active"],
            update_resource=wrapper.get_image,
            timeout=CONF.benchmark.glance_image_create_timeout,
            check_interval=CONF.benchmark.glance_image_create_poll_interval
        )

        return image

    @atomic.action_timer("cinder.create_snapshot")
    def _create_snapshot(self, volume_id, force=False, **kwargs):
        """Create one snapshot.

        Returns when the snapshot is actually created and is in the "Available"
        state.

        :param volume_id: volume uuid for creating snapshot
        :param force: flag to indicate whether to snapshot a volume even if
                      it's attached to an instance
        :param kwargs: Other optional parameters to initialize the volume
        :returns: Created snapshot object
        """
        kwargs["force"] = force

        client = cinder_wrapper.wrap(self._clients.cinder, self)
        snapshot = client.create_snapshot(volume_id, **kwargs)

        time.sleep(CONF.benchmark.cinder_volume_create_prepoll_delay)
        snapshot = bench_utils.wait_for(
            snapshot,
            ready_statuses=["available"],
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.cinder_volume_create_timeout,
            check_interval=CONF.benchmark.cinder_volume_create_poll_interval
        )
        return snapshot

    @atomic.action_timer("cinder.delete_snapshot")
    def _delete_snapshot(self, snapshot):
        """Delete the given snapshot.

        Returns when the snapshot is actually deleted.

        :param snapshot: snapshot object
        """
        snapshot.delete()
        bench_utils.wait_for_status(
            snapshot,
            ready_statuses=["deleted"],
            check_deletion=True,
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.cinder_volume_delete_timeout,
            check_interval=CONF.benchmark.cinder_volume_delete_poll_interval
        )

    @atomic.action_timer("cinder.create_backup")
    def _create_backup(self, volume_id, **kwargs):
        """Create a volume backup of the given volume.

        :param volume_id: The ID of the volume to backup.
        :param kwargs: Other optional parameters
        """
        backup = self.clients("cinder").backups.create(volume_id, **kwargs)
        return bench_utils.wait_for(
            backup,
            ready_statuses=["available"],
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.cinder_volume_create_timeout,
            check_interval=CONF.benchmark.cinder_volume_create_poll_interval
        )

    @atomic.action_timer("cinder.delete_backup")
    def _delete_backup(self, backup):
        """Delete the given backup.

        Returns when the backup is actually deleted.

        :param backup: backup instance
        """
        backup.delete()
        bench_utils.wait_for_status(
            backup,
            ready_statuses=["deleted"],
            check_deletion=True,
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.cinder_volume_delete_timeout,
            check_interval=CONF.benchmark.cinder_volume_delete_poll_interval
        )

    @atomic.action_timer("cinder.restore_backup")
    def _restore_backup(self, backup_id, volume_id=None):
        """Restore the given backup.

        :param backup_id: The ID of the backup to restore.
        :param volume_id: The ID of the volume to restore the backup to.
        """
        restore = self.clients("cinder").restores.restore(backup_id, volume_id)
        restored_volume = self.clients("cinder").volumes.get(restore.volume_id)
        return bench_utils.wait_for(
            restored_volume,
            ready_statuses=["available"],
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.cinder_volume_create_timeout,
            check_interval=CONF.benchmark.cinder_volume_create_poll_interval
        )

    @atomic.action_timer("cinder.list_backups")
    def _list_backups(self, detailed=True):
        """Return user volume backups list.

        :param detailed: True if detailed information about backup
                         should be listed
        """
        return self.clients("cinder").backups.list(detailed)

    def get_random_server(self):
        server_id = random.choice(self.context["tenant"]["servers"])
        return self.clients("nova").servers.get(server_id)
