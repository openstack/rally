# Copyright 2015: Workday, Inc.
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

from rally.common.plugin import plugin
from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.nova import utils
from rally.task import validation


"""Scenarios for Nova images."""


@plugin.deprecated("The image proxy-interface was removed from Nova-API. Use "
                   "Glance related scenarios instead "
                   "(i.e GlanceImages.list_images.", rally_version="0.10.0")
@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="NovaImages.list_images", platform="openstack")
class ListImages(utils.NovaScenario):

    def run(self, detailed=True, **kwargs):
        """[DEPRECATED] List all images.

        Measure the "nova image-list" command performance.

        :param detailed: True if the image listing
                         should contain detailed information
        :param kwargs: Optional additional arguments for image listing
        """
        self._list_images(detailed, **kwargs)
