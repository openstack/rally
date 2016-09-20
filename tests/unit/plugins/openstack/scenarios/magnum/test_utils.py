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

import mock

from rally.plugins.openstack.scenarios.magnum import utils
from tests.unit import test


class MagnumScenarioTestCase(test.ScenarioTestCase):
    def setUp(self):
        super(MagnumScenarioTestCase, self).setUp()
        self.baymodel = mock.Mock()
        self.scenario = utils.MagnumScenario(self.context)

    def test_list_baymodels(self):
        scenario = utils.MagnumScenario(self.context)
        fake_baymodel_list = [self.baymodel]

        self.clients("magnum").baymodels.list.return_value = fake_baymodel_list
        return_baymodels_list = scenario._list_baymodels()
        self.assertEqual(fake_baymodel_list, return_baymodels_list)

        self.clients("magnum").baymodels.list.assert_called_once_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "magnum.list_baymodels")

    def test_create_baymodel(self):
        self.scenario.generate_random_name = mock.Mock(
            return_value="generated_name")
        fake_baymodel = self.baymodel
        self.clients("magnum").baymodels.create.return_value = fake_baymodel

        return_baymodel = self.scenario._create_baymodel(
            image="test_image",
            keypair="test_key",
            external_network="public",
            dns_nameserver="8.8.8.8",
            flavor="m1.large",
            docker_volume_size=50,
            network_driver="docker",
            coe="swarm")

        self.assertEqual(fake_baymodel, return_baymodel)
        args, kwargs = self.clients("magnum").baymodels.create.call_args
        self.assertEqual("generated_name", kwargs["name"])

        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "magnum.create_baymodel")
