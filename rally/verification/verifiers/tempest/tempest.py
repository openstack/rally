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
import shutil
import subprocess
import tempfile


class Tempest(object):

    def __init__(self):
        self.lock_path = tempfile.mkdtemp()

    def _generate_config(self, **kwargs):
        kwargs['lock_path'] = self.lock_path
        with open('rally/verification/verifiers/tempest/config.ini') as conf:
            return conf.read() % kwargs

    @staticmethod
    def _define_path():
        dir_path = os.path.dirname(os.path.dirname(__file__))
        tempest_path = os.path.join(dir_path, 'tempest/openstack-tempest/')
        return tempest_path

    @staticmethod
    def _write_config(conf):
        fd, config_path = tempfile.mkstemp()
        os.write(fd, conf)
        os.close(fd)
        return config_path

    def is_installed(self):
        return os.path.exists(self._define_path())

    def install(self):
        tempest_path = self._define_path()
        if os.path.exists(tempest_path):
            print('Tempest is already installed')
        else:
            subprocess.call(
                ['git', 'clone', 'git://github.com/openstack/tempest',
                 tempest_path])
            print('Tempest has been successfully installed!')

    def _run(self, config_path, set_name, regex):
        tempest_path = self._define_path()
        run_script = '%srun_tempest.sh' % tempest_path
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
            os.unlink(config_path)

        #TODO(miarmak) Change log_file and parse it

    def verify(self, **kwargs):
        conf = self._generate_config(**kwargs)
        config_path = self._write_config(conf)
        self._run(config_path, kwargs['set_name'], kwargs['regex'])
