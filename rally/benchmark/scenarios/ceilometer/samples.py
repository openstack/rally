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
from rally.benchmark.scenarios.ceilometer import utils as ceilometerutils
from rally.benchmark import validation
from rally import consts


class CeilometerSamples(ceilometerutils.CeilometerScenario):
    """Benchmark scenarios for Ceilometer Samples API."""

    @validation.required_services(consts.Service.CEILOMETER)
    @validation.required_openstack(users=True)
    @base.scenario()
    def list_samples(self):
        """Fetch all samples.

        This scenario fetches list of all samples.
        """
        self._list_samples()
