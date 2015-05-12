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

from rally.plugins.openstack.context import servers
from tests.unit import fakes
from tests.unit import test

CTX = "rally.plugins.openstack.context"
SCN = "rally.benchmark.scenarios"
TYP = "rally.benchmark.types"


class ServerGeneratorTestCase(test.TestCase):

    def _gen_tenants(self, count):
        tenants = {}
        for id in range(count):
            tenants[str(id)] = dict(name=str(id))
        return tenants

    def test_init(self):
        tenants_count = 2
        servers_per_tenant = 5
        context = {}
        context["task"] = mock.MagicMock()
        context["config"] = {
            "servers": {
                "servers_per_tenant": servers_per_tenant,
            }
        }
        context["tenants"] = self._gen_tenants(tenants_count)

        inst = servers.ServerGenerator(context)
        self.assertEqual(context["config"]["servers"], inst.config)

    @mock.patch("%s.nova.utils.NovaScenario._boot_servers" % SCN,
                return_value=[
                    fakes.FakeServer(id="uuid"),
                    fakes.FakeServer(id="uuid"),
                    fakes.FakeServer(id="uuid"),
                    fakes.FakeServer(id="uuid"),
                    fakes.FakeServer(id="uuid")
                ])
    @mock.patch("%s.ImageResourceType.transform" % TYP,
                return_value=mock.MagicMock())
    @mock.patch("%s.FlavorResourceType.transform" % TYP,
                return_value=mock.MagicMock())
    @mock.patch("%s.servers.osclients" % CTX, return_value=fakes.FakeClients())
    def test_setup(self, mock_osclients, mock_flavor_transform,
                   mock_image_transform, mock_boot_servers):

        tenants_count = 2
        users_per_tenant = 5
        servers_per_tenant = 5

        tenants = self._gen_tenants(tenants_count)
        users = []
        for id in tenants.keys():
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": id,
                              "endpoint": "endpoint"})

        real_context = {
            "config": {
                "users": {
                    "tenants": 2,
                    "users_per_tenant": 5,
                    "concurrent": 10,
                },
                "servers": {
                    "servers_per_tenant": 5,
                    "image": {
                        "name": "cirros-0.3.2-x86_64-uec",
                    },
                    "flavor": {
                        "name": "m1.tiny",
                    },
                },
            },
            "admin": {
                "endpoint": mock.MagicMock()
            },
            "task": mock.MagicMock(),
            "users": users,
            "tenants": tenants
        }

        new_context = copy.deepcopy(real_context)
        for id in new_context["tenants"]:
            new_context["tenants"][id].setdefault("servers", list())
            for i in range(servers_per_tenant):
                new_context["tenants"][id]["servers"].append("uuid")

        servers_ctx = servers.ServerGenerator(real_context)
        servers_ctx.setup()
        self.assertEqual(new_context, real_context)

    @mock.patch("%s.servers.osclients" % CTX)
    @mock.patch("%s.servers.resource_manager.cleanup" % CTX)
    def test_cleanup(self, mock_cleanup, mock_osclients):

        tenants_count = 2
        users_per_tenant = 5
        servers_per_tenant = 5

        tenants = self._gen_tenants(tenants_count)
        users = []
        for id in tenants.keys():
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": id,
                              "endpoint": "endpoint"})
            tenants[id].setdefault("servers", list())
            for j in range(servers_per_tenant):
                tenants[id]["servers"].append("uuid")

        context = {
            "config": {
                "users": {
                    "tenants": 2,
                    "users_per_tenant": 5,
                    "concurrent": 10,
                },
                "servers": {
                    "servers_per_tenant": 5,
                    "image": {
                        "name": "cirros-0.3.2-x86_64-uec",
                    },
                    "flavor": {
                        "name": "m1.tiny",
                    },
                },
            },
            "admin": {
                "endpoint": mock.MagicMock()
            },
            "task": mock.MagicMock(),
            "users": users,
            "tenants": tenants
        }

        servers_ctx = servers.ServerGenerator(context)
        servers_ctx.cleanup()

        mock_cleanup.assert_called_once_with(names=["nova.servers"],
                                             users=context["users"])
