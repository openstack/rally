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

from six.moves import configparser

LOG = logging.getLogger(__name__)


class Tempest(object):

    tempest_base_path = os.path.join(os.path.expanduser("~"),
                                     '.rally/tempest/base')

    def __init__(self, deploy_id):
        self.lock_path = tempfile.mkdtemp()
        self.tempest_path = os.path.join(os.path.expanduser("~"),
                                         '.rally/tempest',
                                         'for-deployment-%s' % deploy_id)
        self.config_file = os.path.join(self.tempest_path, 'tempest.conf')
        self._venv_wrapper = os.path.join(self.tempest_path,
                                          'tools/with_venv.sh')

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

    def _check_venv_existence(self):
        if not os.path.isdir(os.path.join(self.tempest_path, '.venv')):
            LOG.info('No virtual environment found...Install the virtualenv.')
            LOG.debug('Virtual environment directory: %s' %
                      os.path.join(self.tempest_path, '.venv'))
            subprocess.call('python ./tools/install_venv.py', shell=True,
                            cwd=self.tempest_path)

    def _check_testr_initialization(self):
        if not os.path.isdir(os.path.join(self.tempest_path,
                                          '.testrepository')):
            subprocess.call('%s testr init' % self._venv_wrapper, shell=True,
                            cwd=self.tempest_path)

    def is_installed(self):
        return os.path.exists(self.tempest_path)

    @staticmethod
    def _clone():
        subprocess.call(['git', 'clone', 'git://github.com/openstack/tempest',
                        Tempest.tempest_base_path])

    def install(self):
        if not os.path.exists(Tempest.tempest_base_path):
            Tempest._clone()
        if os.path.exists(self.tempest_path):
            print('Tempest is already installed')
        else:
            shutil.copytree(Tempest.tempest_base_path, self.tempest_path)
            subprocess.Popen('git checkout master; git remote update; '
                             'git pull', shell=True,
                             cwd=os.path.join(self.tempest_path,
                                              'tempest')).communicate()
            print('Tempest has been successfully installed!')

    def uninstall(self):
        if os.path.exists(self.tempest_path):
            shutil.rmtree(self.tempest_path)

    def _run(self, set_name, regex):
        if set_name == 'full':
            set_path = ''
        elif set_name == 'smoke':
            set_path = 'smoke'
        else:
            set_path = 'tempest.api.%s' % set_name
        regex = regex if regex else ''

        testr_runner = '%(venv)s testr run --parallel --subunit ' \
                       '%(set_path)s %(regex)s | %(venv)s subunit-2to1 ' \
                       '| %(venv)s %(tempest_path)s/tools/colorizer.py' % {
                           'venv': self._venv_wrapper,
                           'set_path': set_path,
                           'regex': regex,
                           'tempest_path': self.tempest_path}
        try:
            LOG.debug('testr started by the command: %s' % testr_runner)
            subprocess.check_call(testr_runner,
                                  cwd=self.tempest_path,
                                  env=self._generate_env(), shell=True)
        except subprocess.CalledProcessError:
            print('Test set %s has been finished with error. '
                  'Check log for details' % set_name)
        finally:
            shutil.rmtree(self.lock_path)

        #TODO(miarmak) Change log_file and parse it

    def verify(self, set_name, regex, options):
        if not os.path.isfile(self.config_file):
            conf = self._generate_config(options)
            self._write_config(conf)
        LOG.debug("Tempest config file: %s " % self.config_file)
        self._check_venv_existence()
        self._check_testr_initialization()

        self._run(set_name, regex)
