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
import uuid

from rally.deploy.engines import devstack
from rally.openstack.common import test


SAMPLE_CONFIG = {
    'name': 'DevstackEngine',
    'provider': {
        'name': 'DummyProvider',
        'credentials': [{'user': 'root', 'host': 'example.com'}],
    },
    'localrc': {
        'ADMIN_PASSWORD': 'secret',
    },
}

DEVSTACK_REPO = 'https://github.com/openstack-dev/devstack.git'


class DevstackEngineTestCase(test.BaseTestCase):

    def setUp(self):
        super(DevstackEngineTestCase, self).setUp()
        self.deployment = {
            'uuid': str(uuid.uuid4()),
            'config': SAMPLE_CONFIG,
        }
        self.engine = devstack.DevstackEngine(self.deployment)

    def test_invalid_config(self):
        self.deployment = SAMPLE_CONFIG.copy()
        self.deployment['config'] = {'name': 42}
        self.assertRaises(jsonschema.ValidationError,
                          devstack.DevstackEngine, self.deployment)

    def test_construct(self):
        self.assertEqual(self.engine.localrc['ADMIN_PASSWORD'], 'secret')

    def test_prepare_server(self):
        server = mock.Mock()
        self.engine.prepare_server(server)
        filename = server.ssh.execute_script.mock_calls[0][1][0]
        self.assertTrue(filename.endswith('rally/deploy/engines/'
                                          'devstack/install.sh'))

    @mock.patch('rally.deploy.engines.devstack.open', create=True)
    @mock.patch('rally.serverprovider.provider.Server')
    def test_deploy(self, m_server, m_open):
        s2 = mock.Mock()
        from_credentials = mock.Mock(return_value=s2)
        m_server.from_credentials = from_credentials
        server = mock.Mock(host='fakehost')
        server.get_credentials.return_value = {}
        self.engine.configure_devstack = mock.Mock()
        self.engine.start_devstack = mock.Mock()
        self.engine._vm_provider = mock.Mock()
        self.engine._vm_provider.create_servers.return_value = [server]
        with mock.patch.object(self.engine, 'prepare_server') as ps:
            endpoint = self.engine.deploy()
        ps.assert_called_once_with(server)
        self.assertEqual([mock.call.from_credentials({'user': 'rally'})],
                         m_server.mock_calls)
        self.engine.configure_devstack.assert_called_once_with(s2)
        self.engine.start_devstack.assert_called_once_with(s2)
        self.assertEqual(endpoint, {
            'auth_url': 'http://fakehost:5000/v2.0/',
            'username': 'admin',
            'password': 'secret',
            'tenant_name': 'admin',
        })

    @mock.patch('rally.deploy.engines.devstack.os')
    @mock.patch('rally.deploy.engines.devstack.tempfile')
    @mock.patch('rally.deploy.engines.devstack.open', create=True)
    def test_configure_devstack(self, m_open, m_tmpf, m_os):
        m_tmpf.mkstemp.return_value = (42, 'tmpnam')
        fake_file = mock.Mock()
        m_open.return_value = fake_file
        server = mock.Mock()
        self.engine.localrc = {'k1': 'v1', 'k2': 'v2'}

        self.engine.configure_devstack(server)

        calls = [
            mock.call.ssh.execute('git', 'clone', DEVSTACK_REPO),
            mock.call.ssh.upload('tmpnam', '~/devstack/localrc'),
        ]
        self.assertEqual(calls, server.mock_calls)
        fake_file.asser_has_calls([
            mock.call.write('k1=v1\n'),
            mock.call.write('k2=v2\n'),
        ])
        os_calls = [
            mock.call.close(42),
            mock.call.unlink('tmpnam'),
        ]
        self.assertEqual(os_calls, m_os.mock_calls)

    def test_start_devstack(self):
        server = mock.Mock()
        self.assertTrue(self.engine.start_devstack(server))
        server.ssh.execute.assert_called_once_with('~/devstack/stack.sh')
