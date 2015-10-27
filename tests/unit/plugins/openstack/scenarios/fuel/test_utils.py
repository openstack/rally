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

from rally.plugins.openstack.scenarios.fuel import utils
from tests.unit import test


UTILS = "rally.plugins.openstack.scenarios.fuel.utils."


class ModuleTestCase(test.TestCase):

    @mock.patch(UTILS + "six")
    @mock.patch(UTILS + "FuelClient", return_value="fuel_client")
    def test_fuel(self, mock_fuel_client, mock_six):
        mock_six.moves.urllib.parse.urlparse().hostname = "foo_host"
        client = utils.Fuel(
            mock.Mock(username="foo_user", password="foo_pass"),
            {}, {}).create_client()
        mock_fuel_client.assert_called_once_with(
            version="v1", server_address="foo_host", server_port=8000,
            username="foo_user", password="foo_pass")
        self.assertEqual("fuel_client", client)


class FuelEnvTestCase(test.TestCase):

    def test___init__(self):
        env = utils.FuelEnvManager("some_client")
        self.assertEqual("some_client", env.client)

    def test_get(self):
        client = mock.Mock()
        fenv = utils.FuelEnvManager(client)
        result = fenv.get("some_id")
        client.get_by_id.assert_called_once_with("some_id")
        self.assertEqual(result, client.get_by_id("some_id"))
        client.get_by_id.side_effect = BaseException
        self.assertIsNone(fenv.get("some_id"))

    def test_list(self):
        client = mock.Mock()
        envs = [
            {"name": "one"},
            {"name": "two"},
            {"name": "three"}]
        client.get_all.return_value = envs
        fenv = utils.FuelEnvManager(client)
        self.assertEqual(envs, fenv.list())

    def test_list_exception(self):
        client = mock.Mock()
        client.get_all = mock.Mock(side_effect=SystemExit)
        fenv = utils.FuelEnvManager(client)
        self.assertRaises(RuntimeError, fenv.list)

    def test_create(self):
        client = mock.Mock()
        client.create.return_value = "env"
        fenv = utils.FuelEnvManager(client)
        kwargs = {"release_id": 42, "network_provider": "testprov",
                  "deployment_mode": "some_mode", "net_segment_type": "bar"}
        self.assertEqual("env", fenv.create("some_env", **kwargs))
        client.create.assert_called_once_with("some_env", 42, "testprov",
                                              "some_mode", "bar")
        client.create.side_effect = SystemExit
        self.assertRaises(RuntimeError, fenv.create, "some_env", **kwargs)

    def test_create_env_not_returned(self):
        client = mock.Mock()
        client.create.return_value = None
        kwargs = {"release_id": 42, "network_provider": "testprov",
                  "deployment_mode": "some_mode", "net_segment_type": "bar"}
        fenv = utils.FuelEnvManager(client)
        self.assertRaises(RuntimeError, fenv.create, "some_env", **kwargs)

    @mock.patch(UTILS + "scenario.OpenStackScenario")
    def test_delete(self, mock_open_stack_scenario):
        mock_open_stack_scenario.RESOURCE_NAME_PREFIX = ""
        envs = [{"id": "some_one", "name": "one"}]
        client = mock.Mock()
        client.get_all.return_value = envs
        client.delete_by_id.side_effect = SystemExit

        fenv = utils.FuelEnvManager(client)
        self.assertRaises(RuntimeError, fenv.delete, "some_one", retries=2)
        self.assertEqual(3, len(client.delete_by_id.mock_calls))

    @mock.patch(UTILS + "scenario.OpenStackScenario")
    def test_delete_error(self, mock_open_stack_scenario):
        mock_open_stack_scenario.RESOURCE_NAME_PREFIX = ""
        envs = [{"id": "some_one", "name": "one"}]
        client = mock.Mock()
        client.delete_by_id.side_effect = SystemExit
        client.get_all.return_value = envs

        fenv = utils.FuelEnvManager(client)
        self.assertRaises(RuntimeError, fenv.delete, "some_one", retries=1)
        self.assertEqual(2, len(client.delete_by_id.mock_calls))


class FuelClientTestCase(test.TestCase):

    @mock.patch(UTILS + "FuelEnvManager")
    @mock.patch(UTILS + "os")
    def test___init__(self, mock_os, mock_fuel_env_manager):
        mock_os.environ = {}
        mock_fuelclient = mock.Mock(get_client=lambda *args, **kw: [args, kw])
        with mock.patch.dict("sys.modules", {"fuelclient": mock_fuelclient}):
            client = utils.FuelClient(version="foo_version",
                                      server_address="foo_address",
                                      server_port=1234,
                                      username="foo_user",
                                      password="foo_pass")
            expected_environ = {"KEYSTONE_PASS": "foo_pass",
                                "KEYSTONE_USER": "foo_user",
                                "LISTEN_PORT": "1234",
                                "SERVER_ADDRESS": "foo_address"}
            self.assertEqual(expected_environ, mock_os.environ)
            self.assertEqual(mock_fuel_env_manager.return_value,
                             client.environment)
            self.assertEqual([("node",), {"version": "foo_version"}],
                             client.node)
            self.assertEqual([("task",), {"version": "foo_version"}],
                             client.task)
            mock_fuel_env_manager.assert_called_once_with(
                [("environment",),
                 {"version": "foo_version"}])


