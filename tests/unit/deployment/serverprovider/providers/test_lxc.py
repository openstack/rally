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

import jsonschema
import mock
import netaddr

from rally.deployment.serverprovider.providers import lxc
from rally import exceptions
from tests.unit import test


MOD_NAME = "rally.deployment.serverprovider.providers.lxc."


class HelperFunctionsTestCase(test.TestCase):

    @mock.patch(MOD_NAME + "open", create=True, return_value="fake_script")
    def test__get_script(self, mock_open):
        script = lxc._get_script("script.sh")
        self.assertEqual("fake_script", script)
        path = mock_open.mock_calls[0][1][0]
        mode = mock_open.mock_calls[0][1][1]
        self.assertTrue(path.endswith(
            "rally/deployment/serverprovider/providers/lxc/script.sh"))
        self.assertEqual("rb", mode)

    @mock.patch(MOD_NAME + "_get_script", return_value="fake_script")
    @mock.patch(MOD_NAME + "moves.StringIO")
    def test__get_script_from_template(self, mock_string_io, mock__get_script):
        mock__get_script.return_value = fake_script = mock.Mock()
        fake_script.read.return_value = "fake_data {k1} {k2}"
        mock_string_io.return_value = "fake_formatted_script"
        script = lxc._get_script_from_template("fake_tpl", k1="v1", k2="v2")
        self.assertEqual("fake_formatted_script", script)
        mock_string_io.assert_called_once_with("fake_data v1 v2")


