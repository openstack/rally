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


import copy

import mock

from rally.plugins.openstack.context.ceilometer import samples
from tests.unit import test

CTX = "rally.plugins.openstack.context.ceilometer"


class CeilometerSampleGeneratorTestCase(test.TestCase):

    def _gen_tenants(self, count):
        tenants = {}
        for id_ in range(count):
            tenants[str(id_)] = {"name": str(id_)}
        return tenants

    def _gen_context(self, tenants_count, users_per_tenant,
                     resources_per_tenant, samples_per_resource):
        tenants = self._gen_tenants(tenants_count)
        users = []
        for id_ in tenants.keys():
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": id_,
                              "endpoint": mock.MagicMock()})
        context = test.get_test_context()
        context.update({
            "config": {
                "users": {
                    "tenants": tenants_count,
                    "users_per_tenant": users_per_tenant,
                    "concurrent": 10,
                },
                "ceilometer": {
                    "counter_name": "fake-counter-name",
                    "counter_type": "fake-counter-type",
                    "counter_unit": "fake-counter-unit",
                    "counter_volume": 100,
                    "resources_per_tenant": resources_per_tenant,
                    "samples_per_resource": samples_per_resource
                }
            },
            "admin": {
                "endpoint": mock.MagicMock()
            },
            "users": users,
            "tenants": tenants
        })
        return tenants, context

    def test_init(self):
        context = {}
        context["task"] = mock.MagicMock()
        context["config"] = {
            "ceilometer": {
                "counter_name": "cpu_util",
                "counter_type": "gauge",
                "counter_unit": "instance",
                "counter_volume": 1.0,
                "resources_per_tenant": 5,
                "samples_per_resource": 5
            }
        }

        inst = samples.CeilometerSampleGenerator(context)
        self.assertEqual(inst.config, context["config"]["ceilometer"])

    @mock.patch("%s.samples.ceilo_utils.CeilometerScenario._create_sample"
                % CTX)
    def test_setup(self, mock_ceilometer_scenario__create_sample):
        tenants_count = 2
        users_per_tenant = 2
        resources_per_tenant = 2
        samples_per_resource = 2

        tenants, real_context = self._gen_context(
            tenants_count, users_per_tenant,
            resources_per_tenant, samples_per_resource)

        sample = {
            "counter_name": "fake-counter-name",
            "counter_type": "fake-counter-type",
            "counter_unit": "fake-counter-unit",
            "counter_volume": 100,
            "resource_id": "fake-resource-id"
        }

        new_context = copy.deepcopy(real_context)
        for id_ in tenants.keys():
            new_context["tenants"][id_].setdefault("samples", [])
            new_context["tenants"][id_].setdefault("resources", [])
            for i in range(resources_per_tenant):
                for j in range(samples_per_resource):
                    new_context["tenants"][id_]["samples"].append(sample)
                new_context["tenants"][id_]["resources"].append(
                    sample["resource_id"])

        mock_ceilometer_scenario__create_sample.return_value = [
            mock.MagicMock(to_dict=lambda: sample, **sample)]

        ceilometer_ctx = samples.CeilometerSampleGenerator(real_context)
        ceilometer_ctx.setup()
        self.assertEqual(new_context, ceilometer_ctx.context)

    def test_cleanup(self):
        tenants, context = self._gen_context(2, 5, 3, 3)
        ceilometer_ctx = samples.CeilometerSampleGenerator(context)
        ceilometer_ctx.cleanup()
