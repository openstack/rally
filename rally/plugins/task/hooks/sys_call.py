# Copyright 2016: Mirantis Inc.
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

import json
import shlex
import subprocess

from rally.common import logging
from rally import consts
from rally import exceptions
from rally.task import hook


LOG = logging.getLogger(__name__)


@hook.configure(name="sys_call")
class SysCallHook(hook.HookAction):
    """Performs system call."""

    CONFIG_SCHEMA = {
        "$schema": consts.JSON_SCHEMA,
        "type": "string",
        "description": "Command to execute."
    }

    def run(self):
        LOG.debug("sys_call hook: Running command %s" % self.config)
        proc = subprocess.Popen(shlex.split(self.config),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True)
        out, err = proc.communicate()
        LOG.debug("sys_call hook: Command %s returned %s"
                  % (self.config, proc.returncode))
        if proc.returncode:
            self.set_error(
                exception_name="n/a",  # no exception class
                description="Subprocess returned %s" % proc.returncode,
                details=(err or "stdout: %s" % out))

        # NOTE(amaretskiy): Try to load JSON for charts,
        #                   otherwise save output as-is
        try:
            output = json.loads(out)
            for arg in ("additive", "complete"):
                for out_ in output.get(arg, []):
                    self.add_output(**{arg: out_})
        except (TypeError, ValueError, exceptions.RallyException):
            self.add_output(
                complete={"title": "System call",
                          "chart_plugin": "TextArea",
                          "description": "Args: %s" % self.config,
                          "data": ["RetCode: %i" % proc.returncode,
                                   "StdOut: %s" % (out or "(empty)"),
                                   "StdErr: %s" % (err or "(empty)")]})
