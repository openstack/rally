# Copyright 2014: Mirantis Inc.
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

from rally import consts
from rally.deployment.engines import fuel
from rally import exceptions
from tests.unit import fakes
from tests.unit import test

import mock


SAMPLE_CONFIG = {
    "type": "FuelEngine",
    "deploy_name": "TestDeploy01",
    "net_provider": "nova_network",
    "release": "Havana on Ubuntu 12.04",
    "api_url": "http://example.net:8000/api/v1/",
    "mode": "multinode",
    "networks": {"public": {"cidr": "10.1.1.0/24"}},
    "nodes": {
        "controller": {"amount": 1, "filters": ["cpus==2"]},
        "cinder+compute": {"amount": 4, "filters": ["cpus==8",
                                                    "storage>=2T"]},
    },
}


class FuelEngineTestCase(test.TestCase):

    def setUp(self):
        super(FuelEngineTestCase, self).setUp()
        self.deployment = fakes.FakeDeployment({"config": SAMPLE_CONFIG})

    def test_construct(self):
        fuel.FuelEngine(self.deployment)

    def test_validate_no_computes(self):
        config = SAMPLE_CONFIG.copy()
        config["nodes"].pop("cinder+compute")
        deployment = {"config": config}
        engine = fuel.FuelEngine(deployment)
        self.assertRaises(exceptions.ValidationError,
                          engine.validate)

    def test__get_nodes(self):
        engine = fuel.FuelEngine(self.deployment)
        engine.nodes = mock.MagicMock()
        engine.nodes.pop.side_effect = [1, 2, 3, 4]
        nodes = engine._get_nodes("cinder+compute")
        self.assertEqual([1, 2, 3, 4], nodes)
        expected_calls = [mock.call(["cpus==8", "storage>=2T"])] * 4
        self.assertEqual(expected_calls, engine.nodes.pop.mock_calls)

    def test__get_nodes_no_nodes(self):
        engine = fuel.FuelEngine(self.deployment)
        engine.nodes = mock.MagicMock()
        engine.nodes.pop.return_value = None
        self.assertRaises(exceptions.NoNodesFound,
                          engine._get_nodes, "controller")

    def test__get_nodes_empty(self):
        engine = fuel.FuelEngine(self.deployment)
        self.assertEqual([], engine._get_nodes("nonexistent"))

    def test__get_release_id(self):
        engine = fuel.FuelEngine(self.deployment)
        engine.client = mock.Mock()
        fake_releases = [{"name": "fake", "id": 1},
                         {"name": "Havana on Ubuntu 12.04", "id": 42}]
        engine.client.get_releases = mock.Mock(return_value=fake_releases)
        self.assertEqual(42, engine._get_release_id())

    @mock.patch("rally.deployment.fuel.fuelclient.FuelClient")
    @mock.patch("rally.deployment.fuel.fuelclient.FuelCluster")
    def test_deploy(self, mock_fuel_cluster, mock_fuel_client):
        attributes = {"editable": {"access": {"user": {"value": "user"},
                                              "password": {"value": "pw"},
                                              "tenant": {"value": "tn"}}}}
        client = mock.Mock()
        cluster = mock.Mock(
            cluster={"id": 42},
            **{
                "get_endpoint_ip.return_value": "2.3.4.5",
                "get_attributes.return_value": attributes
            }
        )
        mock_fuel_client.return_value = client
        mock_fuel_cluster.return_value = cluster
        self.deployment.add_resource = mock.Mock()

        engine = fuel.FuelEngine(self.deployment)

        engine._get_nodes = mock.Mock(side_effect=[1, 2, 3, 4])
        engine._get_release_id = mock.Mock()

        endpoint = engine.deploy()
        self.assertEqual(["admin"], list(endpoint))
        endpoint = endpoint["admin"]

        self.assertEqual("user", endpoint.username)
        self.assertEqual("pw", endpoint.password)
        self.assertEqual("tn", endpoint.tenant_name)
        self.assertEqual("http://2.3.4.5:5000/v2.0/", endpoint.auth_url)
        self.assertEqual(consts.EndpointPermission.ADMIN, endpoint.permission)

        expected_cluster_calls = [
            mock.call.set_nodes(1, ["controller"]),
            mock.call.set_nodes(2, ["compute"]),
            mock.call.set_nodes(3, ["cinder"]),
            mock.call.set_nodes(4, ["compute", "cinder"]),
            mock.call.configure_network({"public": {"cidr": "10.1.1.0/24"}}),
            mock.call.deploy(),
            mock.call.get_endpoint_ip(),
            mock.call.get_attributes()
        ]
        self.assertEqual(expected_cluster_calls, cluster.mock_calls)
        self.assertEqual([mock.call.get_nodes()], client.mock_calls)

    @mock.patch("rally.deployment.fuel.fuelclient.FuelClient")
    @mock.patch("rally.deployment.engines.fuel.objects.Deployment")
    def test_cleanup(self, mock_deployment, mock_fuel_client):
        fake_resources = [{"id": 41, "info": {"id": 42}}]
        self.deployment.get_resources = mock.Mock(return_value=fake_resources)

        engine = fuel.FuelEngine(self.deployment)
        engine.client = mock.Mock()
        engine.cleanup()

        engine.client.delete_cluster.assert_called_once_with(42)
        mock_deployment.delete_resource.assert_called_once_with(41)
