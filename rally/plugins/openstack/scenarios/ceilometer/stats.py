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

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.ceilometer import utils
from rally.task import validation


class CeilometerStats(utils.CeilometerScenario):
    """Benchmark scenarios for Ceilometer Stats API."""

    @validation.required_services(consts.Service.CEILOMETER)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["ceilometer"]})
    def create_meter_and_get_stats(self, **kwargs):
        """Create a meter and fetch its statistics.

        Meter is first created and then statistics is fetched for the same
        using GET /v2/meters/(meter_name)/statistics.

        :param kwargs: contains optional arguments to create a meter
        """
        meter = self._create_meter(**kwargs)
        self._get_stats(meter.counter_name)
