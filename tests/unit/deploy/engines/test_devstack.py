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

from rally.deploy.engines import devstack
from tests.unit import test


SAMPLE_CONFIG = {
    'type': 'DevstackEngine',
    'provider': {
        'name': 'ExistingServers',
        'credentials': [{'user': 'root', 'host': 'example.com'}],
    },
    'localrc': {
        'ADMIN_PASSWORD': 'secret',
    },
}

DEVSTACK_REPO = 'https://github.com/openstack-dev/devstack.git'


class DevstackEngineTestCase(test.TestCase):

    def setUp(self):
        super(DevstackEngineTestCase, self).setUp()
        self.deployment = {
            'uuid': 'de641026-dbe3-4abe-844a-ffef930a600a',
            'config': SAMPLE_CONFIG,
        }
        self.engine = devstack.DevstackEngine(self.deployment)

    def test_invalid_config(self):
        self.deployment = SAMPLE_CONFIG.copy()
        self.deployment['config'] = {'type': 42}
        self.assertRaises(jsonschema.ValidationError,
                          devstack.DevstackEngine, self.deployment)

    def test_construct(self):
        self.assertEqual(self.engine.localrc['ADMIN_PASSWORD'], 'secret')

    @mock.patch('rally.deploy.engines.devstack.open', create=True)
    def test_prepare_server(self, m_open):
        m_open.return_value = 'fake_file'
        server = mock.Mock()
        server.password = 'secret'
        self.engine.prepare_server(server)
        calls = [
            mock.call('/bin/sh -e', stdin='fake_file'),
            mock.call('chpasswd', stdin='rally:secret'),
        ]
        self.assertEqual(calls, server.ssh.run.mock_calls)
        filename = m_open.mock_calls[0][1][0]
        self.assertTrue(filename.endswith('rally/deploy/engines/'
                                          'devstack/install.sh'))
        self.assertEqual([mock.call(filename, 'rb')], m_open.mock_calls)

    @mock.patch('rally.deploy.engine.EngineFactory.get_provider')
    @mock.patch('rally.deploy.engines.devstack.get_updated_server')
    @mock.patch('rally.deploy.engines.devstack.get_script')
    @mock.patch('rally.deploy.serverprovider.provider.Server')
    @mock.patch('rally.deploy.engines.devstack.objects.Endpoint')
    def test_deploy(self, m_endpoint, m_server, m_gs, m_gus, m_gp):
        m_gp.return_value = fake_provider = mock.Mock()
        server = mock.Mock()
        server.host = 'host'
        m_endpoint.return_value = 'fake_endpoint'
        m_gus.return_value = ds_server = mock.Mock()
        m_gs.return_value = 'fake_script'
        server.get_credentials.return_value = 'fake_credentials'
        fake_provider.create_servers.return_value = [server]
        with mock.patch.object(self.engine, 'deployment') as m_d:
            endpoints = self.engine.deploy()
        self.assertEqual({"admin": "fake_endpoint"}, endpoints)
        m_endpoint.assert_called_once_with('http://host:5000/v2.0/', 'admin',
                                           'secret', 'admin', 'admin')
        m_d.add_resource.assert_called_once_with(
                                    info='fake_credentials',
                                    provider_name='DevstackEngine',
                                    type='credentials')
        repo = 'https://github.com/openstack-dev/devstack.git'
        cmd = '/bin/sh -e -s %s master' % repo
        server.ssh.run.assert_called_once_with(cmd, stdin='fake_script')
        ds_calls = [
            mock.call.ssh.run('cat > ~/devstack/localrc', stdin=mock.ANY),
            mock.call.ssh.run('~/devstack/stack.sh')
        ]
        self.assertEqual(ds_calls, ds_server.mock_calls)
        localrc = ds_server.mock_calls[0][2]['stdin']
        self.assertIn('ADMIN_PASSWORD=secret', localrc)
