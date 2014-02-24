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

from rally.cmd import envutils
from rally import exceptions
from rally.openstack.common import test


class EnvUtilsTestCase(test.BaseTestCase):

    @mock.patch.dict(os.environ, values={'RALLY_DEPLOYMENT': 'my_deploy_id'},
                     clear=True)
    def test_get_deployment_id_in_env(self):
        deploy_id = envutils._default_deployment_id()
        self.assertEqual('my_deploy_id', deploy_id)

    @mock.patch.dict(os.environ, values={}, clear=True)
    @mock.patch('rally.cmd.envutils.fileutils.load_env_file')
    def test_get_deployment_id_with_exception(self, mock_file):
        self.assertRaises(exceptions.InvalidArgumentsException,
                          envutils._default_deployment_id)
        mock_file.assert_called_once_with(os.path.expanduser(
            '~/.rally/globals'))
