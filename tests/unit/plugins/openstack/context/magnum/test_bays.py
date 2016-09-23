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

from rally.plugins.openstack.context.magnum import bays
from tests.unit import test

CTX = "rally.plugins.openstack.context.magnum"
SCN = "rally.plugins.openstack.scenarios"


class BaysGeneratorTestCase(test.ScenarioTestCase):

    def _gen_tenants(self, count):
        tenants = {}
        for id_ in range(count):
            tenants[str(id_)] = {"name": str(id_)}
        return tenants

    def _gen_tenants_with_baymodel(self, count):
        tenants = {}
        for id_ in range(count):
            tenants[str(id_)] = {"name": str(id_)}
            tenants[str(id_)]["baymodel"] = "rally_baymodel_uuid"
        return tenants

    @mock.patch("%s.magnum.utils.MagnumScenario._create_bay" % SCN,
                return_value=mock.Mock())
    def test_setup_using_existing_baymodel(self,
                                           mock_magnum_scenario__create_bay):
        tenants_count = 2
        users_per_tenant = 5

        tenants = self._gen_tenants(tenants_count)
        users = []
        for ten_id in tenants:
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": ten_id,
                              "credential": mock.MagicMock()})

        self.context.update({
            "config": {
                "users": {
                    "tenants": tenants_count,
                    "users_per_tenant": users_per_tenant,
                    "concurrent": 10,
                },
                "bays": {
                    "baymodel_uuid": "123456789",
                    "node_count": 2
                }
            },
            "users": users,
            "tenants": tenants
        })

        mock_bay = mock_magnum_scenario__create_bay.return_value
        new_context = copy.deepcopy(self.context)
        for id_ in new_context["tenants"]:
            new_context["tenants"][id_]["bay"] = mock_bay.uuid

        bay_ctx = bays.BayGenerator(self.context)
        bay_ctx.setup()

        self.assertEqual(new_context, self.context)
        bay_ctx_config = self.context["config"]["bays"]
        node_count = bay_ctx_config.get("node_count")
        baymodel_uuid = bay_ctx_config.get("baymodel_uuid")
        mock_calls = [mock.call(baymodel=baymodel_uuid, node_count=node_count)
                      for i in range(tenants_count)]
        mock_magnum_scenario__create_bay.assert_has_calls(mock_calls)

    @mock.patch("%s.magnum.utils.MagnumScenario._create_bay" % SCN,
                return_value=mock.Mock())
    def test_setup(self, mock_magnum_scenario__create_bay):
        tenants_count = 2
        users_per_tenant = 5

        tenants = self._gen_tenants_with_baymodel(tenants_count)
        users = []
        for ten_id in tenants:
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": ten_id,
                              "credential": mock.MagicMock()})

        self.context.update({
            "config": {
                "users": {
                    "tenants": tenants_count,
                    "users_per_tenant": users_per_tenant,
                    "concurrent": 10,
                },
                "baymodels": {
                    "dns_nameserver": "8.8.8.8",
                    "external_network_id": "public",
                    "flavor_id": "m1.small",
                    "docker_volume_size": 5,
                    "coe": "kubernetes",
                    "image_id": "fedora-atomic-latest",
                    "network_driver": "flannel"
                },
                "bays": {
                    "node_count": 2
                }
            },
            "users": users,
            "tenants": tenants
        })

        mock_bay = mock_magnum_scenario__create_bay.return_value
        new_context = copy.deepcopy(self.context)
        for id_ in new_context["tenants"]:
            new_context["tenants"][id_]["bay"] = mock_bay.uuid

        bay_ctx = bays.BayGenerator(self.context)
        bay_ctx.setup()

        self.assertEqual(new_context, self.context)
        bay_ctx_config = self.context["config"]["bays"]
        node_count = bay_ctx_config.get("node_count")
        mock_calls = [mock.call(baymodel="rally_baymodel_uuid",
                                node_count=node_count)
                      for i in range(tenants_count)]
        mock_magnum_scenario__create_bay.assert_has_calls(mock_calls)

    @mock.patch("%s.baymodels.resource_manager.cleanup" % CTX)
    def test_cleanup(self, mock_cleanup):
        self.context.update({
            "users": mock.MagicMock()
        })
        bays_ctx = bays.BayGenerator(self.context)
        bays_ctx.cleanup()
        mock_cleanup.assert_called_once_with(
            names=["magnum.bays"],
            users=self.context["users"])
