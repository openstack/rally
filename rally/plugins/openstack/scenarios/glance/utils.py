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

from oslo_config import cfg

from rally.plugins.openstack import scenario
from rally.plugins.openstack.wrappers import glance as glance_wrapper
from rally.task import atomic
from rally.task import utils

GLANCE_BENCHMARK_OPTS = [
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
                      **kwargs):
        """Create a new image.

        :param container_format: container format of image. Acceptable
                                 formats: ami, ari, aki, bare, and ovf
        :param image_location: image file location
        :param disk_format: disk format of image. Acceptable formats:
                            ami, ari, aki, vhd, vmdk, raw, qcow2, vdi, and iso
        :param kwargs: optional parameters to create image

        :returns: image object
        """
        if not kwargs.get("name"):
            kwargs["name"] = self.generate_random_name()
        client = glance_wrapper.wrap(self._clients.glance, self)
        return client.create_image(container_format, image_location,
                                   disk_format, **kwargs)

    @atomic.action_timer("glance.delete_image")
    def _delete_image(self, image):
        """Deletes given image.

        Returns when the image is actually deleted.

        :param image: Image object
        """
        self.clients("glance").images.delete(image.id)
        wrapper = glance_wrapper.wrap(self._clients.glance, self)
        utils.wait_for_status(
            image, ["deleted", "pending_delete"],
            check_deletion=True,
            update_resource=wrapper.get_image,
            timeout=CONF.benchmark.glance_image_delete_timeout,
            check_interval=CONF.benchmark.glance_image_delete_poll_interval)
