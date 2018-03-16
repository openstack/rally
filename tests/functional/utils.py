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

import copy
import errno
import inspect
import json
import os
import shutil
import subprocess
import tempfile

from six.moves import configparser

from rally.utils import encodeutils


class RallyCliError(Exception):

    def __init__(self, cmd, code, output):
        self.command = cmd
        self.code = code
        self.output = encodeutils.safe_decode(output)
        self.msg = "Command: %s Code: %d Output: %s\n" % (self.command,
                                                          self.code,
                                                          self.output)

    def __str__(self):
        return self.msg

    def __unicode__(self):
        return self.msg


class JsonTempFile(object):

    def __init__(self, config):
        config_file = tempfile.NamedTemporaryFile(delete=False)
        config_file.write(encodeutils.safe_encode(json.dumps(config)))
        config_file.close()
        self.filename = config_file.name

    def __del__(self):
        os.unlink(self.filename)


class TaskConfig(JsonTempFile):
    pass


class Rally(object):
    """Create and represent separate rally installation.

    Usage:

        rally = Rally()
        rally("deployment", "create", "--name", "Some Deployment Name")
        output = rally("deployment list")

    """
    _DEPLOYMENT_CREATE_ARGS = ""

    def __init__(self, force_new_db=False, plugin_path=None):

        # NOTE(sskripnick): we should change home dir to avoid races
        # and do not touch any user files in ~/.rally
        self.tmp_dir = tempfile.mkdtemp()
        self.env = copy.deepcopy(os.environ)
        self.env["HOME"] = self.tmp_dir
        self.config_filename = None
        self.method_name = None
        self.class_name = None

        caller_frame = inspect.currentframe().f_back
        if caller_frame.f_code.co_name == "__call__":
            caller_frame = caller_frame.f_back

        self.method_name = caller_frame.f_code.co_name
        if self.method_name == "setUp":
            raise Exception("No rally instance should be generated in "
                            "setUp method")

        test_object = caller_frame.f_locals["self"]
        self.class_name = test_object.__class__.__name__

        if force_new_db or ("RCI_KEEP_DB" not in os.environ):
            config_filename = os.path.join(self.tmp_dir, "conf")
            config = configparser.RawConfigParser()
            config.add_section("database")
            config.set("database", "connection",
                       "sqlite:///%s/db" % self.tmp_dir)
            with open(config_filename, "w") as conf:
                config.write(conf)
            self.args = ["rally", "--config-file", config_filename]
            subprocess.call(["rally", "--config-file", config_filename,
                             "db", "recreate"], env=self.env)
            self.config_filename = config_filename
        else:
            self.args = ["rally"]
            subprocess.call(["rally", "db", "recreate"], env=self.env)

        if plugin_path:
            self.args.extend(["--plugin-paths", os.path.abspath(plugin_path)])
        self.reports_root = os.environ.get("REPORTS_ROOT",
                                           "rally-cli-output-files")
        self._created_files = []
        self("deployment create --name MAIN%s" % self._DEPLOYMENT_CREATE_ARGS,
             write_report=False)

    def __del__(self):
        shutil.rmtree(self.tmp_dir)

    def _safe_make_dirs(self, dirs):
        try:
            os.makedirs(dirs)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(dirs):
                pass
            else:
                raise

    def gen_report_path(self, suffix=None, extension=None, keep_old=False):
        """Report file path/name modifier

        :param suffix: suffix that will be appended to filename.
            It will be appended before extension
        :param extension: file extension.
        :param keep_old: if True, previous reports will not be deleted,
            but rename to 'nameSuffix.old*.extension'

        :return: complete report name to write report
        """

        self._safe_make_dirs("%s/%s" % (self.reports_root, self.class_name))

        suff = suffix or ""
        ext = extension or "txt"
        path = "%s/%s/%s%s.%s" % (self.reports_root, self.class_name,
                                  self.method_name, suff, ext)

        if path not in self._created_files:
            if os.path.exists(path):
                if not keep_old:
                    os.remove(path)
                else:
                    path_list = path.split(".")
                    old_suff = "old"
                    path_list.insert(-1, old_suff)
                    new_path = ".".join(path_list)
                    count = 0
                    while os.path.exists(new_path):
                        count += 1
                        path_list[-2] = "old%d" % count
                        new_path = ".".join(path_list)
                    os.rename(path, new_path)

            self._created_files.append(path)
        return path

    def __call__(self, cmd, getjson=False, report_path=None, raw=False,
                 suffix=None, extension=None, keep_old=False,
                 write_report=True, no_logs=False):
        """Call rally in the shell

        :param cmd: rally command
        :param getjson: in cases, when rally prints JSON, you can catch output
            deserialized
        :param report_path: if present, rally command and its output will be
            written to file with passed file name
        :param raw: don't write command itself to report file. Only output
            will be written
        """

        if not isinstance(cmd, list):
            cmd = cmd.split(" ")
        try:
            if no_logs or getjson:
                cmd = self.args + ["--log-file", "/dev/null"] + cmd
                with open(os.devnull, "w") as DEVNULL:
                    output = encodeutils.safe_decode(subprocess.check_output(
                        cmd, stderr=DEVNULL, env=self.env))
            else:
                cmd = self.args + cmd
                output = encodeutils.safe_decode(subprocess.check_output(
                    cmd, stderr=subprocess.STDOUT, env=self.env))

            if getjson:
                return json.loads(output)

            return output

        except subprocess.CalledProcessError as e:
            output = e.output
            raise RallyCliError(cmd, e.returncode, e.output)
        finally:
            if write_report:
                if not report_path:
                    report_path = self.gen_report_path(
                        suffix=suffix, extension=extension, keep_old=keep_old)
                with open(report_path, "a") as rep:
                    if not raw:
                        rep.write("\n%s:\n" % " ".join(cmd))
                    rep.write("%s\n" % output)


def get_global(global_key, env):
    home_dir = env.get("HOME")
    with open("%s/.rally/globals" % home_dir) as f:
        for line in f.readlines():
            if line.startswith("%s=" % global_key):
                key, value = line.split("=")
                return value.rstrip()
    return ""
