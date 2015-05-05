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

from rally.benchmark.scenarios import base
from rally.benchmark import utils as bench_utils


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


class CinderScenario(base.Scenario):
    """Base class for Cinder scenarios with basic atomic actions."""

    RESOURCE_NAME_PREFIX = "rally_volume_"

    @base.atomic_action_timer("cinder.list_volumes")
    def _list_volumes(self, detailed=True):
        """Returns user volumes list."""

        return self.clients("cinder").volumes.list(detailed)

    @base.atomic_action_timer("cinder.list_snapshots")
    def _list_snapshots(self, detailed=True):
        """Returns user snapshots list."""

        return self.clients("cinder").volume_snapshots.list(detailed)

    @base.atomic_action_timer("cinder.create_volume")
    def _create_volume(self, size, **kwargs):
        """Create one volume.

        Returns when the volume is actually created and is in the "Available"
        state.

        :param size: int be size of volume in GB, or
                     dictionary, must contain two values:
                         min - minimum size volumes will be created as;
                         max - maximum size volumes will be created as.
        :param kwargs: Other optional parameters to initialize the volume
        :returns: Created volume object
        """
        kwargs["display_name"] = kwargs.get("display_name",
                                            self._generate_random_name())

        if isinstance(size, dict):
            size = random.randint(size["min"], size["max"])

        volume = self.clients("cinder").volumes.create(size, **kwargs)
        # NOTE(msdubov): It is reasonable to wait 5 secs before starting to
        #                check whether the volume is ready => less API calls.
        time.sleep(CONF.benchmark.cinder_volume_create_prepoll_delay)
        volume = bench_utils.wait_for(
            volume,
            is_ready=bench_utils.resource_is("available"),
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.cinder_volume_create_timeout,
            check_interval=CONF.benchmark.cinder_volume_create_poll_interval
        )
        return volume

    @base.atomic_action_timer("cinder.delete_volume")
    def _delete_volume(self, volume):
        """Delete the given volume.

        Returns when the volume is actually deleted.

        :param volume: volume object
        """
        volume.delete()
        bench_utils.wait_for_delete(
            volume,
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.cinder_volume_delete_timeout,
            check_interval=CONF.benchmark.cinder_volume_delete_poll_interval
        )

    @base.atomic_action_timer("cinder.extend_volume")
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
            is_ready=bench_utils.resource_is("available"),
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.cinder_volume_create_timeout,
            check_interval=CONF.benchmark.cinder_volume_create_poll_interval
        )

    @base.atomic_action_timer("cinder.upload_volume_to_image")
    def _upload_volume_to_image(self, volume, force=False,
                                container_format="bare", disk_format="raw"):
        """Upload the given volume to image.

        Returns created image.

        :param volume: volume object
        :param force: flag to indicate whether to snapshot a volume even if
                      it's attached to an instance
        :param container_format: container format of image. Acceptable
                                 formats: ami, ari, aki, bare, and ovf
        :param: disk_format: disk format of image. Acceptable formats:
                             ami, ari, aki, vhd, vmdk, raw, qcow2, vdi
                             and iso
        :returns: Returns created image object
        """
        resp, img = volume.upload_to_image(force, self._generate_random_name(),
                                           container_format, disk_format)
        # NOTE (e0ne): upload_to_image changes volume status to uploading so
        # we need to wait until it will be available.
        volume = bench_utils.wait_for(
            volume,
            is_ready=bench_utils.resource_is("available"),
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.cinder_volume_create_timeout,
            check_interval=CONF.benchmark.cinder_volume_create_poll_interval
        )
        image_id = img["os-volume_upload_image"]["image_id"]
        image = self.clients("glance").images.get(image_id)
        image = bench_utils.wait_for(
            image,
            is_ready=bench_utils.resource_is("active"),
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.glance_image_create_prepoll_delay,
            check_interval=CONF.benchmark.glance_image_create_poll_interval
        )

        return image

    @base.atomic_action_timer("cinder.create_snapshot")
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
        kwargs["display_name"] = kwargs.get("display_name",
                                            self._generate_random_name())
        kwargs["force"] = force
        snapshot = self.clients("cinder").volume_snapshots.create(volume_id,
                                                                  **kwargs)
        time.sleep(CONF.benchmark.cinder_volume_create_prepoll_delay)
        snapshot = bench_utils.wait_for(
            snapshot,
            is_ready=bench_utils.resource_is("available"),
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.cinder_volume_create_timeout,
            check_interval=CONF.benchmark.cinder_volume_create_poll_interval
        )
        return snapshot

    @base.atomic_action_timer("cinder.delete_snapshot")
    def _delete_snapshot(self, snapshot):
        """Delete the given snapshot.

        Returns when the snapshot is actually deleted.

        :param snapshot: snapshot object
        """
        snapshot.delete()
        bench_utils.wait_for_delete(
            snapshot,
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.cinder_volume_delete_timeout,
            check_interval=CONF.benchmark.cinder_volume_delete_poll_interval
        )

    def get_random_server(self):
        server_id = random.choice(self.context["tenant"]["servers"])
        return self.clients("nova").servers.get(server_id)
