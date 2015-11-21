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

import mock
import six

from rally.plugins.openstack.context.monasca import metrics
from rally.plugins.openstack.scenarios.monasca import utils as monasca_utils
from tests.unit import test

CTX = "rally.plugins.openstack.context.monasca"


class MonascaMetricGeneratorTestCase(test.TestCase):

    def _gen_tenants(self, count):
        tenants = {}
        for id in six.moves.range(count):
            tenants[str(id)] = {"name": str(id)}
        return tenants

    def _gen_context(self, tenants_count, users_per_tenant,
                     metrics_per_tenant):
        tenants = self._gen_tenants(tenants_count)
        users = []
        for id in tenants.keys():
            for i in six.moves.range(users_per_tenant):
                users.append({"id": i, "tenant_id": id,
                              "endpoint": mock.MagicMock()})
        context = test.get_test_context()
        context.update({
            "config": {
                "users": {
                    "tenants": tenants_count,
                    "users_per_tenant": users_per_tenant,
                    "concurrent": 10,
                },
                "monasca_metrics": {
                    "name": "fake-metric-name",
                    "dimensions": {
                        "region": "fake-region",
                        "service": "fake-identity",
                        "hostname": "fake-hostname",
                        "url": "fake-url"
                    },
                    "metrics_per_tenant": metrics_per_tenant,
                },
                "roles": [
                    "monasca-user"
                ]
            },
            "admin": {
                "endpoint": mock.MagicMock()
            },
            "users": users,
            "tenants": tenants
        })
        return tenants, context

    @mock.patch("%s.metrics.rutils.interruptable_sleep" % CTX)
    @mock.patch("%s.metrics.monasca_utils.MonascaScenario" % CTX)
    def test_setup(self, mock_monasca_scenario, mock_interruptable_sleep):
        tenants_count = 2
        users_per_tenant = 4
        metrics_per_tenant = 5

        tenants, real_context = self._gen_context(
            tenants_count, users_per_tenant, metrics_per_tenant)

        monasca_ctx = metrics.MonascaMetricGenerator(real_context)
        monasca_ctx.setup()

        self.assertEqual(tenants_count, mock_monasca_scenario.call_count,
                         "Scenario should be constructed same times as "
                         "number of tenants")
        self.assertEqual(metrics_per_tenant * tenants_count,
                         mock_monasca_scenario.return_value._create_metrics.
                         call_count,
                         "Total number of metrics created should be tenant"
                         "counts times metrics per tenant")
        first_call = mock.call(0.001)
        second_call = mock.call(monasca_utils.CONF.benchmark.
                                monasca_metric_create_prepoll_delay,
                                atomic_delay=1)
        self.assertEqual([first_call] * metrics_per_tenant * tenants_count +
                         [second_call],
                         mock_interruptable_sleep.call_args_list,
                         "Method interruptable_sleep should be called "
                         "tenant counts times metrics plus one")
