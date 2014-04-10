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

import six

from rally.verification.verifiers.tempest import tempest
from tests import test
from tests.verification.verifiers import fakes


TEMPEST_PATH = 'rally.verification.verifiers.tempest.tempest'


class TempestTestCase(test.TestCase):

    def setUp(self):
        super(TempestTestCase, self).setUp()
        self.verifier = tempest.Tempest('fake_deploy_id')

        self.verifier.verification = mock.MagicMock()

        self.verifier.lock_path = 'fake_lock_path'
        self.conf_opts = (
            ('compute', [
                ('flavor_ref_alt', 'fake_flavor_ref_alt'),
                ('flavor_ref', 'fake_flavor_ref'),
                ('image_ref_alt', 'fake_image_ref_alt'),
                ('image_ref', 'fake_image_ref')]),
            ('compute-admin', [('password', 'fake_password')]),
            ('identity', [
                ('username', 'fake_username'),
                ('password', 'fake_password'),
                ('tenant_name', 'fake_tenant_name'),
                ('admin_username', 'fake_username'),
                ('admin_password', 'fake_password'),
                ('admin_tenant_name', 'fake_tenant_name'),
                ('uri', 'fake_uri'),
                ('uri_v3', 'fake_uri')]))
        self.set_name = 'smoke'
        self.regex = None

    def test__generate_config(self):
        test_config = self.verifier._generate_config(self.conf_opts)

        self.assertEqual(len(fakes.FAKE_CONFIG) - 1,
                         len(test_config.sections()))
        for section, values in six.iteritems(fakes.FAKE_CONFIG):
            if section != 'DEFAULT':
                # NOTE(akurilin): Method `items` from ConfigParser return
                # a list of (name, value) pairs for each option in the given
                # section with options from DEFAULT section, so we need to
                # extend  FAKE_CONFIG for correct comparison.

                values.extend(fakes.FAKE_CONFIG['DEFAULT'])

            self.assertEqual(set(values),
                             set(test_config.items(section)))

    @mock.patch("rally.verification.verifiers.tempest.tempest.open",
                create=True)
    def test__write_config(self, mock_open):
        conf = mock.Mock()
        mock_file = mock.MagicMock()
        mock_open.return_value = mock_file
        fake_conf_path = os.path.join(self.verifier.tempest_path,
                                      'tempest.conf')
        self.verifier._write_config(conf)
        mock_open.assert_called_once_with(fake_conf_path, 'w+')
        self.assertEqual([mock.call.__enter__(),
                          mock.call.__exit__(None, None, None)],
                         mock_file.mock_calls)

    @mock.patch('os.path.exists')
    def test_is_installed(self, mock_exists):
        mock_exists.return_value = True

        result = self.verifier.is_installed()

        mock_exists.assert_called_once_with(
            os.path.join(self.verifier.tempest_path, '.venv'))
        self.assertTrue(result)

    @mock.patch('rally.verification.verifiers.tempest.tempest.subprocess')
    def test__clone(self, mock_sp):
        self.verifier._clone()
        mock_sp.check_call.assert_called_once_with(
            ['git', 'clone', 'git://github.com/openstack/tempest',
             tempest.Tempest.tempest_base_path])

    @mock.patch(TEMPEST_PATH + '.Tempest._install_venv')
    @mock.patch(TEMPEST_PATH + '.subprocess')
    @mock.patch('os.path.exists')
    @mock.patch('shutil.copytree')
    def test_install(self, mock_copytree, mock_exists, mock_sp, mock_venv):
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
    @mock.patch('os.path.exists')
    def test_uninstall(self, mock_exists, mock_shutil):
        mock_exists.return_value = True
        self.verifier.uninstall()
        mock_shutil.rmtree.assert_called_once_with(self.verifier.tempest_path)

    @mock.patch(TEMPEST_PATH + '.Tempest._generate_env')
    @mock.patch('shutil.rmtree')
    @mock.patch(TEMPEST_PATH + '.subprocess')
    def test__run(self, mock_sp, mock_rmtree, mock_env):
        self.verifier._run('smoke')
        fake_call = (
            '%(venv)s testr run --parallel --subunit smoke '
            '| %(venv)s subunit2junitxml --forward '
            '--output-to=%(tempest_path)s/testr_log.xml '
            '| %(venv)s subunit-2to1 '
            '| %(venv)s %(tempest_path)s/tools/colorizer.py' % {
                'venv': self.verifier._venv_wrapper,
                'tempest_path': self.verifier.tempest_path})
        mock_sp.check_call.assert_called_once_with(
            fake_call, env=mock_env(), cwd=self.verifier.tempest_path,
            shell=True)

    @mock.patch(TEMPEST_PATH + '.Tempest._save_results')
    @mock.patch(TEMPEST_PATH + '.Tempest._prepare_and_run')
    def test_verify(self, mock_run, mock_save_results):
        self.verifier.verify(set_name=self.set_name, regex=None,
                             options=self.conf_opts)

        mock_run.assert_called_once_with('smoke', None, self.conf_opts)

    @mock.patch(TEMPEST_PATH + '.Tempest._check_testr_initialization')
    @mock.patch(TEMPEST_PATH + '.Tempest._run')
    @mock.patch(TEMPEST_PATH + '.Tempest._write_config')
    @mock.patch(TEMPEST_PATH + '.Tempest._generate_config')
    def test__prepare_and_run(self, mock_gen, mock_write, mock_run,
                              mock_check_testr):
        mock_gen.return_value = 'fake_conf'

        self.verifier._prepare_and_run(set_name=self.set_name,
                                       regex=None,
                                       options=self.conf_opts)

        mock_gen.assert_called_once_with(self.conf_opts)
        mock_write.assert_called_once_with('fake_conf')
        mock_run.assert_called_once_with('smoke')

    @mock.patch('os.environ')
    def test__generate_env(self, mock_env):
        expected_env = {'PATH': '/some/path'}
        mock_env.copy.return_value = expected_env.copy()
        expected_env.update({
            'TEMPEST_CONFIG': 'tempest.conf',
            'TEMPEST_CONFIG_DIR': self.verifier.tempest_path,
            'OS_TEST_PATH': os.path.join(self.verifier.tempest_path,
                                         'tempest/test_discover')})
        self.assertEqual(expected_env, self.verifier._generate_env())

    @mock.patch('os.path.isdir')
    @mock.patch(TEMPEST_PATH + '.subprocess')
    def test__venv_install_when_venv_exists(self, mock_sp, mock_isdir):
        mock_isdir.return_value = True
        self.verifier._install_venv()

        mock_isdir.assert_called_once_with(
            os.path.join(self.verifier.tempest_path, '.venv'))
        self.assertEqual(0, mock_sp.call_count)

    @mock.patch('os.path.isdir')
    @mock.patch(TEMPEST_PATH + '.subprocess')
    def test__venv_install_when_venv_not_exist(self, mock_sp, mock_isdir):
        mock_isdir.return_value = False
        self.verifier._install_venv()

        mock_isdir.assert_called_once_with(
            os.path.join(self.verifier.tempest_path, '.venv'))
        mock_sp.check_call.assert_has_calls([
            mock.call('python ./tools/install_venv.py', shell=True,
                      cwd=self.verifier.tempest_path),
            mock.call('%s pip install junitxml' % self.verifier._venv_wrapper,
                      shell=True, cwd=self.verifier.tempest_path)])

    @mock.patch('os.path.isdir')
    @mock.patch(TEMPEST_PATH + '.subprocess')
    def test__check_testr_initialization_when_testr_already_initialized(
            self, mock_sp, mock_isdir):
        mock_isdir.return_value = True
        self.verifier._check_testr_initialization()

        mock_isdir.assert_called_once_with(
            os.path.join(self.verifier.tempest_path, '.testrepository'))
        self.assertEqual(0, mock_sp.call_count)

    @mock.patch('os.path.isdir')
    @mock.patch(TEMPEST_PATH + '.subprocess.call')
    def test__check_testr_initialization_when_testr_not_initialized(
            self, mock_sp, mock_isdir):
        mock_isdir.return_value = False
        self.verifier._check_testr_initialization()

        mock_isdir.assert_called_once_with(
            os.path.join(self.verifier.tempest_path, '.testrepository'))
        mock_sp.assert_called_once_with(
            '%s testr init' % self.verifier._venv_wrapper, shell=True,
            cwd=self.verifier.tempest_path)

    @mock.patch('xml.dom.minidom')
    @mock.patch('os.path.isfile')
    def test__save_results_without_log_file(self, mock_isfile, mock_minidom):
        mock_isfile.return_value = False

        self.verifier._save_results()

        mock_isfile.assert_called_once_with(self.verifier.log_file)
        self.assertEqual(0, mock_minidom.call_count)

    @mock.patch('os.path.isfile')
    def test__save_results_with_log_file(self, mock_isfile):
        mock_isfile.return_value = True
        self.verifier.log_file = os.path.join(os.path.dirname(__file__),
                                              'fake_log.xml')

        self.verifier._save_results()
        mock_isfile.assert_called_once_with(self.verifier.log_file)
        fake_test_case = fakes.get_fake_test_case()
        self.verifier.verification.finish_verification.assert_called_once_with(
            total=fake_test_case['total'],
            test_cases=fake_test_case['test_cases'])