class LxcHostTestCase(test.TestCase):

    def setUp(self):
        super(LxcHostTestCase, self).setUp()

        sample_config = {"network": "10.1.1.0/24",
                         "forward_ssh": True,
                         "tunnel_to": ["1.1.1.1", "2.2.2.2"]}
        self.server = mock.Mock()
        self.server.host = "fake_server_ip"
        self.server.get_credentials.return_value = {"ip": "3.3.3.3"}
        self.host = lxc.LxcHost(self.server, sample_config)

    @mock.patch(MOD_NAME + "provider.Server")
    def test__get_updated_server(self, mock_server):
        server = self.host._get_updated_server(host="4.4.4.4")
        new_server = mock_server.from_credentials({"host": "4.4.4.4"})
        self.assertEqual(new_server, server)

    def test_backingstore_btrfs(self):
        self.server.ssh.execute.return_value = [0, "", ""]
        self.assertEqual("btrfs", self.host.backingstore)
        self.assertEqual("btrfs", self.host.backingstore)
        # second call will return cached value
        self.assertEqual([mock.call.ssh.execute("df -t btrfs /var/lib/lxc/")],
                         self.server.mock_calls)

    def test_backingstore_none(self):
        self.server.ssh.execute.return_value = [-1, "", ""]
        self.assertEqual("", self.host.backingstore)

    @mock.patch(MOD_NAME + "moves.StringIO")
    @mock.patch(MOD_NAME + "_get_script", return_value="fake_script")
    def test_prepare(self, mock__get_script, mock_string_io):
        mock_string_io.return_value = fake_conf = mock.Mock()
        self.host.create_local_tunnels = mock.Mock()
        self.host.create_remote_tunnels = mock.Mock()

        self.host.prepare()

        write_calls = [
            mock.call("LXC_DHCP_MAX=\"253\"\n"),
            mock.call("LXC_NETMASK=\"255.255.255.0\"\n"),
            mock.call("LXC_ADDR=\"10.1.1.1\"\n"),
            mock.call("LXC_DHCP_RANGE=\"10.1.1.2,10.1.1.254\"\n"),
            mock.call("LXC_NETWORK=\"10.1.1.0/24\"\n"),
            mock.call("LXC_BRIDGE=\"lxcbr0\"\n"),
            mock.call("USE_LXC_BRIDGE=\"true\"\n")
        ]
        fake_conf.write.assert_has_calls(write_calls, any_order=True)
        ssh_calls = [mock.call.run("cat > /tmp/.lxc_default", stdin=fake_conf),
                     mock.call.run("/bin/sh", stdin="fake_script")]
        self.assertEqual(ssh_calls, self.server.ssh.mock_calls)
        self.host.create_local_tunnels.assert_called_once_with()
        self.host.create_remote_tunnels.assert_called_once_with()

    @mock.patch(MOD_NAME + "os.unlink")
    @mock.patch(MOD_NAME + "_get_script_from_template")
    def test_create_local_tunnels(self, mock__get_script_from_template,
                                  mock_unlink):
        mock__get_script_from_template.side_effect = ["s1", "s2"]
        self.host.create_local_tunnels()
        getscript_calls = [
            mock.call("tunnel-local.sh", local="fake_server_ip",
                      net=netaddr.IPNetwork("10.1.1.0/24"), remote="1.1.1.1"),
            mock.call("tunnel-local.sh", local="fake_server_ip",
                      net=netaddr.IPNetwork("10.1.1.0/24"), remote="2.2.2.2"),
        ]
        self.assertEqual(
            getscript_calls, mock__get_script_from_template.mock_calls)
        self.assertEqual([mock.call("/bin/sh", stdin="s1"),
                          mock.call("/bin/sh", stdin="s2")],
                         self.server.ssh.run.mock_calls)

    @mock.patch(MOD_NAME + "_get_script_from_template")
    def test_create_remote_tunnels(self, mock__get_script_from_template):
        mock__get_script_from_template.side_effect = ["s1", "s2"]
        fake_server = mock.Mock()
        self.host._get_updated_server = mock.Mock(return_value=fake_server)
        self.host.create_remote_tunnels()
        self.assertEqual([mock.call("/bin/sh", stdin="s1"),
                          mock.call("/bin/sh", stdin="s2")],
                         fake_server.ssh.run.mock_calls)

    def test_delete_tunnels(self):
        s1 = mock.Mock()
        s2 = mock.Mock()
        self.host._get_updated_server = mock.Mock(side_effect=[s1, s2])

        self.host.delete_tunnels()
        s1.ssh.execute.assert_called_once_with("ip tun del t10.1.1.0")
        s2.ssh.execute.assert_called_once_with("ip tun del t10.1.1.0")
        self.assertEqual([mock.call("ip tun del t1.1.1.1"),
                          mock.call("ip tun del t2.2.2.2")],
                         self.server.ssh.execute.mock_calls)

    @mock.patch(MOD_NAME + "time.sleep")
    def test_get_ip(self, mock_sleep):
        s1 = "link/ether fe:54:00:d3:f5:98 brd ff:ff:ff:ff:ff:ff"
        s2 = s1 + "\n   inet 10.20.0.1/24 scope global br1"
        self.host.server.ssh.execute.side_effect = [(0, s1, ""), (0, s2, "")]
        ip = self.host.get_ip("name")
        self.assertEqual("10.20.0.1", ip)
        self.assertEqual([mock.call("lxc-attach -n name ip"
                                    " addr list dev eth0")] * 2,
                         self.host.server.ssh.execute.mock_calls)

    def test_create_container(self):
        self.host.configure_container = mock.Mock()
        self.host._backingstore = "btrfs"
        self.host.create_container("name", "dist")
        self.server.ssh.run.assert_called_once_with(
            "lxc-create -B btrfs -n name -t dist")
        self.assertEqual(["name"], self.host.containers)
        self.host.configure_container.assert_called_once_with("name")

        # check with no btrfs
        self.host._backingstore = ""
        self.host.create_container("name", "dist")
        self.assertEqual(mock.call("lxc-create -n name -t dist"),
                         self.server.ssh.run.mock_calls[1])

        # check release
        self.host.create_container("name", "ubuntu", "raring")
        self.host.create_container("name", "debian", "woody")
        expected = [mock.call("lxc-create -n name -t ubuntu -- -r raring"),
                    mock.call("SUITE=woody lxc-create -n name -t debian")]
        self.assertEqual(expected, self.server.ssh.run.mock_calls[2:])

    def test_create_clone(self):
        self.host._backingstore = "btrfs"
        self.host.configure_container = mock.Mock()
        self.host.create_clone("name", "src")
        self.server.ssh.execute.assert_called_once_with("lxc-clone --snapshot"
                                                        " -o src -n name")
        self.assertEqual(["name"], self.host.containers)

        # check with no btrfs
        self.host._backingstore = ""
        self.host.create_clone("name", "src")
        self.assertEqual(mock.call("lxc-clone -o src -n name"),
                         self.server.ssh.execute.mock_calls[1])

    @mock.patch(MOD_NAME + "os.path.join")
    @mock.patch(MOD_NAME + "_get_script")
    def test_configure_container(self, mock__get_script, mock_join):
        mock__get_script.return_value = "fake_script"
        mock_join.return_value = "fake_path"
        self.server.ssh.execute.return_value = 0, "", ""
        self.host.configure_container("name")
        self.server.ssh.run.assert_called_once_with(
            "/bin/sh -e -s fake_path", stdin="fake_script")

    def test_start_containers(self):
        self.host.containers = ["c1", "c2"]
        self.host.start_containers()
        calls = [mock.call("lxc-start -d -n c1"),
                 mock.call("lxc-start -d -n c2")]
        self.assertEqual(calls, self.server.ssh.run.mock_calls)

    def test_stop_containers(self):
        self.host.containers = ["c1", "c2"]
        self.host.stop_containers()
        calls = [
            mock.call("lxc-stop -n c1"),
            mock.call("lxc-stop -n c2"),
        ]
        self.assertEqual(calls, self.server.ssh.run.mock_calls)

    def test_destroy_containers(self):
        self.host.containers = ["c1", "c2"]
        self.host.destroy_containers()
        calls = [
            mock.call("lxc-stop -n c1"), mock.call("lxc-destroy -n c1"),
            mock.call("lxc-stop -n c2"), mock.call("lxc-destroy -n c2"),
        ]
        self.assertEqual(calls, self.server.ssh.run.mock_calls)

    def test_get_server_object(self):
        fake_server = mock.Mock()
        self.host.get_ip = mock.Mock(return_value="ip")
        self.host.get_port = mock.Mock(return_value=42)
        self.host._get_updated_server = mock.Mock(return_value=fake_server)

        so = self.host.get_server_object("c1", wait=False)

        self.assertEqual(fake_server, so)
        self.host.get_port.assert_called_once_with("ip")
        self.host._get_updated_server.assert_called_once_with(port=42)
        self.assertFalse(fake_server.ssh.wait.mock_calls)
        so = self.host.get_server_object("c1", wait=True)
        fake_server.ssh.wait.assert_called_once_with(timeout=300)

    @mock.patch(MOD_NAME + "LxcHost.get_server_object")
    def test_get_server_objects(self, mock_get_server_object):
        mock_get_server_object.side_effect = ["s1", "s2"]
        self.host.containers = ["c1", "c2"]
        retval = list(self.host.get_server_objects(wait="wait"))
        self.assertEqual(["s1", "s2"], retval)
        self.assertEqual([mock.call("c1", "wait"), mock.call("c2", "wait")],
                         mock_get_server_object.mock_calls)


