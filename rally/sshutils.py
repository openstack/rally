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

import subprocess

DEFAULT_OPTIONS = ['-o', 'StrictHostKeyChecking=no']


class SSHException(Exception):
    pass


def upload_file(user, host, source, destination):
    cmd = ['scp'] + DEFAULT_OPTIONS + [
        source, '%s@%s:%s' % (user, host, destination)]
    pipe = subprocess.Popen(cmd, stderr=subprocess.PIPE)
    (so, se) = pipe.communicate()
    if pipe.returncode:
        raise SSHException(se)


def execute_script(user, host, script, enterpreter='/bin/sh'):
    cmd = ['ssh'] + DEFAULT_OPTIONS + ['%s@%s' % (user, host), enterpreter]
    subprocess.check_call(cmd, stdin=open(script, 'r'))


def execute_command(user, host, cmd):
    pipe = subprocess.Popen(['ssh'] + DEFAULT_OPTIONS +
                            ['%s@%s' % (user, host)] + cmd,
                            stderr=subprocess.PIPE)
    (so, se) = pipe.communicate()
    if pipe.returncode:
        raise SSHException(se)
