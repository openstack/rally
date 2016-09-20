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

import shlex
import subprocess

from rally.common import logging
from rally import consts
from rally.task import hook


LOG = logging.getLogger(__name__)


@hook.configure(name="sys_call")
class SysCallHook(hook.Hook):
    """Performs system call."""

    CONFIG_SCHEMA = {
        "$schema": consts.JSON_SCHEMA,
        "type": "string",
    }

    def run(self):
        LOG.debug("sys_call hook: Running command %s", self.config)
        proc = subprocess.Popen(shlex.split(self.config),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        proc.wait()
        LOG.debug("sys_call hook: Command %s returned %s",
                  self.config, proc.returncode)

        if proc.returncode == 0:
            self.set_status(consts.HookStatus.SUCCESS)
        else:
            self.set_error(
                exception_name="n/a",  # no exception class
                description="Subprocess returned {}".format(proc.returncode),
                details=proc.stdout.read().decode(),
            )
