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

import mock
import os

from rally.verification.verifiers.tempest import tempest
from tests import test


TEMPEST_PATH = 'rally.verification.verifiers.tempest.tempest'


class TempestTestCase(test.TestCase):

    def setUp(self):
        super(TempestTestCase, self).setUp()
        self.verifier = tempest.Tempest()
        self.verifier.lock_path = 'fake_lock_path'
        self.conf_args = {'flavor_ref_alt': 'fake_flavor_ref_alt',
                          'flavor_ref': 'fake_flavor_ref',
                          'image_ref_alt': 'fake_image_ref_alt',
                          'image_ref': 'fake_image_ref',
                          'password': 'fake_password',
                          'username': 'fake_username',
                          'tenant_name': 'fake_tenant_name',
                          'uri': 'fake_uri',
                          'lock_path': self.verifier.lock_path}
        self.tempest_dir = 'rally/verification/verifiers/tempest/'

    def test__generate_config(self):
        test_config = self.verifier._generate_config(
            flavor_ref_alt=self.conf_args['flavor_ref_alt'],
            flavor_ref=self.conf_args['flavor_ref'],
            image_ref_alt=self.conf_args['image_ref_alt'],
            image_ref=self.conf_args['image_ref'],
            password=self.conf_args['password'],
            username=self.conf_args['username'],
            tenant_name=self.conf_args['tenant_name'],
            uri=self.conf_args['uri'])

        with open(self.tempest_dir + 'config.ini') as config_file:
            self.assertEqual(test_config, config_file.read() % self.conf_args)

    def test__define_path(self):
        tempest_path = self.verifier._define_path()
        self.assertEqual(os.path.abspath(tempest_path),
                         os.path.abspath(self.tempest_dir +
                                         'openstack-tempest/'))

    @mock.patch('tempfile.mkstemp')
    @mock.patch('rally.verification.verifiers.tempest.tempest.os')
    def test__write_config(self, mock_os, mock_tempfile):
        conf = mock.Mock()
        mock_tempfile.return_value = ['fake_fd', 'fake_path']
        os_calls = [mock.call.write('fake_fd', conf),
                    mock.call.close('fake_fd')]

        conf_path = self.verifier._write_config(conf)

        self.assertEqual(os_calls, mock_os.mock_calls)
        self.assertEqual('fake_path', conf_path)

    @mock.patch('os.path.exists')
    def test_is_installed(self, mock_exists):
        mock_exists.return_value = True

        result = self.verifier.is_installed()

        mock_exists.assert_called_once_with(self.verifier._define_path())
        self.assertTrue(result)

    @mock.patch(TEMPEST_PATH + '.Tempest._define_path')
    @mock.patch('rally.verification.verifiers.tempest.tempest.subprocess')
    @mock.patch('os.path.exists')
    def test_install(self, mock_exists, mock_sp, mock_path):
        mock_path.return_value = 'fake_tempest_path/'
        mock_exists.return_value = False

        self.verifier.install()

        mock_sp.call.assert_called_once_with(
            ['git', 'clone', 'git://github.com/openstack/tempest',
             'fake_tempest_path/'])

    @mock.patch('shutil.rmtree')
    @mock.patch('os.unlink')
    @mock.patch(TEMPEST_PATH + '.subprocess')
    @mock.patch(TEMPEST_PATH + '.Tempest._define_path')
    def test__run(self, mock_path, mock_sp, mock_unlink, mock_rmtree):
        mock_path.return_value = 'fake_tempest_path/'

        self.verifier._run('fake_conf_path')

        mock_unlink.assert_called_once_with('fake_conf_path')
        mock_sp.check_call.assert_called_once_with(
            ['/usr/bin/env', 'bash', 'fake_tempest_path/run_tempest.sh', '-C',
             'fake_conf_path', '-s'])

    @mock.patch('rally.verification.verifiers.tempest.tempest.Tempest._run')
    @mock.patch(TEMPEST_PATH + '.Tempest._write_config')
    @mock.patch(TEMPEST_PATH + '.Tempest._generate_config')
    def test_verify(self, mock_gen, mock_write, mock_run):
        mock_gen.return_value = 'fake_conf'
        mock_write.return_value = 'fake_conf_path'

        self.verifier.verify(kwargs='fake_kwargs')

        mock_gen.assert_called_once_with(kwargs='fake_kwargs')
        mock_write.assert_called_once_with('fake_conf')
        mock_run.assert_called_once_with('fake_conf_path')
