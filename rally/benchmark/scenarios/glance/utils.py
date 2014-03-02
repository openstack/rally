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

import random
import string
import time

from rally.benchmark.scenarios import base
from rally.benchmark.scenarios import utils as scenario_utils
from rally.benchmark import utils as bench_utils
from rally import utils


class GlanceScenario(base.Scenario):

    @scenario_utils.atomic_action_timer('glance.create_image')
    def _create_image(self, image_name, container_format,
                      image_url, disk_format, **kwargs):
        """Create a new image.

        :param image_name: String used to name the image
        :param container_format: Container format of image.
        Acceptable formats: ami, ari, aki, bare, and ovf.
        :param image_url: URL for download image
        :param disk_format: Disk format of image. Acceptable formats:
        ami, ari, aki, vhd, vmdk, raw, qcow2, vdi, and iso.
        :param **kwargs:  optional parameters to create image

        returns: object of image
        """
        image = self.clients("glance").images.create(
                                        name=image_name,
                                        copy_from=image_url,
                                        container_format=container_format,
                                        disk_format=disk_format,
                                        **kwargs)
        time.sleep(5)
        image = utils.wait_for(image,
                               is_ready=bench_utils.resource_is("active"),
                               update_resource=bench_utils.get_from_manager(),
                               timeout=120, check_interval=3)
        return image

    @scenario_utils.atomic_action_timer('glance.delete_image')
    def _delete_image(self, image):
        """Deletes the given image.

        Returns when the image is actually deleted.

        :param image: Image object
        """
        image.delete()
        utils.wait_for_delete(image,
                              update_resource=bench_utils.get_from_manager(),
                              timeout=120, check_interval=3)

    def _generate_random_name(self, length):
        name = ''.join(random.choice(string.lowercase) for i in range(length))
        return 'test-rally-image' + name
