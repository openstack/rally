# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import ddt

from rally.plugins.openstack.scenarios.monasca import utils
from tests.unit import test


@ddt.ddt
class MonascaScenarioTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(MonascaScenarioTestCase, self).setUp()
        self.scenario = utils.MonascaScenario(self.context)
        self.kwargs = {
            "dimensions": {
                "region": "fake_region",
                "hostname": "fake_host_name",
                "service": "fake_service",
                "url": "fake_url"
            }
        }

    def test_list_metrics(self):
        return_metric_value = self.scenario._list_metrics()
        self.assertEqual(return_metric_value,
                         self.clients("monasca").metrics.list.return_value)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "monasca.list_metrics")

    @ddt.data(
        {"name": ""},
        {"name": "fake_metric"},
    )
    @ddt.unpack
    def test_create_metrics(self, name=None):
        self.name = name
        self.scenario._create_metrics(name=self.name, kwargs=self.kwargs)
        self.assertEqual(1, self.clients("monasca").metrics.create.call_count)
