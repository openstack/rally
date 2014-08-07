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

from rally.benchmark.scenarios import base as scenario_base
from rally.benchmark.scenarios.cinder import utils
from rally.benchmark import validation
from rally import consts


class CinderVolumes(utils.CinderScenario):

    @scenario_base.scenario(context={"cleanup": ["cinder"]})
    @validation.required_services(consts.Service.CINDER)
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

    @scenario_base.scenario(context={"cleanup": ["cinder"]})
    @validation.required_services(consts.Service.CINDER)
    def create_and_delete_volume(self, size, min_sleep=0, max_sleep=0,
                                 **kwargs):
        """Tests creating and then deleting a volume.

        Good for testing a maximal bandwidth of cloud.
        """

        volume = self._create_volume(size, **kwargs)
        self.sleep_between(min_sleep, max_sleep)
        self._delete_volume(volume)

    @scenario_base.scenario(context={"cleanup": ["cinder"]})
    @validation.required_services(consts.Service.CINDER)
    def create_volume(self, size, **kwargs):
        """Test creating volumes perfromance.

        Good test to check how influence amount of active volumes on
        performance of creating new.
        """
        self._create_volume(size, **kwargs)
