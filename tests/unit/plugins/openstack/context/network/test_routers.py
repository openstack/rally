# Copyright 2017: Orange
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

import copy
import mock

from rally.plugins.openstack.context.network import routers as router_context
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils

from tests.unit import test

SCN = "rally.plugins.openstack.scenarios"
CTX = "rally.plugins.openstack.context.network.routers"


class RouterTestCase(test.ScenarioTestCase):

    def _gen_tenants(self, count):
        tenants = {}
        for id_ in range(count):
            tenants[str(id_)] = {"name": str(id_)}
        return tenants

    def test__init__default(self):
        self.context.update({
            "config": {
                "router": {
                    "routers_per_tenant": 1,
                }
            }
        })
        context = router_context.Router(self.context)
        self.assertEqual(context.config["routers_per_tenant"], 1)

    @mock.patch("%s.neutron.utils.NeutronScenario._create_router" % SCN,
                return_value={"id": "uuid"})
    def test_setup(self, mock_neutron_scenario__create_router):
        tenants_count = 2
        users_per_tenant = 3
        routers_per_tenant = 2

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
                    "users_per_tenant": 3,
                    "concurrent": 2,
                },
                "router": {
                    "routers_per_tenant": routers_per_tenant,
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
            new_context["tenants"][id_].setdefault("routers", [])
            for i in range(routers_per_tenant):
                new_context["tenants"][id_]["routers"].append({"id": "uuid"})

        routers_ctx = router_context.Router(self.context)
        routers_ctx.setup()
        self.assertEqual(new_context, self.context)

    @mock.patch("%s.resource_manager.cleanup" % CTX)
    def test_cleanup(self, mock_cleanup):
        self.context.update({"users": mock.MagicMock()})
        routers_ctx = router_context.Router(self.context)
        routers_ctx.cleanup()
        mock_cleanup.assert_called_once_with(
            names=["neutron.router"],
            users=self.context["users"],
            superclass=neutron_utils.NeutronScenario,
            task_id=self.context["owner_id"])
