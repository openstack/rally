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

from six.moves import configparser

import json
import os
import pwd
import shutil
import subprocess
import tempfile

TEST_ENV = {
    "OS_USERNAME": "admin",
    "OS_PASSWORD": "admin",
    "OS_TENANT_NAME": "admin",
    "OS_AUTH_URL": "http://fake/",
}

DEPLOYMENT_FILE = "/tmp/rally_functests_main_deployment.json"


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
        config_file.write(json.dumps(config).encode("utf-8"))
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

    def __init__(self, fake=False):
        # NOTE(sskripnick): we shoud change home dir to avoid races
        # and do not touch any user files in ~/.rally
        os.environ["HOME"] = pwd.getpwuid(os.getuid()).pw_dir
        if not os.path.exists(DEPLOYMENT_FILE):
            subprocess.call("rally deployment config > %s" % DEPLOYMENT_FILE,
                            shell=True)
        self.tmp_dir = tempfile.mkdtemp()
        os.environ["HOME"] = self.tmp_dir

        if "RCI_KEEP_DB" not in os.environ:
            config_filename = os.path.join(self.tmp_dir, "conf")
            config = configparser.RawConfigParser()
            config.add_section("database")
            config.set("database", "connection",
                       "sqlite:///%s/db" % self.tmp_dir)
            with open(config_filename, "w") as conf:
                config.write(conf)
            self.args = ["rally", "--config-file", config_filename]
            subprocess.call(["rally-manage", "--config-file", config_filename,
                             "db", "recreate"])
        else:
            self.args = ["rally"]
            subprocess.call(["rally-manage", "db", "recreate"])

        self("deployment create --file %s --name MAIN" % DEPLOYMENT_FILE)

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
            return output.decode("utf-8")
        except subprocess.CalledProcessError as e:
            raise RallyCmdError(e.returncode, e.output)
