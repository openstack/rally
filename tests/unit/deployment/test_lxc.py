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

import mock

from rally.common import objects
from rally.deployment import engine
from tests.unit import test

MOD = "rally.deployment.engines.lxc."


class LxcEngineTestCase(test.TestCase):

    def setUp(self):
        super(LxcEngineTestCase, self).setUp()
        self.config = {
            "type": "LxcEngine",
            "container_name": "rally",
            "containers_per_host": 2,
            "tunnel_to": ["1.1.1.1", "2.2.2.2"],
            "distribution": "ubuntu",
            "start_lxc_network": "10.128.128.0/28",
            "engine": {
                "name": "FakeEngine",
                "config": {
                    "key": "value",
                },
            },
            "provider": {
                "type": "DummyProvider",
                "credentials": [{"user": "root", "host": "host1.net"},
                                {"user": "root", "host": "host2.net"}]
            }
        }
        self.deployment = {
            "uuid": "test-deployment-uuid",
            "config": self.config,
        }
        self.engine = engine.Engine.get_engine("LxcEngine",
                                               self.deployment)

    @mock.patch(MOD + "objects")
    @mock.patch(MOD + "engine")
    def test__deploy_first(self, mock_engine, mock_objects):
        fake_credentials = {"user": "admin", "host": "host.net"}
        fake_deployment = mock.Mock()
        fake_engine = mock.Mock()
        mock_objects.Deployment = mock.Mock(return_value=fake_deployment)
        mock_engine.Engine.get_engine = mock.Mock(
            return_value=fake_engine)

        fake_host = mock.Mock()
        fake_so = mock.Mock()
        fake_so.get_credentials.return_value = fake_credentials
        fake_host.get_server_object = mock.Mock(return_value=fake_so)
        self.engine._deploy_first(fake_host, "name", "dist", "release")
        host_calls = [
            mock.call.prepare(),
            mock.call.create_container("name", "dist", "release"),
            mock.call.start_containers(),
            mock.call.get_server_object("name"),
            mock.call.stop_containers()]
        self.assertEqual(host_calls, fake_host.mock_calls)
        fake_engine.deploy.assert_called_once_with()
        mock_engine.Engine.get_engine.assert_called_once_with(
            "FakeEngine", fake_deployment)
        engine_config = self.config["engine"].copy()
        engine_config["provider"] = {"credentials": [fake_credentials],
                                     "type": "DummyProvider"}
        mock_objects.Deployment.assert_called_once_with(
            config=engine_config, parent_uuid="test-deployment-uuid")

    @mock.patch(MOD + "provider.ProviderFactory.get_provider")
    def test__get_provider(self, mock_provider_factory_get_provider):
        mock_provider_factory_get_provider.return_value = "fake_provider"
        provider = self.engine._get_provider()
        self.assertEqual("fake_provider", provider)
        mock_provider_factory_get_provider.assert_called_once_with(
            self.config["provider"], self.deployment)

    @mock.patch(MOD + "open", create=True)
    @mock.patch(MOD + "get_script_path", return_value="fake_sp")
    @mock.patch(MOD + "lxc.LxcHost")
    @mock.patch(MOD + "LxcEngine._deploy_first")
    @mock.patch(MOD + "LxcEngine._get_provider")
    def test_deploy(self, mock__get_provider, mock__deploy_first,
                    mock_lxc_host, mock_get_script_path, mock_open):
        mock_open.return_value = "fs"
        fake_containers = ((mock.Mock(), mock.Mock()),
                           (mock.Mock(), mock.Mock()))
        fake_hosts = mock_lxc_host.side_effect = [mock.Mock(), mock.Mock()]
        fake_hosts[0].get_server_objects.return_value = fake_containers[0]
        fake_hosts[1].get_server_objects.return_value = fake_containers[1]
        fake_hosts[0]._port_cache = {1: 2, 3: 4}
        fake_hosts[1]._port_cache = {5: 6, 7: 8}
        fake_provider = mock__get_provider.return_value
        fake_servers = [mock.Mock(), mock.Mock()]
        fake_servers[0].get_credentials.return_value = "fc1"
        fake_servers[1].get_credentials.return_value = "fc2"
        fake_provider.create_servers.return_value = fake_servers

        add_res_calls = [
            {"provider_name": "LxcEngine",
             "info": {"host": "fc1",
                      "config": {"network": "10.128.128.0/28",
                                 "tunnel_to": ["1.1.1.1", "2.2.2.2"]},
                      "forwarded_ports": [(1, 2), (3, 4)],
                      "containers": fake_hosts[0].containers}},
            {"provider_name": "LxcEngine",
             "info": {"host": "fc2",
                      "config": {"network": "10.128.128.16/28",
                                 "tunnel_to": ["1.1.1.1", "2.2.2.2"]},
                      "forwarded_ports": [(5, 6), (7, 8)],
                      "containers": fake_hosts[1].containers}}]

        def add_resource(**actual_kwargs):
            expected_kwargs = add_res_calls.pop(0)

            self.assertEqual(expected_kwargs["provider_name"],
                             actual_kwargs["provider_name"])
            self.assertEqual(expected_kwargs["info"]["host"],
                             actual_kwargs["info"]["host"])
            self.assertEqual(expected_kwargs["info"]["config"],
                             actual_kwargs["info"]["config"])
            self.assertEqual(expected_kwargs["info"]["containers"],
                             actual_kwargs["info"]["containers"])
            self.assertSequenceEqual(
                expected_kwargs["info"]["forwarded_ports"],
                actual_kwargs["info"]["forwarded_ports"])

        fake_deployment = mock.MagicMock()
        fake_deployment.add_resource = add_resource

        with mock.patch.object(self.engine, "deployment", fake_deployment):
            credential = self.engine.deploy()

        self.assertIsInstance(credential["admin"], objects.Credential)
        lxc_host_calls = [
            mock.call(fake_servers[0], {"network": "10.128.128.0/28",
                                        "tunnel_to": ["1.1.1.1", "2.2.2.2"]}),
            mock.call(fake_servers[1], {"network": "10.128.128.16/28",
                                        "tunnel_to": ["1.1.1.1", "2.2.2.2"]})]
        self.assertEqual(lxc_host_calls, mock_lxc_host.mock_calls)
        deploy_first_calls = [
            mock.call(fake_hosts[0], "rally-10-128-128-0-000", "ubuntu", None),
            mock.call(fake_hosts[1], "rally-10-128-128-16-000", "ubuntu",
                      None)]
        self.assertEqual(deploy_first_calls, mock__deploy_first.mock_calls)

        host1_calls = [
            mock.call.create_clone("rally-10-128-128-0-001",
                                   "rally-10-128-128-0-000"),
            mock.call.start_containers(),
            mock.call.get_server_objects()]

        host2_calls = [
            mock.call.create_clone("rally-10-128-128-16-001",
                                   "rally-10-128-128-16-000"),
            mock.call.start_containers(),
            mock.call.get_server_objects()]

        self.assertEqual(host1_calls, fake_hosts[0].mock_calls)
        self.assertEqual(host2_calls, fake_hosts[1].mock_calls)

        self.assertEqual([mock.call("fake_sp", "rb")] * 4,
                         mock_open.mock_calls)

        for host in fake_containers:
            for container in host:
                self.assertEqual([mock.call.ssh.run("/bin/sh -e", stdin="fs")],
                                 container.mock_calls)

    @mock.patch(MOD + "LxcEngine._get_provider")
    @mock.patch(MOD + "lxc.LxcHost")
    @mock.patch(MOD + "provider.Server.from_credentials")
    def test_cleanup(self, mock_server_from_credentials, mock_lxc_host,
                     mock__get_provider):
        mock__get_provider.return_value = fake_provider = mock.Mock()
        mock_lxc_host.side_effect = fake_hosts = [mock.Mock(), mock.Mock()]
        mock_server_from_credentials.side_effect = ["s1", "s2"]
        fake_resources = []
        for i in range(2):
            res = mock.Mock()
            res.info = {"host": "host%d" % i,
                        "config": "fake_config%d" % i,
                        "forwarded_ports": [(1, 2), (3, 4)],
                        "containers": "fake_containers"}
            fake_resources.append(res)
        with mock.patch.object(self.engine, "deployment") as mock_deployment:
            mock_deployment.get_resources.return_value = fake_resources
            self.engine.cleanup()

        for host in fake_hosts:
            self.assertEqual("fake_containers", host.containers)
            self.assertEqual([mock.call.destroy_containers(),
                              mock.call.destroy_ports([(1, 2), (3, 4)]),
                              mock.call.delete_tunnels()], host.mock_calls)

        delete_calls = [mock.call.delete_resource(r.id)
                        for r in fake_resources]
        self.assertEqual(delete_calls,
                         mock_deployment.delete_resource.call_args_list)

        fake_provider.destroy_servers.assert_called_once_with()
