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
import os
import uuid

from rally.deploy.engines import devstack
from rally.openstack.common import test


SAMPLE_CONFIG = {
    'name': 'DevstackEngine',
    'provider': {
        'name': 'DummyProvider',
        'credentials': ['root@example.com'],
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
        self.de = devstack.DevstackEngine(self.deployment)

    def test_invalid_config(self):
        self.deployment['config']['name'] = 42
        self.assertRaises(jsonschema.ValidationError,
                          devstack.DevstackEngine, self.deployment)

    def test_construct(self):
        self.assertEqual(self.de.localrc['ADMIN_PASSWORD'], 'secret')

    def test_deploy(self):
        with mock.patch('rally.sshutils.SSH') as ssh:
            self.de.deploy()
        config_tmp_filename = ssh.mock_calls[4][1][0]
        call = mock.call
        install_script = 'rally/deploy/engines/devstack/install.sh'
        expected = [
            call('example.com', 'root'),
            call().execute_script(os.path.abspath(install_script)),
            call('example.com', 'rally'),
            call().execute('git', 'clone', DEVSTACK_REPO),
            call().upload(config_tmp_filename, '~/devstack/localrc'),
            call().execute('~/devstack/stack.sh')]
        self.assertEqual(expected, ssh.mock_calls)
