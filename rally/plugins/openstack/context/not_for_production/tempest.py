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
import tempfile

from rally.common.i18n import _
from rally.common import logging
from rally import consts
from rally import exceptions
from rally.task import context
from rally.verification.tempest import tempest

LOG = logging.getLogger(__name__)


@context.configure(name="tempest", order=666)
class Tempest(context.Context):
    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "source": {"type": "string"},
            "tempest-config": {"type": "string"}
        },
    }

    def __init__(self, context):
        super(Tempest, self).__init__(context)
        self.results_dir = os.path.join(
            tempfile.gettempdir(), "%s-results" % self.task.task.uuid)
        self.verifier = tempest.Tempest(self.task["deployment_uuid"],
                                        source=self.config.get("source"),
                                        tempest_config=self.config.get(
                                            "tempest-config"))

    @logging.log_task_wrapper(LOG.info, _("Enter context: `tempest`"))
    def setup(self):
        self.verifier.log_file_raw = "/dev/null"
        # Create temporary directory for subunit-results.
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
        except exceptions.TempestConfigCreationFailure:
            msg = _("Failing to configure tempest.")
            LOG.error(msg)
            raise exceptions.BenchmarkSetupFailure(msg)

        self.context["verifier"] = self.verifier

    @logging.log_task_wrapper(LOG.info, _("Exit context: `tempest`"))
    def cleanup(self):
        LOG.info("Built-in stress cleanup from Tempest looks like can help to "
                 "shot yourself in the foot. Sorry, but even Rally can not "
                 "clean up after Tempest. Deal with it.")
        if os.path.exists(self.results_dir):
            shutil.rmtree(self.results_dir)
