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

from rally.benchmark.context import base
from rally.common.i18n import _
from rally.common import utils
from rally import exceptions
from rally import log as logging
from rally.verification.tempest import config
from rally.verification.tempest import tempest

LOG = logging.getLogger(__name__)


@base.context(name="tempest", order=666, hidden=True)
class Tempest(base.Context):
    @utils.log_task_wrapper(LOG.info, _("Enter context: `tempest`"))
    def setup(self):
        self.verifier = tempest.Tempest(self.task.task.deployment_uuid)
        self.verifier.log_file_raw = "/dev/null"
        # Create temporary directory for subunit-results.
        self.results_dir = os.path.join(
            tempfile.gettempdir(), "%s-results" % self.task.task.uuid)
        os.mkdir(self.results_dir)
        self.context["tmp_results_dir"] = self.results_dir

        try:
            if not self.verifier.is_installed():
                self.verifier.install()
            if not self.verifier.is_configured():
                self.verifier.generate_config_file()
        except tempest.TempestSetupFailure:
            msg = _("Failing to install tempest.")
            LOG.error(msg)
            raise exceptions.BenchmarkSetupFailure(msg)
        except config.TempestConfigCreationFailure:
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
                       "tempest_dir": self.verifier.path,
                       "venv": self.verifier.venv_wrapper})
            LOG.debug("Cleanup started by the command: %s" % cmd)

            subprocess.check_call(cmd, shell=True, env=self.verifier.env,
                                  cwd=self.verifier.path)
        except subprocess.CalledProcessError:
            LOG.error("Tempest cleanup failed.")

        if os.path.exists(self.results_dir):
            shutil.rmtree(self.results_dir)
