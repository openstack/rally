# Copyright 2013: Mirantis Inc.
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

from rally.deployment.fuel import fuelclient
from tests.unit import test


class FuelNodeTestCase(test.TestCase):

    def test_check(self):

        node = {
            "cluster": None,
            "mac": "00:01:02:0a:0b:0c",
            "meta": {
                "memory": {"total": 42},
                "cpu": {"total": 2},
                "disks": [{"size": 22}, {"size": 33}]  # total 55
            },
        }

        n = fuelclient.FuelNode(node)

        self.assertFalse(n.check("ram==41"))
        self.assertFalse(n.check("ram!=42"))
        self.assertFalse(n.check("ram<=41"))
        self.assertFalse(n.check("ram>=43"))
        self.assertFalse(n.check("ram>43"))
        self.assertFalse(n.check("ram<41"))
        self.assertFalse(n.check("cpus>3"))

        self.assertTrue(n.check("ram==42"))
        self.assertTrue(n.check("ram!=41"))
        self.assertTrue(n.check("ram<=43"))
        self.assertTrue(n.check("ram<=42"))
        self.assertTrue(n.check("ram>=41"))
        self.assertTrue(n.check("ram>=42"))
        self.assertTrue(n.check("ram<43"))
        self.assertTrue(n.check("ram>41"))
        self.assertTrue(n.check("cpus==2"))

        self.assertTrue(n.check("mac==00:01:02:0a:0b:0c"))
        self.assertTrue(n.check("mac!=00:01:02:0a:0b:0e"))
        self.assertTrue(n.check("storage==55"))
        self.assertTrue(n.check("storage<=1G"))
        self.assertTrue(n.check("storage<1M"))


class FuelNodesCollectionTestCase(test.TestCase):

    def test_pop(self):
        node = {
            "cluster": None,
            "mac": "00:01:02:0a:0b:0c",
            "meta": {
                "memory": {"total": 42},
                "cpu": {"total": 2},
                "disks": [{"size": 22}, {"size": 33}]  # total 55
            },
        }

        nodes = [copy.deepcopy(node) for i in range(4)]
        nodes[0]["meta"]["cpu"]["total"] = 1
        nodes[1]["meta"]["cpu"]["total"] = 2
        nodes[2]["meta"]["memory"]["total"] = 16
        nodes[3]["cluster"] = 42  # node with cluster is occupied

        nodes = fuelclient.FuelNodesCollection(nodes)

        node_1cpu = nodes.pop(["cpus==1"])
        self.assertEqual(node_1cpu._get_cpus(), 1)
        self.assertEqual(len(nodes.nodes), 3)

        node_2cpu = nodes.pop(["cpus==2"])
        self.assertEqual(node_2cpu._get_cpus(), 2)
        self.assertEqual(len(nodes.nodes), 2)

        node_16ram_2cpu = nodes.pop(["ram>=16", "cpus==2"])
        self.assertEqual(node_16ram_2cpu._get_ram(), 16)
        self.assertEqual(node_16ram_2cpu._get_cpus(), 2)
        self.assertEqual(len(nodes.nodes), 1)
        node_none = nodes.pop(["storage>4T"])
        self.assertIsNone(node_none)


