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

from rally.deployment.engines import devstack
from tests.unit import test


SAMPLE_CONFIG = {
    "type": "DevstackEngine",
    "provider": {
        "name": "ExistingServers",
        "credentials": [{"user": "root", "host": "example.com"}],
    },
    "local_conf": {
        "ADMIN_PASSWORD": "secret",
    },
}

DEVSTACK_REPO = "https://git.openstack.org/openstack-dev/devstack"


class DevstackEngineTestCase(test.TestCase):

    def setUp(self):
        super(DevstackEngineTestCase, self).setUp()
        self.deployment = {
            "uuid": "de641026-dbe3-4abe-844a-ffef930a600a",
            "config": SAMPLE_CONFIG,
        }
        self.engine = devstack.DevstackEngine(self.deployment)

    def test_invalid_config(self):
        self.deployment = SAMPLE_CONFIG.copy()
        self.deployment["config"] = {"type": 42}
        engine = devstack.DevstackEngine(self.deployment)
        self.assertRaises(jsonschema.ValidationError,
                          engine.validate)

    def test_construct(self):
        self.assertEqual(self.engine.local_conf["ADMIN_PASSWORD"], "secret")

    @mock.patch("rally.deployment.engines.devstack.open", create=True)
    def test_prepare_server(self, mock_open):
        mock_open.return_value = "fake_file"
        server = mock.Mock()
        server.password = "secret"
        self.engine.prepare_server(server)
        calls = [
            mock.call("/bin/sh -e", stdin="fake_file"),
            mock.call("chpasswd", stdin="rally:secret"),
        ]
        self.assertEqual(calls, server.ssh.run.mock_calls)
        filename = mock_open.mock_calls[0][1][0]
        self.assertTrue(filename.endswith("rally/deployment/engines/"
                                          "devstack/install.sh"))
        self.assertEqual([mock.call(filename, "rb")], mock_open.mock_calls)

    @mock.patch("rally.deployment.engine.Engine.get_provider")
    @mock.patch("rally.deployment.engines.devstack.get_updated_server")
    @mock.patch("rally.deployment.engines.devstack.get_script")
    @mock.patch("rally.deployment.serverprovider.provider.Server")
    @mock.patch("rally.deployment.engines.devstack.objects.Credential")
    def test_deploy(self, mock_credential, mock_server, mock_get_script,
                    mock_get_updated_server, mock_engine_get_provider):
        mock_engine_get_provider.return_value = fake_provider = (
            mock.Mock()
        )
        server = mock.Mock(host="host")
        mock_credential.return_value = "fake_credential"
        mock_get_updated_server.return_value = ds_server = mock.Mock()
        mock_get_script.return_value = "fake_script"
        server.get_credentials.return_value = "fake_credentials"
        fake_provider.create_servers.return_value = [server]
        with mock.patch.object(self.engine, "deployment") as mock_deployment:
            credentials = self.engine.deploy()
        self.assertEqual({"admin": "fake_credential"}, credentials)
        mock_credential.assert_called_once_with(
            "http://host:5000/v2.0/", "admin", "secret", "admin", "admin")
        mock_deployment.add_resource.assert_called_once_with(
            info="fake_credentials",
            provider_name="DevstackEngine",
            type="credentials")
        repo = "https://git.openstack.org/openstack-dev/devstack"
        cmd = "/bin/sh -e -s %s master" % repo
        server.ssh.run.assert_called_once_with(cmd, stdin="fake_script")
        ds_calls = [
            mock.call.ssh.run("cat > ~/devstack/local.conf", stdin=mock.ANY),
            mock.call.ssh.run("~/devstack/stack.sh")
        ]
        self.assertEqual(ds_calls, ds_server.mock_calls)
        local_conf = ds_server.mock_calls[0][2]["stdin"]
        self.assertIn("ADMIN_PASSWORD=secret", local_conf)
