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


import logging
import os
import shutil
import subprocess
import sys

from rally import exceptions
from rally.openstack.common.gettextutils import _
from rally.openstack.common import jsonutils
from rally import utils
from rally.verification.verifiers.tempest import config
from rally.verification.verifiers.tempest import subunit2json

LOG = logging.getLogger(__name__)


class Tempest(object):

    tempest_base_path = os.path.join(os.path.expanduser("~"),
                                     ".rally/tempest/base")

    def __init__(self, deploy_id, verification=None, tempest_config=None):
        self.deploy_id = deploy_id
        self.tempest_path = os.path.join(os.path.expanduser("~"),
                                         ".rally/tempest",
                                         "for-deployment-%s" % deploy_id)
        self.config_file = tempest_config or os.path.join(self.tempest_path,
                                                          "tempest.conf")
        self.log_file_raw = os.path.join(self.tempest_path, "subunit.stream")
        self.venv_wrapper = os.path.join(self.tempest_path,
                                         "tools/with_venv.sh")
        self.verification = verification
        self._env = None

    def _generate_env(self):
        env = os.environ.copy()
        env["TEMPEST_CONFIG_DIR"] = os.path.split(self.config_file)[0]
        env["TEMPEST_CONFIG"] = os.path.basename(self.config_file)
        env["OS_TEST_PATH"] = os.path.join(self.tempest_path,
                                           "tempest/test_discover")
        LOG.debug("Generated environ: %s" % env)
        self._env = env

    @property
    def env(self):
        if not self._env:
            self._generate_env()
        return self._env

    def _install_venv(self):
        if not os.path.isdir(os.path.join(self.tempest_path, '.venv')):
            LOG.info('Validating python environment')
            self.validate_env()
            LOG.info("No virtual environment found...Install the virtualenv.")
            LOG.debug("Virtual environment directory: %s" %
                      os.path.join(self.tempest_path, ".venv"))
            subprocess.check_call("python ./tools/install_venv.py", shell=True,
                                  cwd=self.tempest_path)
            subprocess.check_call(
                "%s python setup.py install" % self.venv_wrapper,
                shell=True, cwd=self.tempest_path)

    def is_configured(self):
        return os.path.isfile(self.config_file)

    def generate_config_file(self):
        """Generate configuration file of tempest for current deployment."""

        LOG.debug("Tempest config file: %s " % self.config_file)
        if not self.is_configured():
            msg = _("Creation of configuration file for tempest.")
            LOG.info(_("Starting: ") + msg)

            config.TempestConf(self.deploy_id).generate(self.config_file)
            LOG.info(_("Completed: ") + msg)
        else:
            LOG.info("Tempest is already configured.")

    def _initialize_testr(self):
        if not os.path.isdir(os.path.join(self.tempest_path,
                                          ".testrepository")):
            msg = _("Test Repository initialization.")
            LOG.info(_("Starting: ") + msg)
            subprocess.check_call("%s testr init" % self.venv_wrapper,
                                  shell=True, cwd=self.tempest_path)
            LOG.info(_("Completed: ") + msg)

    def is_installed(self):
        return os.path.exists(os.path.join(self.tempest_path, ".venv"))

    @staticmethod
    def _clone():
        print("Please wait while tempest is being cloned. "
              "This could take a few minutes...")
        subprocess.check_call(["git", "clone",
                               "https://github.com/openstack/tempest",
                               Tempest.tempest_base_path])

    def install(self):
        if not self.is_installed():
            try:
                if not os.path.exists(Tempest.tempest_base_path):
                    Tempest._clone()

                if not os.path.exists(self.tempest_path):
                    shutil.copytree(Tempest.tempest_base_path,
                                    self.tempest_path)
                    subprocess.check_call("git checkout master; "
                                          "git remote update; "
                                          "git pull", shell=True,
                                          cwd=os.path.join(self.tempest_path,
                                                           "tempest"))
                self._install_venv()
                self._initialize_testr()
            except subprocess.CalledProcessError as e:
                self.uninstall()
                raise exceptions.TempestSetupFailure("failed cmd: '%s'", e.cmd)
            else:
                print("Tempest has been successfully installed!")

        else:
            print("Tempest is already installed")

    def uninstall(self):
        if os.path.exists(self.tempest_path):
            shutil.rmtree(self.tempest_path)

    @utils.log_verification_wrapper(LOG.info, _("Run verification."))
    def _prepare_and_run(self, set_name, regex):
        if not self.is_configured():
            self.generate_config_file()

        if set_name == "full":
            testr_arg = ""
        elif set_name == "smoke":
            testr_arg = "smoke"
        else:
            if set_name:
                testr_arg = "tempest.api.%s" % set_name
            elif regex:
                testr_arg = regex
            else:
                testr_arg = ""

        self.verification.start_verifying(set_name)
        try:
            self.run(testr_arg)
        except subprocess.CalledProcessError:
            print("Test set %s has been finished with error. "
                  "Check log for details" % set_name)

    def run(self, testr_arg=None, log_file=None):
        """Launch tempest with given arguments

        :param testr_arg: argument which will be transmitted into testr
        :type testr_arg: str
        :param log_file: file name for raw subunit results of tests. If not
                         specified, value from "self.log_file_raw"
                         will be chosen.
        :type testr_arg: str

        :raises: :class:`subprocess.CalledProcessError` if tests has been
                 finished with error.
        """

        test_cmd = (
            "%(venv)s testr run --parallel --subunit %(arg)s "
            "| tee %(log_file)s "
            "| %(venv)s subunit-2to1 "
            "| %(venv)s %(tempest_path)s/tools/colorizer.py" %
            {
                "venv": self.venv_wrapper,
                "arg": testr_arg,
                "tempest_path": self.tempest_path,
                "log_file": log_file or self.log_file_raw
            })
        LOG.debug("Test(s) started by the command: %s" % test_cmd)
        subprocess.check_call(test_cmd, cwd=self.tempest_path,
                              env=self.env, shell=True)

    def discover_tests(self, pattern=""):
        """Return a set of discovered tests which match given pattern."""

        cmd = "%(venv)s testr list-tests %(pattern)s" % {
            "venv": self.venv_wrapper,
            "pattern": pattern}
        raw_results = subprocess.Popen(
            cmd, shell=True, cwd=self.tempest_path, env=self.env,
            stdout=subprocess.PIPE).communicate()[0]

        tests = set()
        for test in raw_results.split('\n'):
            if test.startswith("tempest."):
                index = test.find("[")
                if index != -1:
                    tests.add(test[:index])
                else:
                    tests.add(test)

        return tests

    @staticmethod
    def parse_results(log_file_raw):
        """Parse subunit raw log file."""

        if os.path.isfile(log_file_raw):
            data = jsonutils.loads(subunit2json.main(log_file_raw))
            return data['total'], data['test_cases']
        else:
            LOG.error("JSON-log file not found.")
            return None, None

    @utils.log_verification_wrapper(
        LOG.info, _("Saving verification results."))
    def _save_results(self):
        total, test_cases = self.parse_results(self.log_file_raw)
        if total and test_cases and self.verification:
            self.verification.finish_verification(total=total,
                                                  test_cases=test_cases)

    def validate_env(self):
        """Validate environment parameters required for running tempest.

           eg: python>2.7
        """

        if sys.version_info < (2, 7):
            raise exceptions.IncompatiblePythonVersion(
                                                    version=sys.version_info)

    def verify(self, set_name, regex):
        self._prepare_and_run(set_name, regex)
        self._save_results()