class FuelClusterTestCase(test.TestCase):

    def setUp(self):
        super(FuelClusterTestCase, self).setUp()
        self.client = mock.Mock()
        self.config = {"name": "Cluster"}
        self.cluster = fuelclient.FuelCluster(self.client, **self.config)

    def test_init(self):
        self.client.post.assert_called_once_with("clusters", self.config)

    def test_get_nodes(self):
        self.cluster.cluster = {"id": 42}
        self.cluster.get_nodes()
        self.client.get.assert_called_once_with("nodes?cluster_id=42")

    def test_set_nodes_empty(self):
        self.assertIsNone(self.cluster.set_nodes([], []))

    def test_set_nodes(self):
        nodes = [{"id": 42}, {"id": 43}]
        self.cluster.cluster = {"id": 1}
        self.cluster.set_nodes(nodes, ["role1", "role2"])

        node42_args = {"cluster_id": 1,
                       "pending_roles": ["role1", "role2"],
                       "pending_addition": True,
                       "id": 42}
        node43_args = {"cluster_id": 1,
                       "pending_roles": ["role1", "role2"],
                       "pending_addition": True,
                       "id": 43}
        expected = [
            mock.call.post("clusters", {"name": "Cluster"}),
            mock.call.put("nodes", [node42_args, node43_args])
        ]
        self.assertEqual(expected, self.client.mock_calls)

    def test_configure_network(self):
        current_network = {"networks": [{"name": "public",
                                         "key": "old_val",
                                         "key2": "val2"}]}

        netconfig = {"public": {"key": "new_val"}}
        self.cluster.get_network = mock.Mock(return_value=current_network)
        self.cluster.set_network = mock.Mock()

        self.cluster.configure_network(netconfig)

        self.cluster.set_network.assert_called_once_with(
            {"networks": [{"name": "public",
                           "key": "new_val",
                           "key2": "val2"}]})

    @mock.patch("rally.deployment.fuel.fuelclient.time.sleep")
    def test_deploy(self, mock_sleep):
        call1 = {"progress": 50}
        call2 = {"progress": 100}
        self.client.get_task.side_effect = [call1, call2]

        tasks = [{"name": "deploy", "id": 41}]
        self.client.get_tasks.return_value = tasks

        self.cluster.cluster = {"id": 42}
        self.cluster.deploy()

        expected = [
            mock.call.post("clusters", {"name": "Cluster"}),
            mock.call.put("clusters/42/changes", {}),
            mock.call.get_tasks(42),
            mock.call.get_task(41),
            mock.call.get_task(41)
        ]
        self.assertEqual(expected, self.client.mock_calls)

    def test_get_network(self):
        self.cluster.cluster = {"id": 42, "net_provider": "nova_network"}
        self.cluster.get_network()
        self.client.get.assert_called_once_with(
            "clusters/42/network_configuration/nova_network")

    def test_set_network(self):
        self.cluster.cluster = {"id": 42, "net_provider": "nova_network"}
        self.cluster.verify_network = mock.Mock()
        self.cluster.set_network({"key": "val"})

        self.client.put.assert_called_once_with(
            "clusters/42/network_configuration/nova_network", {"key": "val"})
        self.cluster.verify_network.assert_called_once_with({"key": "val"})

    @mock.patch("rally.deployment.fuel.fuelclient.time.sleep")
    def test_verify_network(self, mock_sleep):
        call1 = {"progress": 50}
        call2 = {"progress": 100, "message": ""}

        self.client.put.return_value = {"id": 42}
        self.client.get_task.side_effect = [call1, call2]
        self.cluster.cluster = {"id": 43, "net_provider": "nova_network"}

        self.cluster.verify_network({"key": "val"})

        self.client.put.assert_called_once_with(
            "clusters/43/network_configuration/nova_network/verify",
            {"key": "val"})
        self.assertEqual([mock.call(42), mock.call(42)],
                         self.client.get_task.mock_calls)

    @mock.patch("rally.deployment.fuel.fuelclient.time.sleep")
    def test_verify_network_fail(self, mock_sleep):
        self.client.put.return_value = {"id": 42}
        self.client.get_task.return_value = {"progress": 100,
                                             "message": "error"}
        self.cluster.cluster = {"id": 43, "net_provider": "nova_network"}
        self.assertRaises(fuelclient.FuelNetworkVerificationFailed,
                          self.cluster.verify_network, {"key": "val"})

    def test_get_attributes(self):
        self.cluster.cluster = {"id": 52}
        self.cluster.get_attributes()
        self.client.get.assert_called_once_with("clusters/52/attributes")

    def test_get_endpoint_ip_multinode(self):
        self.cluster.cluster = {"mode": "multinode"}
        node1 = {"roles": ["compute", "cinder"]}
        node2 = {"roles": ["controller"],
                 "network_data": [{"name": "private"},
                                  {"name": "public", "ip": "42.42.42.42/24"}]}
        fake_nodes = [node1, node2]
        self.cluster.get_nodes = mock.Mock(return_value=fake_nodes)
        ip = self.cluster.get_endpoint_ip()
        self.assertEqual("42.42.42.42", ip)

    def test_get_endpoint_ip_ha(self):
        ip = "1.2.3.4"
        self.cluster.cluster = {"id": 42, "mode": "ha_compact"}
        self.cluster.get_network = mock.Mock(return_value={"public_vip": ip})
        self.assertEqual(ip, self.cluster.get_endpoint_ip())


