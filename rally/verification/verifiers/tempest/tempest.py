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


import logging
import os
import shutil
import subprocess
import tempfile
from xml.dom import minidom as md

from six.moves import configparser

from rally.openstack.common.gettextutils import _
from rally import utils

LOG = logging.getLogger(__name__)


class Tempest(object):

    tempest_base_path = os.path.join(os.path.expanduser("~"),
                                     '.rally/tempest/base')

    def __init__(self, deploy_id, verification=None):
        self.lock_path = tempfile.mkdtemp()
        self.tempest_path = os.path.join(os.path.expanduser("~"),
                                         '.rally/tempest',
                                         'for-deployment-%s' % deploy_id)
        self.config_file = os.path.join(self.tempest_path, 'tempest.conf')
        self.log_file = os.path.join(self.tempest_path, 'testr_log.xml')
        self._venv_wrapper = os.path.join(self.tempest_path,
                                          'tools/with_venv.sh')
        self.verification = verification

    def _generate_config(self, options):
        conf = configparser.ConfigParser()
        conf.optionxform = str
        conf.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
        for section, values in options:
            if section not in conf.sections() and section != 'DEFAULT':
                conf.add_section(section)
            for key, value in values:
                conf.set(section, key, value)
        conf.set('DEFAULT', 'lock_path', self.lock_path)
        return conf

    def _write_config(self, conf):
        with open(self.config_file, 'w+') as f:
            conf.write(f)

    def _generate_env(self):
        env = os.environ.copy()
        env['TEMPEST_CONFIG_DIR'] = self.tempest_path
        env['TEMPEST_CONFIG'] = os.path.basename(self.config_file)
        env['OS_TEST_PATH'] = os.path.join(self.tempest_path,
                                           'tempest/test_discover')
        LOG.debug('Generated environ: %s' % env)
        return env

    def _install_venv(self):
        if not os.path.isdir(os.path.join(self.tempest_path, '.venv')):
            LOG.info('No virtual environment found...Install the virtualenv.')
            LOG.debug('Virtual environment directory: %s' %
                      os.path.join(self.tempest_path, '.venv'))
            subprocess.check_call('python ./tools/install_venv.py', shell=True,
                                  cwd=self.tempest_path)
            # NOTE(akurilin): junitxml is required for subunit2junitxml filter.
            # This library not in openstack/requirements, so we must install it
            # by this way.
            subprocess.check_call(
                '%s pip install junitxml' % self._venv_wrapper,
                shell=True, cwd=self.tempest_path)

    @utils.log_verification_wrapper(LOG.info,
                                    _('Check existence of configuration file'))
    def _check_config_existence(self, options):
        LOG.debug("Tempest config file: %s " % self.config_file)
        if not os.path.isfile(self.config_file):
            conf = self._generate_config(options)
            self._write_config(conf)

    @utils.log_verification_wrapper(
        LOG.info, _('Check initialization of test repository.'))
    def _check_testr_initialization(self):
        if not os.path.isdir(os.path.join(self.tempest_path,
                                          '.testrepository')):
            subprocess.call('%s testr init' % self._venv_wrapper, shell=True,
                            cwd=self.tempest_path)

    def is_installed(self):
        return os.path.exists(os.path.join(self.tempest_path, '.venv'))

    @staticmethod
    def _clone():
        print('Please wait while tempest is being cloned. '
              'This could take a few minutes...')
        subprocess.check_call(['git', 'clone',
                               'git://github.com/openstack/tempest',
                               Tempest.tempest_base_path])

    def install(self):
        if not self.is_installed():
            try:
                if not os.path.exists(Tempest.tempest_base_path):
                    Tempest._clone()

                if not os.path.exists(self.tempest_path):
                    shutil.copytree(Tempest.tempest_base_path,
                                    self.tempest_path)
                    subprocess.check_call('git checkout master; '
                                          'git remote update; '
                                          'git pull', shell=True,
                                          cwd=os.path.join(self.tempest_path,
                                                           'tempest'))
                self._install_venv()
            except subprocess.CalledProcessError:
                print ('Tempest installation failed.')
                return 1
            else:
                print('Tempest has been successfully installed!')
        else:
            print('Tempest is already installed')

    def uninstall(self):
        if os.path.exists(self.tempest_path):
            shutil.rmtree(self.tempest_path)

    @utils.log_verification_wrapper(LOG.info, _('Run verification.'))
    def _prepare_and_run(self, set_name, regex, options):
        self._check_config_existence(options)
        self._check_testr_initialization()

        if set_name == 'full':
            testr_arg = ''
        elif set_name == 'smoke':
            testr_arg = 'smoke'
        else:
            testr_arg = 'tempest.api.%s' % set_name

        if regex:
            testr_arg += ' %s' % regex

        self.verification.start_verifying(set_name)
        self._run(testr_arg)

    def _run(self, testr_arg):
        testr_runner = (
            '%(venv)s testr run --parallel --subunit %(arg)s '
            '| %(venv)s subunit2junitxml --forward --output-to=%(log_file)s '
            '| %(venv)s subunit-2to1 '
            '| %(venv)s %(tempest_path)s/tools/colorizer.py' %
            {
                'venv': self._venv_wrapper,
                'arg': testr_arg,
                'tempest_path': self.tempest_path,
                'log_file': self.log_file
            })
        try:
            LOG.debug('testr started by the command: %s' % testr_runner)
            subprocess.check_call(testr_runner,
                                  cwd=self.tempest_path,
                                  env=self._generate_env(), shell=True)
        except subprocess.CalledProcessError:
            print('Test set %s has been finished with error. '
                  'Check log for details' % testr_arg)
        finally:
            shutil.rmtree(self.lock_path)

    @utils.log_verification_wrapper(
        LOG.info, _('Saving verification results.'))
    def _save_results(self):
        if os.path.isfile(self.log_file):
            dom = md.parse(self.log_file).getElementsByTagName('testsuite')[0]

            total = {
                'tests': int(dom.getAttribute('tests')),
                'errors': int(dom.getAttribute('errors')),
                'failures': int(dom.getAttribute('failures')),
                'time': float(dom.getAttribute('time')),
            }

            test_cases = {}
            for test_elem in dom.getElementsByTagName('testcase'):
                if test_elem.getAttribute('name') == 'process-returncode':
                    total['failures'] -= 1
                else:
                    test = {
                        'name': ".".join((test_elem.getAttribute('classname'),
                                          test_elem.getAttribute('name'))),
                        'time': float(test_elem.getAttribute('time'))
                    }

                    failure = test_elem.getElementsByTagName('failure')
                    if failure:
                        test['status'] = 'FAIL'
                        test['failure'] = {
                            'type': failure[0].getAttribute('type'),
                            'log': failure[0].firstChild.nodeValue}
                    else:
                        test['status'] = 'OK'
                    test_cases[test['name']] = test
            self.verification.finish_verification(total=total,
                                                  test_cases=test_cases)
        else:
            LOG.error('XML-log file not found.')

    def verify(self, set_name, regex, options):
        self._prepare_and_run(set_name, regex, options)
        self._save_results()