class FuelScenarioTestCase(test.ScenarioTestCase):

    def test__list_environments(self):
        scenario = utils.FuelScenario(self.context)
        self.assertEqual(
            scenario._list_environments(),
            self.admin_clients("fuel").environment.list.return_value)
        self.admin_clients("fuel").environment.list.assert_called_once_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "fuel.list_environments")

    def test__create_environment(self):
        self.admin_clients("fuel").environment.create.return_value = {"id": 42}

        fuel_scenario = utils.FuelScenario()
        fuel_scenario.admin_clients = self.admin_clients

        fuel_scenario.generate_random_name = mock.Mock()
        result = fuel_scenario._create_environment()
        self.assertEqual(
            self.admin_clients("fuel").environment.create.return_value["id"],
            result)
        tmp_mck = self.admin_clients("fuel").environment.create
        tmp_mck.assert_called_once_with(
            fuel_scenario.generate_random_name.return_value, 1, "neutron",
            "ha_compact", "vlan")

    def test__delete_environment(self):
        fuel_scenario = utils.FuelScenario()

        fuel_scenario.admin_clients = self.admin_clients
        fuel_scenario._delete_environment(42, 33)
        tmp_mock = fuel_scenario.admin_clients("fuel")
        tmp_mock.environment.delete.assert_called_once_with(42, 33)

    def test__add_nodes(self):
        fscen = utils.FuelScenario()
        fscen.admin_clients = mock.Mock()
        fscen._add_node("1", ["42"], node_roles=["some_role"])
        tmp_mock = fscen.admin_clients.return_value.environment.client
        tmp_mock.add_nodes.assert_called_once_with("1", ["42"], ["some_role"])

    def test__add_nodes_error(self):
        fscen = utils.FuelScenario()
        fscen.admin_clients = mock.Mock()
        tmp_mock = fscen.admin_clients.return_value.environment.client
        tmp_mock.add_nodes.side_effect = BaseException
        self.assertRaises(RuntimeError, fscen._add_node, "1", "42",
                          node_roles="some_role")

    @mock.patch(UTILS + "FuelClient")
    def test__remove_nodes(self, mock_fuel_client):
        mock_tmp = mock_fuel_client.fuelclient_module.objects
        mock_env = mock_tmp.environment.Environment
        mock_env.return_value = mock.Mock()
        fscen = utils.FuelScenario()
        fscen._remove_node("1", "2")
        mock_env.assert_called_once_with("1")
        mock_env.return_value.unassign.assert_called_once_with(["2"])

    @mock.patch(UTILS + "FuelClient")
    def test__remove_nodes_error(self, mock_fuel_client):
        mock_tmp = mock_fuel_client.fuelclient_module.objects
        mock_env = mock_tmp.environment.Environment
        mock_env.return_value = mock.Mock()
        mock_env.return_value.unassign.side_effect = BaseException
        fscen = utils.FuelScenario()
        self.assertRaises(RuntimeError, fscen._remove_node, "1", "2")

    def test__list_node_ids(self):
        fscen = utils.FuelScenario()
        fscen.admin_clients = mock.Mock()
        fscen.admin_clients.return_value.node.get_all.return_value = [
            {"id": "id1"}, {"id": "id2"}]
        res = fscen._list_node_ids("env")
        self.assertEqual(["id1", "id2"], res)
        tmp_mock = fscen.admin_clients.return_value.node.get_all
        tmp_mock.assert_called_once_with(environment_id="env")

    def test__node_is_assigned(self):
        fscen = utils.FuelScenario()
        fscen.admin_clients = mock.Mock()
        fscen.admin_clients.return_value.node.get_by_id.return_value = {
            "id": "id1", "cluster": "some_id"}
        self.assertTrue(fscen._node_is_assigned("id1"))
        fscen.admin_clients.return_value.node.get_by_id.return_value[
            "cluster"] = ""
        self.assertFalse(fscen._node_is_assigned("id2"))

    @mock.patch(UTILS + "FuelScenario._node_is_assigned", return_value=False)
    @mock.patch(UTILS + "FuelScenario._list_node_ids",
                return_value=["id1", "id2"])
    def test__get_free_node_id(self, mock__list_node_ids,
                               mock__node_is_assigned):
        node_id = utils.FuelScenario()._get_free_node_id()
        self.assertIn(node_id, mock__list_node_ids.return_value)

    @mock.patch(UTILS + "FuelScenario._node_is_assigned", return_value=True)
    @mock.patch(UTILS + "FuelScenario._list_node_ids",
                return_value=["id1", "id2"])
    def test__get_free_node_id_exception(self, mock__list_node_ids,
                                         mock__node_is_assigned):
        self.assertRaises(RuntimeError,
                          utils.FuelScenario()._get_free_node_id)