class FuelClientTestCase(test.TestCase):

    def setUp(self):
        super(FuelClientTestCase, self).setUp()
        self.client = fuelclient.FuelClient("http://10.20.0.2:8000/api/v1/")

    @mock.patch("rally.deployment.fuel.fuelclient.requests")
    def test__request_non_json(self, mock_requests):
        reply = mock.Mock()
        reply.status_code = 200
        reply.headers = {"content-type": "application/x-httpd-php"}
        reply.text = "{\"reply\": \"ok\"}"
        mock_requests.method.return_value = reply

        retval = self.client._request("method", "url", data={"key": "value"})

        self.assertEqual(retval, reply)

    @mock.patch("rally.deployment.fuel.fuelclient.requests")
    def test__request_non_2xx(self, mock_requests):
        reply = mock.Mock()
        reply.status_code = 300
        reply.headers = {"content-type": "application/json"}
        reply.text = "{\"reply\": \"ok\"}"
        mock_requests.method.return_value = reply
        self.assertRaises(fuelclient.FuelClientException,
                          self.client._request, "method", "url",
                          data={"key": "value"})

    @mock.patch("rally.deployment.fuel.fuelclient.requests")
    def test__request(self, mock_requests):
        reply = mock.Mock()
        reply.status_code = 202
        reply.headers = {"content-type": "application/json"}
        reply.text = "{\"reply\": \"ok\"}"
        mock_requests.method.return_value = reply

        retval = self.client._request("method", "url", data={"key": "value"})
        mock_requests.method.assert_called_once_with(
            "http://10.20.0.2:8000/api/v1/url",
            headers={"content-type": "application/json"},
            data="{\"key\": \"value\"}")
        self.assertEqual(retval, {"reply": "ok"})

    @mock.patch.object(fuelclient.FuelClient, "_request")
    def test_get(self, mock_fuel_client__request):
        self.client.get("url")
        mock_fuel_client__request.assert_called_once_with("get", "url")

    @mock.patch.object(fuelclient.FuelClient, "_request")
    def test_delete(self, mock_fuel_client__request):
        self.client.delete("url")
        mock_fuel_client__request.assert_called_once_with("delete", "url")

    @mock.patch.object(fuelclient.FuelClient, "_request")
    def test_post(self, mock_fuel_client__request):
        self.client.post("url", {"key": "val"})
        mock_fuel_client__request.assert_called_once_with(
            "post", "url", {"key": "val"})

    @mock.patch.object(fuelclient.FuelClient, "_request")
    def test_put(self, mock_fuel_client__request):
        self.client.put("url", {"key": "val"})
        mock_fuel_client__request.assert_called_once_with(
            "put", "url", {"key": "val"})

    @mock.patch.object(fuelclient.FuelClient, "get")
    def test_get_releases(self, mock_fuel_client_get):
        self.client.get_releases()
        mock_fuel_client_get.assert_called_once_with("releases")

    @mock.patch.object(fuelclient.FuelClient, "get")
    def test_get_task(self, mock_fuel_client_get):
        self.client.get_task(42)
        mock_fuel_client_get.assert_called_once_with("tasks/42")

    @mock.patch.object(fuelclient.FuelClient, "get")
    def test_get_tasks(self, mock_fuel_client_get):
        self.client.get_tasks(42)
        mock_fuel_client_get.assert_called_once_with("tasks?cluster_id=42")

    @mock.patch.object(fuelclient.FuelClient, "get")
    def test_get_node(self, mock_fuel_client_get):
        self.client.get_node(42)
        mock_fuel_client_get.assert_called_once_with("nodes/42")

    @mock.patch.object(fuelclient, "FuelNodesCollection")
    @mock.patch.object(fuelclient.FuelClient, "get")
    def test_get_nodes(self, mock_fuel_client_get, mock_fuel_nodes_collection):
        mock_fuel_client_get.return_value = "fake_nodes"
        mock_fuel_nodes_collection.return_value = "fake_collection"
        retval = self.client.get_nodes()
        self.assertEqual("fake_collection", retval)
        mock_fuel_nodes_collection.assert_called_once_with("fake_nodes")
        mock_fuel_client_get.assert_called_once_with("nodes")

    @mock.patch.object(fuelclient.FuelClient, "delete")
    def test_delete_cluster(self, mock_fuel_client_delete):
        self.client.delete_cluster(42)
        mock_fuel_client_delete.assert_called_once_with("clusters/42")
