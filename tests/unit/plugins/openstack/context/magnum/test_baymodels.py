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

from rally.plugins.openstack.context.magnum import baymodels
from tests.unit import fakes
from tests.unit import test


BASE_CTX = "rally.task.context"
CTX = "rally.plugins.openstack.context"
BASE_SCN = "rally.task.scenarios"
SCN = "rally.plugins.openstack.scenarios"


class BaymodelsGeneratorTestCase(test.ScenarioTestCase):

    """Generate tenants."""
    def _gen_tenants(self, count):
        tenants = {}
        for id_ in range(count):
            tenants[str(id_)] = dict(name=str(id_))
        return tenants

    @mock.patch("%s.magnum.utils.MagnumScenario._create_baymodel" % SCN,
                return_value=fakes.FakeBaymodel(id="uuid"))
    @mock.patch("%s.nova.utils.NovaScenario._create_keypair" % SCN,
                return_value="key1")
    def test_setup(self, mock_nova_scenario__create_keypair,
                   mock_magnum_scenario__create_baymodel):
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
                "baymodels": {
                    "dns_nameserver": "8.8.8.8",
                    "external_network_id": "public",
                    "flavor_id": "m1.small",
                    "docker_volume_size": 5,
                    "coe": "kubernetes",
                    "image_id": "fedora-atomic-latest",
                    "network_driver": "flannel"
                }
            },
            "users": users,
            "tenants": tenants
        })

        baymodel_ctx = baymodels.BaymodelGenerator(self.context)
        baymodel_ctx.setup()

        baymodel_ctx_config = self.context["config"]["baymodels"]
        image_id = baymodel_ctx_config.get("image_id")
        external_network_id = baymodel_ctx_config.get(
            "external_network_id")
        dns_nameserver = baymodel_ctx_config.get("dns_nameserver")
        flavor_id = baymodel_ctx_config.get("flavor_id")
        docker_volume_size = baymodel_ctx_config.get("docker_volume_size")
        network_driver = baymodel_ctx_config.get("network_driver")
        coe = baymodel_ctx_config.get("coe")
        mock_calls = [mock.call(image_id=image_id, keypair_id="key1",
                                external_network_id=external_network_id,
                                dns_nameserver=dns_nameserver,
                                flavor_id=flavor_id,
                                docker_volume_size=docker_volume_size,
                                network_driver=network_driver, coe=coe)
                      for i in range(tenants_count)]
        mock_magnum_scenario__create_baymodel.assert_has_calls(mock_calls)

        # check that stack ids have been saved in context
        for ten_id in self.context["tenants"].keys():
            self.assertIsNotNone(self.context["tenants"][ten_id]["baymodel"])

    @mock.patch("%s.magnum.baymodels.resource_manager.cleanup" % CTX)
    def test_cleanup(self, mock_cleanup):
        self.context.update({
            "users": mock.MagicMock()
        })
        baymodel_ctx = baymodels.BaymodelGenerator(self.context)
        baymodel_ctx.cleanup()
        mock_cleanup.assert_called_once_with(names=["magnum.baymodels",
                                                    "nova.keypairs"],
                                             users=self.context["users"])
