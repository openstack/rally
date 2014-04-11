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

import subprocess

from rally.benchmark.context import base
from rally import exceptions
from rally.openstack.common.gettextutils import _
from rally.openstack.common import log as logging
from rally import utils
from rally.verification.verifiers.tempest import tempest

LOG = logging.getLogger(__name__)


class Tempest(base.Context):
    __ctx_name__ = "tempest"
    __ctx_order__ = 666
    __ctx_hidden__ = True

    @utils.log_task_wrapper(LOG.info, _("Enter context: `tempest`"))
    def setup(self):
        self.verifier = tempest.Tempest(self.task.task.deployment_uuid)
        self.verifier.log_file = "/dev/null"

        try:
            if not self.verifier.is_installed():
                self.verifier.install()
            if not self.verifier.is_configured():
                self.verifier.generate_config_file()
        except exceptions.TempestSetupFailure:
            msg = _("Failing to install tempest.")
            LOG.error(msg)
            raise exceptions.BenchmarkSetupFailure(msg)
        except exceptions.TempestConfigCreationFailure:
            msg = _("Failing to configure tempest.")
            LOG.error(msg)
            raise exceptions.BenchmarkSetupFailure(msg)

        self.context["verifier"] = self.verifier

    @utils.log_task_wrapper(LOG.info, _("Exit context: `tempest`"))
    def cleanup(self):
        try:
            cmd = ("cd %(tempest_dir)s "
                   "&& %(venv)s python tempest/stress/tools/cleanup.py" %
                   {
                       "tempest_dir": self.verifier.tempest_path,
                       "venv": self.verifier.venv_wrapper})
            LOG.debug("Cleanup started by the command: %s" % cmd)

            subprocess.check_call(cmd, shell=True, env=self.verifier.env,
                                  cwd=self.verifier.tempest_path)
        except subprocess.CalledProcessError:
            LOG.error("Tempest cleanup failed.")
