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

from rally.benchmark.scenarios.cinder import utils


class CinderVolumes(utils.CinderScenario):

    @classmethod
    def create_and_delete_volume(cls, size,
                                 min_sleep=0, max_sleep=0, **kwargs):
        """Tests creating and then deleting a volume."""

        volume = cls._create_volume(size, **kwargs)
        cls.sleep_between(min_sleep, max_sleep)
        cls._delete_volume(volume)

    @classmethod
    def create_volume(cls, size, **kwargs):
        cls._create_volume(size, **kwargs)
