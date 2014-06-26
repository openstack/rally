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
import json
import os
import pwd
import shutil
import subprocess
import tempfile
import unittest

import mock

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


class TaskConfig(object):

    def __init__(self, config):
        config_file = tempfile.NamedTemporaryFile(delete=False)
        config_file.write(json.dumps(config))
        config_file.close()
        self.filename = config_file.name

    def __del__(self):
        os.unlink(self.filename)


class Rally(object):
    """Create and represent separate rally installation.

    Usage:

        rally = Rally()
        rally("deployment", "create", "--name", "Some Deployment Name")
        output = rally("deployment list")

    """

    def __init__(self):
        # NOTE(sskripnick): we shoud change home dir to avoid races
        # and do not touch any user files in ~/.rally
        os.environ["HOME"] = pwd.getpwuid(os.getuid()).pw_dir
        subprocess.call("rally deployment config > /tmp/.rd.json", shell=True)
        self.tmp_dir = tempfile.mkdtemp()
        os.environ["HOME"] = self.tmp_dir
        config_filename = os.path.join(self.tmp_dir, "conf")
        config = ConfigParser.RawConfigParser()
        config.add_section("database")
        config.set("database", "connection", "sqlite:///%s/db" % self.tmp_dir)
        with open(config_filename, "wb") as conf:
            config.write(conf)
        self.args = ["rally", "--config-file", config_filename]
        subprocess.call(["rally-manage", "--config-file", config_filename,
                         "db", "recreate"])
        self("deployment create --file /tmp/.rd.json --name MAIN")

    def __del__(self):
        shutil.rmtree(self.tmp_dir)

    def __call__(self, cmd, getjson=False):
        if not isinstance(cmd, list):
            cmd = cmd.split(" ")
        try:
            output = subprocess.check_output(self.args + cmd,
                                             stderr=subprocess.STDOUT)
            if getjson:
                return json.loads(output)
            return output
        except subprocess.CalledProcessError as e:
            raise RallyCmdError(e.returncode, e.output)


class DeploymentTestCase(unittest.TestCase):

    def test_create_fromenv_list_endpoint(self):
        rally = Rally()
        with mock.patch.dict("os.environ", TEST_ENV):
            rally("deployment create --name t_create --fromenv")
        self.assertIn("t_create", rally("deployment list"))
        self.assertIn(TEST_ENV["OS_AUTH_URL"], rally("deployment endpoint"))


class SLATestCase(unittest.TestCase):

    def _get_sample_task_config(self, max_seconds_per_iteration=4,
                                max_failure_percent=0):
        return {
            "KeystoneBasic.create_and_list_users": [
                {
                    "args": {
                        "name_length": 10
                    },
                    "runner": {
                        "type": "constant",
                        "times": 5,
                        "concurrency": 5
                    },
                    "sla": {
                        "max_seconds_per_iteration": max_seconds_per_iteration,
                        "max_failure_percent": max_failure_percent,
                    }
                }
            ]
        }

    def test_sla_fail(self):
        rally = Rally()
        cfg = self._get_sample_task_config(max_seconds_per_iteration=0.001)
        config = TaskConfig(cfg)
        rally("task start --task %s" % config.filename)
        self.assertRaises(RallyCmdError, rally, "task sla_check")

    def test_sla_success(self):
        rally = Rally()
        config = TaskConfig(self._get_sample_task_config())
        rally("task start --task %s" % config.filename)
        rally("task sla_check")
        expected = [
                {"benchmark": "KeystoneBasic.create_and_list_users",
                 "criterion": "max_seconds_per_iteration",
                 "pos": 0, "success": True},
                {"benchmark": "KeystoneBasic.create_and_list_users",
                 "criterion": "max_failure_percent",
                 "pos": 0, "success": True},
        ]
        data = rally("task sla_check --json", getjson=True)
        self.assertEqual(expected, data)
