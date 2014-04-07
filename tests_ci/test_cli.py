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

import ConfigParser
import mock
import os
import shutil
import subprocess
import tempfile
import unittest


"""Test rally command line interface.

This module is intended for running by OpenStack CI system.
To start tests manually please use

 $ tox -ecli

"""


TEST_ENV = {
            "OS_USERNAME": "admin",
            "OS_PASSWORD": "admin",
            "OS_TENANT_NAME": "admin",
            "OS_AUTH_URL": "http://fake/",
}


class RallyCmdError(Exception):

    def __init__(self, code, output):
        self.code = code
        self.output = output

    def __str__(self):
        return "Code: %d Output: %s\n" % (self.code, self.output)

    def __unicode__(self):
        return "Code: %d Output: %s\n" % (self.code, self.output)


class Rally(object):
    """Create and represent separate rally installation.

    Usage:

        rally = Rally()
        rally("deployment", "create", "--name", "Some Deployment Name")
        output = rally("deployment list")

    """

    def __init__(self):
        self.tmp_dir = tempfile.mkdtemp()
        config_filename = os.path.join(self.tmp_dir, 'conf')
        config = ConfigParser.RawConfigParser()
        config.add_section('database')
        config.set('database', 'connection', 'sqlite:///%s/db' % self.tmp_dir)
        with open(config_filename, 'wb') as conf:
            config.write(conf)
        self.args = ['rally', '-d', '-v', '--config-file', config_filename]
        subprocess.call(['rally-manage', '--config-file', config_filename,
                         'db', 'recreate'])

    def __del__(self):
        shutil.rmtree(self.tmp_dir)

    def __call__(self, cmd):
        if not isinstance(cmd, list):
            cmd = cmd.split(" ")
        try:
            return subprocess.check_output(self.args + cmd,
                                           stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            raise RallyCmdError(e.returncode, e.output)


class DeploymentTestCase(unittest.TestCase):

    def test_create_fromenv_list_endpoint(self):
        rally = Rally()
        with mock.patch.dict('os.environ', TEST_ENV):
            rally("deployment create --name t_create --fromenv")
        self.assertIn('t_create', rally("deployment list"))
        self.assertIn(TEST_ENV['OS_AUTH_URL'], rally("deployment endpoint"))
