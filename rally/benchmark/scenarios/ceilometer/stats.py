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

from rally.benchmark.scenarios import base
from rally.benchmark.scenarios.ceilometer import utils
from rally.benchmark import validation
from rally import consts


class CeilometerStats(utils.CeilometerScenario):

    @validation.required_services(consts.Service.CEILOMETER)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["ceilometer"]})
    def create_meter_and_get_stats(self, **kwargs):
        """Test creating a meter and fetching its statistics.

        Meter is first created and then statistics is fetched for the same
        using GET /v2/meters/(meter_name)/statistics.
        :param name_length: length of generated (random) part of meter name
        :param kwargs: contains optional arguments to create a meter
        """
        meter = self._create_meter(**kwargs)
        self._get_stats(meter.counter_name)
