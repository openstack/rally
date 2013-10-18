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
import os

from rally.deploy.engines import devstack
from rally.openstack.common import test


SAMPLE_CONFIG = {
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
        self.task = mock.MagicMock()
        self.task['uuid'] = mock.MagicMock()
        self.de = devstack.DevstackEngine(self.task, SAMPLE_CONFIG)
        super(DevstackEngineTestCase, self).setUp()

    def test_construct(self):
        self.assertEqual(self.de.localrc['ADMIN_PASSWORD'], 'secret')

    def test_deploy(self):
        with mock.patch('rally.deploy.engines.devstack.sshutils') as ssh:
            self.de.deploy()
        config_tmp_filename = ssh.mock_calls[2][1][2]
        call = mock.call
        install_script = 'rally/deploy/engines/devstack/install.sh'
        expected = [
            call.execute_script('root', 'example.com',
                                os.path.abspath(install_script)),
            call.execute_command('rally', 'example.com',
                                 ['git', 'clone', DEVSTACK_REPO]),
            call.upload_file('rally', 'example.com', config_tmp_filename,
                             '~/devstack/localrc'),
            call.execute_command('rally', 'example.com',
                                 ['~/devstack/stack.sh'])
        ]
        self.assertEqual(expected, ssh.mock_calls)
