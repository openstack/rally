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

import os
import sys

import mock
import testtools

from rally import exceptions
from rally.openstack.common import jsonutils
from rally.verification.verifiers.tempest import subunit2json
from rally.verification.verifiers.tempest import tempest
from tests import test


TEMPEST_PATH = 'rally.verification.verifiers.tempest'


class TempestTestCase(test.TestCase):

    def setUp(self):
        super(TempestTestCase, self).setUp()
        self.verifier = tempest.Tempest('fake_deploy_id',
                                        verification=mock.MagicMock())

        self.verifier.tempest_path = '/tmp'
        self.verifier.config_file = '/tmp/tempest.conf'
        self.verifier.log_file_raw = '/tmp/subunit.stream'
        self.regex = None

    @mock.patch('os.path.exists', return_value=True)
    def test_is_installed(self, mock_exists):
        result = self.verifier.is_installed()

        mock_exists.assert_called_once_with(
            os.path.join(self.verifier.tempest_path, '.venv'))
        self.assertTrue(result)

    @mock.patch('rally.verification.verifiers.tempest.tempest.subprocess')
    def test__clone(self, mock_sp):
        self.verifier._clone()
        mock_sp.check_call.assert_called_once_with(
            ['git', 'clone', 'https://github.com/openstack/tempest',
             tempest.Tempest.tempest_base_path])

    @mock.patch(TEMPEST_PATH + '.tempest.Tempest._initialize_testr')
    @mock.patch(TEMPEST_PATH + '.tempest.Tempest._install_venv')
    @mock.patch(TEMPEST_PATH + '.tempest.subprocess')
    @mock.patch('os.path.exists')
    @mock.patch('shutil.copytree')
    def test_install(
            self, mock_copytree, mock_exists, mock_sp, mock_venv, mock_testr):
        mock_exists.side_effect = (False, True, False)
        # simulate tempest is clonned but is not installed for current deploy

        self.verifier.install()
        mock_copytree.assert_called_once_with(
            tempest.Tempest.tempest_base_path,
            self.verifier.tempest_path)
        mock_sp.check_call.assert_called_once_with(
            'git checkout master; git remote update; git pull',
            cwd=os.path.join(self.verifier.tempest_path, 'tempest'),
            shell=True)

    @mock.patch('rally.verification.verifiers.tempest.tempest.shutil')
    @mock.patch('os.path.exists', return_value=True)
    def test_uninstall(self, mock_exists, mock_shutil):
        self.verifier.uninstall()
        mock_shutil.rmtree.assert_called_once_with(self.verifier.tempest_path)

    @mock.patch(TEMPEST_PATH + '.tempest.Tempest.env')
    @mock.patch(TEMPEST_PATH + '.tempest.subprocess')
    def test_run(self, mock_sp, mock_env):
        self.verifier.run('tempest.api.image')
        fake_call = (
            '%(venv)s testr run --parallel --subunit tempest.api.image '
            '| tee %(tempest_path)s/subunit.stream '
            '| %(venv)s subunit-2to1 '
            '| %(venv)s %(tempest_path)s/tools/colorizer.py' % {
                'venv': self.verifier.venv_wrapper,
                'tempest_path': self.verifier.tempest_path})
        mock_sp.check_call.assert_called_once_with(
            fake_call, env=mock_env, cwd=self.verifier.tempest_path,
            shell=True)

    @mock.patch(TEMPEST_PATH + '.tempest.os.remove')
    @mock.patch(TEMPEST_PATH + '.tempest.Tempest.discover_tests')
    @mock.patch(TEMPEST_PATH + '.tempest.Tempest._initialize_testr')
    @mock.patch(TEMPEST_PATH + '.tempest.Tempest.run')
    @mock.patch(TEMPEST_PATH + '.config.TempestConf')
    @mock.patch('rally.db.deployment_get')
    @mock.patch('rally.osclients.Clients')
    @mock.patch('rally.objects.endpoint.Endpoint')
    def test_verify(self, mock_endpoint, mock_osclients, mock_get, mock_conf,
                    mock_run, mock_testr_init, mock_discover, mock_os):
        self.verifier.verify("smoke", None)
        mock_conf().generate.assert_called_once_with(self.verifier.config_file)
        mock_run.assert_called_once_with("smoke")

    @mock.patch('os.environ')
    def test__generate_env(self, mock_env):
        expected_env = {'PATH': '/some/path'}
        mock_env.copy.return_value = expected_env.copy()
        expected_env.update({
            'TEMPEST_CONFIG': 'tempest.conf',
            'TEMPEST_CONFIG_DIR': self.verifier.tempest_path,
            'OS_TEST_PATH': os.path.join(self.verifier.tempest_path,
                                         'tempest/test_discover')})
        self.assertIsNone(self.verifier._env)
        self.verifier._generate_env()
        self.assertEqual(expected_env, self.verifier._env)

    @mock.patch('os.path.isdir', return_value=True)
    @mock.patch(TEMPEST_PATH + '.tempest.subprocess')
    @testtools.skipIf(sys.version_info < (2, 7), "Incompatible Python Version")
    def test__venv_install_when_venv_exists(self, mock_sp, mock_isdir):
        self.verifier._install_venv()

        mock_isdir.assert_called_once_with(
            os.path.join(self.verifier.tempest_path, '.venv'))
        self.assertFalse(mock_sp.called)

    @mock.patch('os.path.isdir', return_value=False)
    @mock.patch(TEMPEST_PATH + '.tempest.subprocess.check_call')
    @testtools.skipIf(sys.version_info < (2, 7), "Incompatible Python Version")
    def test__venv_install_when_venv_not_exist(self, mock_sp, mock_isdir):
        self.verifier._install_venv()

        mock_isdir.assert_called_once_with(
            os.path.join(self.verifier.tempest_path, '.venv'))
        mock_sp.assert_has_calls([
            mock.call('python ./tools/install_venv.py', shell=True,
                      cwd=self.verifier.tempest_path),
            mock.call('%s python setup.py install' %
                      self.verifier.venv_wrapper, shell=True,
                      cwd=self.verifier.tempest_path)])

    @mock.patch('os.path.isdir', return_value=False)
    @testtools.skipIf(sys.version_info >= (2, 7),
                      "Incompatible Python Version")
    def test__venv_install_for_py26_fails(self, mock_isdir):
        self.assertRaises(exceptions.IncompatiblePythonVersion,
                          self.verifier._install_venv)

        mock_isdir.assert_called_once_with(
            os.path.join(self.verifier.tempest_path, '.venv'))

    @mock.patch('os.path.isdir', return_value=True)
    @mock.patch(TEMPEST_PATH + '.tempest.subprocess')
    def test__initialize_testr_when_testr_already_initialized(
            self, mock_sp, mock_isdir):
        self.verifier._initialize_testr()

        mock_isdir.assert_called_once_with(
            os.path.join(self.verifier.tempest_path, '.testrepository'))
        self.assertFalse(mock_sp.called)

    @mock.patch('os.path.isdir', return_value=False)
    @mock.patch(TEMPEST_PATH + '.tempest.subprocess.check_call')
    def test__initialize_testr_when_testr_not_initialized(
            self, mock_sp, mock_isdir):
        self.verifier._initialize_testr()

        mock_isdir.assert_called_once_with(
            os.path.join(self.verifier.tempest_path, '.testrepository'))
        mock_sp.assert_called_once_with(
            '%s testr init' % self.verifier.venv_wrapper, shell=True,
            cwd=self.verifier.tempest_path)

    @mock.patch.object(subunit2json, 'main')
    @mock.patch('os.path.isfile', return_value=False)
    def test__save_results_without_log_file(self, mock_isfile, mock_parse):

        self.verifier._save_results()
        self.assertEqual(0, mock_parse.call_count)

    @mock.patch('os.path.isfile', return_value=True)
    def test__save_results_with_log_file(self, mock_isfile):
        with mock.patch.object(subunit2json, 'main') as mock_main:
            data = {'total': True, 'test_cases': True}
            mock_main.return_value = jsonutils.dumps(data)
            self.verifier.log_file_raw = os.path.join(
                                            os.path.dirname(__file__),
                                            'subunit.stream')
            self.verifier._save_results()
            mock_isfile.assert_called_once_with(self.verifier.log_file_raw)
            mock_main.assert_called_once_with(
                self.verifier.log_file_raw)

            self.assertEqual(
                1, self.verifier.verification.finish_verification.call_count)
