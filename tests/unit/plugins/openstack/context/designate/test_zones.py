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

from rally.plugins.openstack.context.designate import zones
from tests.unit import test

CTX = "rally.plugins.openstack.context"
SCN = "rally.plugins.openstack.scenarios"


class ZoneGeneratorTestCase(test.ScenarioTestCase):

    def _gen_tenants(self, count):
        tenants = {}
        for id_ in range(count):
            tenants[str(id_)] = {"name": str(id_)}
        return tenants

    def test_init(self):
        self.context.update({
            "config": {
                "zones": {
                    "zones_per_tenant": 5,
                }
            }
        })

        inst = zones.ZoneGenerator(self.context)
        self.assertEqual(inst.config, self.context["config"]["zones"])

    @mock.patch("%s.designate.utils.DesignateScenario._create_zone" % SCN,
                return_value={"id": "uuid"})
    def test_setup(self, mock_designate_scenario__create_zone):
        tenants_count = 2
        users_per_tenant = 5
        zones_per_tenant = 5

        tenants = self._gen_tenants(tenants_count)
        users = []
        for id_ in tenants.keys():
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": id_,
                              "credential": mock.MagicMock()})

        self.context.update({
            "config": {
                "users": {
                    "tenants": 2,
                    "users_per_tenant": 5,
                    "concurrent": 10,
                },
                "zones": {
                    "zones_per_tenant": zones_per_tenant,
                }
            },
            "admin": {
                "credential": mock.MagicMock()
            },
            "users": users,
            "tenants": tenants
        })

        new_context = copy.deepcopy(self.context)
        for id_ in tenants.keys():
            new_context["tenants"][id_].setdefault("zones", [])
            for i in range(zones_per_tenant):
                new_context["tenants"][id_]["zones"].append({"id": "uuid"})

        zones_ctx = zones.ZoneGenerator(self.context)
        zones_ctx.setup()
        self.assertEqual(new_context, self.context)

    @mock.patch("%s.designate.zones.resource_manager.cleanup" % CTX)
    def test_cleanup(self, mock_cleanup):

        tenants_count = 2
        users_per_tenant = 5
        zones_per_tenant = 5

        tenants = self._gen_tenants(tenants_count)
        users = []
        for id_ in tenants.keys():
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": id_,
                              "endpoint": "endpoint"})
            tenants[id_].setdefault("zones", [])
            for j in range(zones_per_tenant):
                tenants[id_]["zones"].append({"id": "uuid"})

        self.context.update({
            "config": {
                "users": {
                    "tenants": 2,
                    "users_per_tenant": 5,
                    "concurrent": 10,
                },
                "zones": {
                    "zones_per_tenant": 5,
                }
            },
            "admin": {
                "endpoint": mock.MagicMock()
            },
            "users": users,
            "tenants": tenants
        })

        zones_ctx = zones.ZoneGenerator(self.context)
        zones_ctx.cleanup()

        mock_cleanup.assert_called_once_with(names=["designate.zones"],
                                             users=self.context["users"])
