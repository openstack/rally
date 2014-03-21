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

LOG = logging.getLogger(__name__)


class Tempest(object):

    tempest_base_path = os.path.join(os.path.expanduser("~"),
                                     '.rally/tempest/base')

    def __init__(self, deploy_id):
        self.lock_path = tempfile.mkdtemp()
        self.tempest_path = os.path.join(os.path.expanduser("~"),
                                         '.rally/tempest',
                                         'for-deployment-%s' % deploy_id)

    def _generate_config(self, **kwargs):
        kwargs['lock_path'] = self.lock_path
        with open(os.path.join(os.path.dirname(__file__),
                               'config.ini')) as conf:
            return conf.read() % kwargs

    def _write_config(self, conf):
        config_path = os.path.join(self.tempest_path, 'tempest.conf')
        if not os.path.isfile(config_path):
            with open(config_path, 'w+') as f:
                f.write(conf)
        return config_path

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

    def _run(self, config_path, set_name, regex):
        run_script = os.path.join(self.tempest_path, 'run_tempest.sh')
        if set_name == 'full':
            set_path = ''
        elif set_name == 'smoke':
            set_path = '-s'
        else:
            set_path = 'tempest.api.%s' % set_name
        regex = regex if regex else ''
        try:
            subprocess.check_call(
                ['/usr/bin/env', 'bash', run_script, '-C', config_path,
                 set_path, regex])
        except subprocess.CalledProcessError:
            print('Test set %s has been finished with error. '
                  'Check log for details' % set_name)
        finally:
            shutil.rmtree(self.lock_path)

        #TODO(miarmak) Change log_file and parse it

    def verify(self, **kwargs):
        conf = self._generate_config(**kwargs)
        config_path = self._write_config(conf)
        LOG.debug("Temporary tempest config file: %s " % config_path)
        self._run(config_path, kwargs['set_name'], kwargs['regex'])
