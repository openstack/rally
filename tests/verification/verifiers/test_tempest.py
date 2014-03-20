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
        self.verifier = tempest.Tempest('fake_deploy_id')
        self.verifier.lock_path = 'fake_lock_path'
        self.conf_args = {'flavor_ref_alt': 'fake_flavor_ref_alt',
                          'flavor_ref': 'fake_flavor_ref',
                          'image_ref_alt': 'fake_image_ref_alt',
                          'image_ref': 'fake_image_ref',
                          'password': 'fake_password',
                          'username': 'fake_username',
                          'tenant_name': 'fake_tenant_name',
                          'uri': 'fake_uri',
                          'uri_v3': 'fake_uri',
                          'lock_path': self.verifier.lock_path,
                          'set_name': 'smoke',
                          'regex': None}
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
            uri=self.conf_args['uri'],
            uri_v3=self.conf_args['uri_v3'],
            regex=None)

        with open(self.tempest_dir + 'config.ini') as config_file:
            self.assertEqual(test_config, config_file.read() % self.conf_args)

    @mock.patch('__builtin__.open')
    def test__write_config(self, mock_open):
        conf = mock.Mock()
        mock_file = mock.MagicMock()
        mock_open.return_value = mock_file
        fake_conf_path = os.path.join(self.verifier.tempest_path,
                                      'tempest.conf')
        returned_conf_path = self.verifier._write_config(conf)
        mock_open.assert_called_once_with(fake_conf_path, 'w+')
        mock_file.write.assert_called_once_whith(conf)
        mock_file.close.assert_called_once()
        self.assertEqual(fake_conf_path, returned_conf_path)

    @mock.patch('os.path.exists')
    def test_is_installed(self, mock_exists):
        mock_exists.return_value = True

        result = self.verifier.is_installed()

        mock_exists.assert_called_once_with(self.verifier.tempest_path)
        self.assertTrue(result)

    @mock.patch('rally.verification.verifiers.tempest.tempest.subprocess')
    def test__clone(self, mock_sp):
        self.verifier._clone()
        mock_sp.call.assert_called_once_with(
            ['git', 'clone', 'git://github.com/openstack/tempest',
             tempest.Tempest.tempest_base_path])

    @mock.patch('rally.verification.verifiers.tempest.tempest.subprocess')
    @mock.patch('os.path.exists')
    @mock.patch('shutil.copytree')
    def test_install(self, mock_copytree, mock_exists, mock_sp):
        mock_exists.side_effect = (True, False)
        # simulate tempest is clonned but is not installed for current deploy

        self.verifier.install()
        mock_copytree.assert_called_once_with(
            tempest.Tempest.tempest_base_path,
            self.verifier.tempest_path)
        mock_sp.Popen.assert_called_once_with(
            'git checkout master; git remote update; git pull',
            cwd=os.path.join(self.verifier.tempest_path, 'tempest'),
            shell=True)

    @mock.patch('rally.verification.verifiers.tempest.tempest.shutil')
    @mock.patch('os.path.exists')
    def test_uninstall(self, mock_exists, mock_shutil):
        mock_exists.return_value = True
        self.verifier.uninstall()
        mock_shutil.rmtree.assert_called_once_with(self.verifier.tempest_path)

    @mock.patch('shutil.rmtree')
    @mock.patch(TEMPEST_PATH + '.subprocess')
    def test__run(self, mock_sp, mock_rmtree):
        self.verifier._run('fake_conf_path', 'smoke', None)

        mock_sp.check_call.assert_called_once_with(
            ['/usr/bin/env', 'bash', os.path.join(self.verifier.tempest_path,
                                                  'run_tempest.sh'),
             '-C', 'fake_conf_path', '-s', ''])

    @mock.patch('rally.verification.verifiers.tempest.tempest.Tempest._run')
    @mock.patch(TEMPEST_PATH + '.Tempest._write_config')
    @mock.patch(TEMPEST_PATH + '.Tempest._generate_config')
    def test_verify(self, mock_gen, mock_write, mock_run):
        mock_gen.return_value = 'fake_conf'
        mock_write.return_value = 'fake_conf_path'

        self.verifier.verify(**self.conf_args)

        mock_gen.assert_called_once_with(**self.conf_args)
        mock_write.assert_called_once_with('fake_conf')
        mock_run.assert_called_once_with('fake_conf_path', 'smoke', None)
