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
import string
import time

from rally.benchmark import base
from rally.benchmark.scenarios import utils as scenario_utils
from rally.benchmark import utils as bench_utils
from rally import utils

# TODO(boris-42): Bind name to the uuid of benchmark.
TEMP_TEMPLATE = "rally_c_"


def is_temporary(resource):
    return resource.name.startswith(TEMP_TEMPLATE)


def generate_volume_name(length=10):
    """Generate random name for volume."""
    rand_part = ''.join(random.choice(string.lowercase) for i in range(length))
    return TEMP_TEMPLATE + rand_part


class CinderScenario(base.Scenario):

    @scenario_utils.atomic_action_timer('cinder.create_volume')
    def _create_volume(self, size, **kwargs):
        """create one volume.

        Returns when the volume is actually created and is in the "Available"
        state.

        :param size: int be size of volume in GB
        :param **kwargs: Other optional parameters to initialize the volume

        :returns: Created volume object
        """
        volumename = kwargs.get('display_name', generate_volume_name(10))
        kwargs['display_name'] = volumename
        volume = self.clients("cinder").volumes.create(size, **kwargs)
        # NOTE(msdubov): It is reasonable to wait 5 secs before starting to
        #                check whether the volume is ready => less API calls.
        time.sleep(3)
        volume = utils.wait_for(volume,
                                is_ready=bench_utils.resource_is("available"),
                                update_resource=bench_utils.get_from_manager(),
                                timeout=600, check_interval=3)
        return volume

    @scenario_utils.atomic_action_timer('cinder.delete_volume')
    def _delete_volume(self, volume):
        """Delete the given volume.

        Returns when the volume is actually deleted.

        :param volume: volume object
        """
        volume.delete()
        utils.wait_for_delete(volume,
                              update_resource=bench_utils.get_from_manager(),
                              timeout=600, check_interval=2)