class LxcProviderTestCase(test.TestCase):

    def setUp(self):
        super(LxcProviderTestCase, self).setUp()
        self.config = {
            "type": "LxcProvider",
            "distribution": "ubuntu",
            "start_lxc_network": "10.1.1.0/29",
            "containers_per_host": 2,
            "tunnel_to": ["10.10.10.10", "20.20.20.20"],
            "container_name_prefix": "rally-lxc",
            "host_provider": {
                "name": "ExistingServers",
                "credentials": [{"user": "root", "host": "host1.net"},
                                {"user": "root", "host": "host2.net"}]}
        }
        self.deployment = {"uuid": "fake_uuid"}
        self.provider = lxc.LxcProvider(self.deployment, self.config)

    def test_validate(self):
        self.provider.validate()

    def test_validate_invalid_tunnel(self):
        config = self.config.copy()
        config["tunnel_to"] = "ok"
        self.assertRaises(jsonschema.ValidationError,
                          lxc.LxcProvider, self.deployment, config)

    def test_validate_required_field(self):
        config = self.config.copy()
        del(config["host_provider"])
        self.assertRaises(jsonschema.ValidationError,
                          lxc.LxcProvider, self.deployment, config)

    def test_validate_too_small_network(self):
        config = self.config.copy()
        config["containers_per_host"] = 42
        self.assertRaises(exceptions.InvalidConfigException,
                          lxc.LxcProvider, self.deployment, config)

    @mock.patch(MOD_NAME + "LxcHost")
    @mock.patch(MOD_NAME + "provider.ProviderFactory.get_provider")
    def test_create_servers(self, mock_provider_factory_get_provider,
                            mock_lxc_host):
        fake_provider = mock.Mock()
        fake_provider.create_servers.return_value = ["server1", "server2"]
        fake_hosts = []
        fake_sos = []
        for i in (1, 2):
            fake_host_sos = [mock.Mock(), mock.Mock()]
            fake_sos.extend(fake_host_sos)
            fake_host = mock.Mock()
            fake_host.containers = ["c-%d-1" % i, "c-%d-2" % i]
            fake_host._port_cache = {1: i, 2: i}
            fake_host.config = {"network": "fake-%d" % i}
            fake_host.server.get_credentials.return_value = {"ip": "f%d" % i}
            fake_host.get_server_objects.return_value = fake_host_sos
            fake_hosts.append(fake_host)
        mock_lxc_host.side_effect = fake_hosts
        mock_provider_factory_get_provider.return_value = fake_provider

        fake_info = [
            {"host": {"ip": "f1"},
             "config": {"network": "fake-1"},
             "forwarded_ports": [(1, 1), (2, 1)],
             "container_names": ["c-1-1", "c-1-2"]},
            {"host": {"ip": "f2"},
             "config": {"network": "fake-2"},
             "forwarded_ports": [(1, 2), (2, 2)],
             "container_names": ["c-2-1", "c-2-2"]}]

        def res_create(actual_info):
            expected_info = fake_info.pop(0)
            self.assertEqual(expected_info["host"], actual_info["host"])
            self.assertEqual(expected_info["config"], actual_info["config"])
            self.assertEqual(expected_info["container_names"],
                             actual_info["container_names"])
            self.assertSequenceEqual(expected_info["forwarded_ports"],
                                     actual_info["forwarded_ports"])

        fake_res = mock.MagicMock()
        fake_res.create = res_create

        with mock.patch.object(self.provider, "resources", fake_res):
            servers = self.provider.create_servers()

        self.assertEqual(fake_sos, servers)

        host1_calls = [
            mock.call.prepare(),
            mock.call.create_container("rally-lxc-000-10-1-1-0",
                                       "ubuntu", None),
            mock.call.create_clone("rally-lxc-001-10-1-1-0",
                                   "rally-lxc-000-10-1-1-0"),
            mock.call.start_containers(),
            mock.call.get_server_objects(),
            mock.call.server.get_credentials(),
        ]
        host2_calls = [
            mock.call.prepare(),
            mock.call.create_container("rally-lxc-000-10-1-1-8",
                                       "ubuntu", None),
            mock.call.create_clone("rally-lxc-001-10-1-1-8",
                                   "rally-lxc-000-10-1-1-8"),
            mock.call.start_containers(),
            mock.call.get_server_objects(),
            mock.call.server.get_credentials(),
        ]

        self.assertEqual(host1_calls, fake_hosts[0].mock_calls)
        self.assertEqual(host2_calls, fake_hosts[1].mock_calls)

    @mock.patch(MOD_NAME + "LxcHost")
    @mock.patch(MOD_NAME + "provider.Server.from_credentials")
    def test_destroy_servers(self, mock_server_from_credentials,
                             mock_lxc_host):
        fake_resource = {"info": {"config": "fake_config",
                                  "host": "fake_credentials",
                                  "forwarded_ports": [1, 2],
                                  "container_names": ["n1", "n2"]}}
        fake_resource["id"] = "fake_res_id"
        fake_host = mock.Mock()
        mock_server_from_credentials.return_value = "fake_server"
        mock_lxc_host.return_value = fake_host
        self.provider.resources = mock.Mock()
        self.provider.resources.get_all.return_value = [fake_resource]

        with mock.patch.object(self.provider, "get_host_provider") as ghp:
            ghp.return_value = fake_host_provider = mock.Mock()
            self.provider.destroy_servers()

        mock_lxc_host.assert_called_once_with("fake_server", "fake_config")
        host_calls = [mock.call.destroy_containers(),
                      mock.call.destroy_ports([1, 2]),
                      mock.call.delete_tunnels()]
        self.assertEqual(host_calls, fake_host.mock_calls)
        self.provider.resources.delete.assert_called_once_with("fake_res_id")
        fake_host_provider.destroy_servers.assert_called_once_with()
