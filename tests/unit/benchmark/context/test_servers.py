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

from rally.benchmark.context import servers
from tests.unit import fakes
from tests.unit import test

CTX = "rally.benchmark.context"
SCN = "rally.benchmark.scenarios"
TYP = "rally.benchmark.types"


class ServerGeneratorTestCase(test.TestCase):
    def test_init(self):
        context = {}
        context["task"] = mock.MagicMock()
        context["config"] = {
            "servers": {
                "servers_per_tenant": 5,
            }
        }

        new_context = copy.deepcopy(context)
        new_context["servers"] = []
        servers.ServerGenerator(context)
        self.assertEqual(new_context, context)

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
        ctx_servers = [
            {'server_ids':
                ['uuid', 'uuid', 'uuid', 'uuid', 'uuid'],
             'endpoint': 'endpoint',
             'tenant_id': i}
            for i in range(2)]
        user_key = [{'id': i, 'tenant_id': j, 'endpoint': 'endpoint'}
                    for j in range(2)
                    for i in range(5)]

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
            "users": user_key,
        }

        new_context = copy.deepcopy(real_context)
        new_context["servers"] = ctx_servers

        servers_ctx = servers.ServerGenerator(real_context)
        servers_ctx.setup()
        self.assertEqual(new_context, real_context)

    @mock.patch("%s.servers.osclients" % CTX)
    @mock.patch("%s.servers.resource_manager.cleanup" % CTX)
    def test_cleanup(self, mock_cleanup, mock_osclients):
        ctx_servers = [
            {'server_ids':
                ['uuid', 'uuid', 'uuid', 'uuid', 'uuid'],
             'endpoint': mock.MagicMock(),
             'tenant_id': i}
            for i in range(2)]
        user_key = [{'id': i, 'tenant_id': j, 'endpoint': 'endpoint'}
                    for j in range(2)
                    for i in range(5)]

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
            "users": user_key,
            "servers": ctx_servers,
        }

        servers_ctx = servers.ServerGenerator(context)
        servers_ctx.cleanup()

        mock_cleanup.assert_called_once_with(names=["nova.servers"],
                                             users=context["users"])