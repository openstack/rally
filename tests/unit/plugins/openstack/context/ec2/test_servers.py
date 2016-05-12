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

from rally.plugins.openstack.context.ec2 import servers
from tests.unit import fakes
from tests.unit import test

CTX = "rally.plugins.openstack.context.ec2"
SCN = "rally.plugins.openstack.scenarios"
TYP = "rally.plugins.openstack.types"


class EC2ServerGeneratorTestCase(test.TestCase):

    def _gen_tenants_and_users(self, tenants_count, users_per_tenant):
        tenants = {}
        for id in range(tenants_count):
            tenants[str(id)] = dict(name=str(id))

        users = []
        for tenant_id in tenants.keys():
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": tenant_id,
                              "credential": "credential"})
        return tenants, users

    def _get_context(self, users, tenants):
        return {
            "config": {
                "users": {
                    "tenants": 2,
                    "users_per_tenant": 5,
                    "concurrent": 10},
                "ec2_servers": {
                    "servers_per_tenant": 5,
                    "image": {"name": "foo_image"},
                    "flavor": {"name": "foo_flavor"}
                }
            },
            "admin": {"credential": mock.MagicMock()},
            "task": mock.MagicMock(),
            "users": users,
            "tenants": tenants
        }

    @mock.patch("%s.ec2.utils.EC2Scenario._boot_servers" % SCN,
                return_value=[fakes.FakeServer(id=str(i)) for i in range(5)])
    @mock.patch("%s.EC2Image.transform" % TYP, return_value=mock.MagicMock())
    @mock.patch("%s.servers.osclients" % CTX, return_value=fakes.FakeClients())
    def test_setup(self, mock_osclients,
                   mock_ec2_image_transform,
                   mock_ec2_scenario__boot_servers):

        tenants_count = 2
        users_per_tenant = 5
        servers_per_tenant = 5

        tenants, users = self._gen_tenants_and_users(tenants_count,
                                                     users_per_tenant)

        real_context = self._get_context(users, tenants)

        new_context = copy.deepcopy(real_context)
        for tenant_id in new_context["tenants"]:
            new_context["tenants"][tenant_id].setdefault("ec2_servers", [])
            for i in range(servers_per_tenant):
                new_context["tenants"][tenant_id]["ec2_servers"].append(str(i))

        servers_ctx = servers.EC2ServerGenerator(real_context)
        servers_ctx.setup()
        self.assertEqual(new_context, servers_ctx.context)

    @mock.patch("%s.servers.osclients" % CTX)
    @mock.patch("%s.servers.resource_manager.cleanup" % CTX)
    def test_cleanup(self, mock_cleanup, mock_osclients):

        tenants_count = 2
        users_per_tenant = 5
        servers_per_tenant = 5

        tenants, users = self._gen_tenants_and_users(tenants_count,
                                                     users_per_tenant)
        for tenant_id in tenants.keys():
            tenants[tenant_id].setdefault("ec2_servers", [])
            for i in range(servers_per_tenant):
                tenants[tenant_id]["ec2_servers"].append(str(i))

        context = self._get_context(users, tenants)

        servers_ctx = servers.EC2ServerGenerator(context)
        servers_ctx.cleanup()

        mock_cleanup.assert_called_once_with(names=["ec2.servers"],
                                             users=context["users"])
