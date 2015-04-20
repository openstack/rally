# Copyright 2014: Mirantis Inc.
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

import os
import time

from oslo_config import cfg

from rally.plugins.openstack import scenario
from rally.task import atomic
from rally.task import utils


GLANCE_BENCHMARK_OPTS = [
    cfg.FloatOpt("glance_image_create_prepoll_delay",
                 default=2.0,
                 help="Time to sleep after creating a resource before "
                      "polling for it status"),
    cfg.FloatOpt("glance_image_create_timeout",
                 default=120.0,
                 help="Time to wait for glance image to be created."),
    cfg.FloatOpt("glance_image_create_poll_interval",
                 default=1.0,
                 help="Interval between checks when waiting for image "
                      "creation."),
    cfg.FloatOpt("glance_image_delete_timeout",
                 default=120.0,
                 help="Time to wait for glance image to be deleted."),
    cfg.FloatOpt("glance_image_delete_poll_interval",
                 default=1.0,
                 help="Interval between checks when waiting for image "
                      "deletion.")
]


CONF = cfg.CONF
benchmark_group = cfg.OptGroup(name="benchmark", title="benchmark options")
CONF.register_opts(GLANCE_BENCHMARK_OPTS, group=benchmark_group)


class GlanceScenario(scenario.OpenStackScenario):
    """Base class for Glance scenarios with basic atomic actions."""

    @atomic.action_timer("glance.list_images")
    def _list_images(self):
        """Returns user images list."""
        return list(self.clients("glance").images.list())

    @atomic.action_timer("glance.create_image")
    def _create_image(self, container_format, image_location, disk_format,
                      name=None, prefix=None, length=None, **kwargs):
        """Create a new image.

        :param container_format: container format of image. Acceptable
                                 formats: ami, ari, aki, bare, and ovf
        :param image_location: image file location
        :param disk_format: disk format of image. Acceptable formats:
                            ami, ari, aki, vhd, vmdk, raw, qcow2, vdi, and iso
        :param name: string used to name the image
        :param prefix: prefix of generated image name if name not specified
        ignore if name specified
        :param length: length of autometic generated part in image name
        ignore if name specified
        :param kwargs: optional parameters to create image

        :returns: image object
        """
        name = name or self._generate_random_name(prefix, length)
        kw = {
            "name": name,
            "container_format": container_format,
            "disk_format": disk_format,
        }

        kw.update(kwargs)
        image_location = os.path.expanduser(image_location)

        try:
            if os.path.isfile(image_location):
                kw["data"] = open(image_location)
            else:
                kw["copy_from"] = image_location

            image = self.clients("glance").images.create(**kw)

            time.sleep(CONF.benchmark.glance_image_create_prepoll_delay)

            image = utils.wait_for(
                image,
                is_ready=utils.resource_is("active"),
                update_resource=utils.get_from_manager(),
                timeout=CONF.benchmark.glance_image_create_timeout,
                check_interval=CONF.benchmark.
                glance_image_create_poll_interval)

        finally:
            if "data" in kw:
                kw["data"].close()

        return image

    @atomic.action_timer("glance.delete_image")
    def _delete_image(self, image):
        """Deletes given image.

        Returns when the image is actually deleted.

        :param image: Image object
        """
        image.delete()
        utils.wait_for_delete(
            image,
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.glance_image_delete_timeout,
            check_interval=CONF.benchmark.glance_image_delete_poll_interval)
