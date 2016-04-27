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

from rally import exceptions
from rally.plugins.openstack.context import fuel
from tests.unit import test

BASE = "rally.plugins.openstack.context.fuel"


class FuelEnvGeneratorTestCase(test.TestCase):

    @mock.patch(BASE + ".FuelEnvGenerator._create_envs",
                return_value=["env1"])
    @mock.patch(BASE + ".fuel_utils.FuelScenario")
    def test_setup(self, mock_fuel_scenario, mock__create_envs):
        context = {}
        context["config"] = {"fuel_environments": {"environments": 1}}
        context["task"] = {"uuid": "some_uuid"}
        context["admin"] = {"credential": "some_credential"}

        env_ctx = fuel.FuelEnvGenerator(context)
        env_ctx.setup()
        self.assertIn("fuel", env_ctx.context)
        self.assertIn("environments", env_ctx.context["fuel"])

        mock__create_envs.assert_called_once_with()
        mock_fuel_scenario.assert_called_once_with(context)

    @mock.patch(BASE + ".FuelEnvGenerator._create_envs",
                return_value=["env1"])
    @mock.patch(BASE + ".fuel_utils.FuelScenario")
    def test_setup_error(self, mock_fuel_scenario, mock__create_envs):
        context = {}
        context["config"] = {"fuel_environments": {"environments": 5}}
        context["task"] = {"uuid": "some_uuid"}
        context["admin"] = {"credential": "some_credential"}

        env_ctx = fuel.FuelEnvGenerator(context)
        self.assertRaises(exceptions.ContextSetupFailure, env_ctx.setup)

    def test__create_envs(self):
        config = {"environments": 4,
                  "release_id": 42,
                  "network_provider": "provider",
                  "deployment_mode": "mode",
                  "net_segment_type": "type",
                  "resource_management_workers": 3}

        context = {"task": {},
                   "config": {"fuel_environments": config}}

        env_ctx = fuel.FuelEnvGenerator(context)
        env_ctx.fscenario = mock.Mock()
        env_ctx.fscenario.return_value._create_environment.return_value = "id"
        self.assertEqual(config["environments"], len(env_ctx._create_envs()))
        enves = config.pop("environments")
        config.pop("resource_management_workers")
        exp_calls = [mock.call(**config) for i in range(enves)]
        env_ctx.fscenario._create_environment.has_calls(exp_calls,
                                                        any_order=True)

    def test__delete_envs(self):
        config = {"release_id": 42,
                  "network_provider": "provider",
                  "deployment_mode": "mode",
                  "net_segment_type": "type",
                  "resource_management_workers": 3}

        context = {"task": {},
                   "config": {"fuel_environments": config},
                   "fuel": {"environments": ["id", "id", "id"]}}

        env_ctx = fuel.FuelEnvGenerator(context)
        env_ctx.fscenario = mock.Mock()

        env_ctx._delete_envs()
        self.assertEqual({}, context["fuel"])

    def test_cleanup(self):
        config = {"release_id": 42,
                  "network_provider": "provider",
                  "deployment_mode": "mode",
                  "net_segment_type": "type",
                  "resource_management_workers": 3}

        context = {"task": {"uuid": "some_id"},
                   "config": {"fuel_environments": config},
                   "fuel": {"environments": ["id", "id", "id"]}}

        env_ctx = fuel.FuelEnvGenerator(context)
        env_ctx._delete_envs = mock.Mock()
        env_ctx.cleanup()
        env_ctx._delete_envs.assert_called_once_with()
