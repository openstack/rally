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
import re
import shutil
import subprocess
import sys
import tempfile

from oslo_utils import encodeutils

from rally.common.i18n import _
from rally.common.io import subunit_v2
from rally.common import logging
from rally import consts
from rally import exceptions
from rally.verification.tempest import config


TEMPEST_SOURCE = "https://git.openstack.org/openstack/tempest"

LOG = logging.getLogger(__name__)


class TempestSetupFailure(exceptions.RallyException):
    msg_fmt = _("Unable to setup Tempest: %(message)s")


def check_output(*args, **kwargs):
    debug = kwargs.pop("debug", True)
    kwargs["stderr"] = subprocess.STDOUT
    try:
        output = subprocess.check_output(*args, **kwargs)
    except subprocess.CalledProcessError as e:
        LOG.error("Failed cmd: '%s'" % e.cmd)
        LOG.error("Error output: '%s'" % encodeutils.safe_decode(e.output))
        raise

    if debug:
        LOG.debug("Subprocess output: '%s'" % encodeutils.safe_decode(output))

    return output


class Tempest(object):

    base_repo_dir = os.path.join(os.path.expanduser("~"),
                                 ".rally/tempest/base")

    def __init__(self, deployment, verification=None, tempest_config=None,
                 source=None, version=None, plugin_source=None,
                 plugin_version=None, system_wide=False):
        self.deployment = deployment
        self.verification = verification
        self._path = os.path.join(os.path.expanduser("~"),
                                  ".rally/tempest",
                                  "for-deployment-%s" % deployment)
        self.config_file = tempest_config or self.path("tempest.conf")
        self.tempest_source = source or TEMPEST_SOURCE
        self.version = version
        self.plugin_source = plugin_source
        self.plugin_version = plugin_version
        self.log_file_raw = self.path("subunit.stream")

        self._env = None
        self._base_repo = None
        self._system_wide = system_wide

    def _generate_env(self):
        env = os.environ.copy()
        env["TEMPEST_CONFIG_DIR"] = os.path.dirname(self.config_file)
        env["TEMPEST_CONFIG"] = os.path.basename(self.config_file)
        env["OS_TEST_PATH"] = self.path("tempest/test_discover")
        LOG.debug("Generated environ: %s" % env)
        self._env = env

    @property
    def venv_wrapper(self):
        if self._system_wide:
            return ""
        else:
            return self.path("tools/with_venv.sh")

    @property
    def env(self):
        if not self._env:
            self._generate_env()
        return self._env

    def path(self, *inner_path):
        if inner_path:
            return os.path.join(self._path, *inner_path)
        return self._path

    @staticmethod
    def _is_git_repo(directory):
        # will suppress git output
        with open(os.devnull, "w") as devnull:
            return os.path.isdir(directory) and not subprocess.call(
                ["git", "status"], stdout=devnull, stderr=subprocess.STDOUT,
                cwd=os.path.abspath(directory))

    @staticmethod
    def _move_contents_to_dir(base, directory):
        """Moves contents of directory :base into directory :directory

        :param base: source directory to move files from
        :param directory: directory to move files to
        """
        for filename in os.listdir(base):
            source = os.path.join(base, filename)
            LOG.debug("Moving file {source} to {dest}".format(source=source,
                                                              dest=directory))
            shutil.move(source, os.path.join(directory, filename))

    @property
    def base_repo(self):
        """Get directory to clone tempest to

        old:
            _ rally/tempest
            |_base -> clone from source to here
            |_for-deployment-<UUID1> -> copy from relevant tempest base
            |_for-deployment-<UUID2> -> copy from relevant tempest base

        new:
            _ rally/tempest
            |_base
            ||_ tempest_base-<rand suffix specific for source> -> clone
            ||        from source to here
            ||_ tempest_base-<rand suffix 2>
            |_for-deployment-<UUID1> -> copy from relevant tempest base
            |_for-deployment-<UUID2> -> copy from relevant tempest base

        """
        if os.path.exists(Tempest.base_repo_dir):
            if self._is_git_repo(Tempest.base_repo_dir):
                # this is the old dir structure and needs to be upgraded
                directory = tempfile.mkdtemp(prefix=os.path.join(
                    Tempest.base_repo_dir, "tempest_base-"))
                LOG.debug("Upgrading Tempest directory tree: "
                          "Moving Tempest base dir %s into subdirectory %s" %
                          (Tempest.base_repo_dir, directory))
                self._move_contents_to_dir(Tempest.base_repo_dir,
                                           directory)
            if not self._base_repo:
                # Search existing tempest bases for a matching source
                repos = [d for d in os.listdir(Tempest.base_repo_dir)
                         if self._is_git_repo(d) and
                         self.tempest_source == self._get_remote_origin(d)]
                if len(repos) > 1:
                    raise exceptions.MultipleMatchesFound(
                        needle="git directory",
                        haystack=repos)
                if repos:
                    # Use existing base with relevant source
                    self._base_repo = repos.pop()
        else:
            os.makedirs(Tempest.base_repo_dir)
        if not self._base_repo:
            self._base_repo = tempfile.mkdtemp(prefix=os.path.join(
                os.path.abspath(Tempest.base_repo_dir), "tempest_base-"))
        return self._base_repo

    @staticmethod
    def _get_remote_origin(directory):
        out = check_output(["git", "config", "--get", "remote.origin.url"],
                           cwd=os.path.abspath(directory))
        return out.strip()

    def _install_venv(self):
        path_to_venv = self.path(".venv")

        if not os.path.isdir(path_to_venv):
            LOG.debug("No virtual environment for Tempest found.")
            LOG.info(_("Installing the virtual environment for Tempest."))
            LOG.debug("Virtual environment directory: %s" % path_to_venv)
            try:
                check_output(["virtualenv", "-p", sys.executable, ".venv"],
                             cwd=self.path())
                # NOTE(kun): Using develop mode installation is for running
                #            multiple Tempest instances.
                check_output([self.venv_wrapper, "pip", "install", "-e", "./"],
                             cwd=self.path())
            except subprocess.CalledProcessError:
                if os.path.exists(self.path(".venv")):
                    shutil.rmtree(self.path(".venv"))
                raise TempestSetupFailure(_("Failed to install virtualenv."))

    def is_configured(self):
        return os.path.isfile(self.config_file)

    def generate_config_file(self, extra_conf=None, override=False):
        """Generate Tempest configuration file for the current deployment.

        :param extra_conf: A ConfigParser() object with options to
                           extend/update Tempest config file
        :param override: Whether or not to override existing Tempest
                         config file
        """
        if not self.is_configured() or override:
            if not override:
                LOG.info(_("Tempest is not configured "
                           "for deployment: %s") % self.deployment)

            LOG.info(_("Creating Tempest configuration "
                       "file for deployment: %s") % self.deployment)
            conf = config.TempestConfig(self.deployment)
            conf.generate(self.config_file, extra_conf)
            LOG.info(_("Tempest configuration file "
                       "has been successfully created!"))
        else:
            LOG.info(_("Tempest is already configured "
                       "for deployment: %s") % self.deployment)

    def _initialize_testr(self):
        if not os.path.isdir(self.path(".testrepository")):
            LOG.debug("Initialization of 'testr'.")
            cmd = ["testr", "init"]
            if self.venv_wrapper:
                cmd.insert(0, self.venv_wrapper)
            try:
                check_output(cmd, cwd=self.path())
            except (subprocess.CalledProcessError, OSError):
                if os.path.exists(self.path(".testrepository")):
                    shutil.rmtree(self.path(".testrepository"))
                raise TempestSetupFailure(_("Failed to initialize 'testr'"))

    def is_installed(self):
        if self._system_wide:
            return os.path.exists(self.path(".testrepository"))

        return os.path.exists(self.path(".venv")) and os.path.exists(
            self.path(".testrepository"))

    def _clone(self):
        LOG.info(_("Please, wait while Tempest is being cloned."))
        try:
            subprocess.check_call(["git", "clone",
                                   self.tempest_source,
                                   self.base_repo])
        except subprocess.CalledProcessError:
            if os.path.exists(self.base_repo):
                shutil.rmtree(self.base_repo)
            raise

    def install(self):
        """Creates local Tempest repo and virtualenv for deployment."""
        if not self.is_installed():
            LOG.info(_("Tempest is not installed "
                       "for deployment: %s") % self.deployment)
            LOG.info(_("Installing Tempest "
                       "for deployment: %s") % self.deployment)
            try:
                if not os.path.exists(self.path()):
                    if not self._is_git_repo(self.base_repo):
                        self._clone()
                    shutil.copytree(self.base_repo, self.path())

                if self.version:
                    check_output(["git", "checkout", self.version],
                                 cwd=self.path())

                if not self._system_wide:
                    self._install_venv()

                self._initialize_testr()
            except subprocess.CalledProcessError as e:
                self.uninstall()
                raise TempestSetupFailure("Failed cmd: '%s'" % e.cmd)
            else:
                LOG.info(_("Tempest has been successfully installed!"))
        else:
            LOG.info(_("Tempest is already installed."))

    def uninstall(self):
        """Removes local Tempest repo and virtualenv for deployment

         Checks that local repo exists first.
        """
        if os.path.exists(self.path()):
            shutil.rmtree(self.path())

    def install_plugin(self):
        """Install Tempest plugin for local Tempest repo."""
        LOG.info(_("Installing Tempest plugin from %s for "
                   "deployment: %s") % (self.plugin_source, self.deployment))
        egg = re.sub("\.git$", "",
                     os.path.basename(self.plugin_source.strip("/")))
        version = self.plugin_version or "master"
        cmd = ["pip", "install", "--no-deps",
               "--src", self.path("plugins/system-wide"), "-e",
               "git+{0}@{1}#egg={2}".format(self.plugin_source, version, egg)]
        if not self._system_wide:
            cmd.remove("--no-deps")
            cmd.remove(self.path("plugins/system-wide"))
            cmd.insert(0, self.path("tools/with_venv.sh"))
            cmd.insert(4, self.path("plugins"))
        check_output(cmd, cwd=self.path())
        LOG.info(_("Tempest plugin has been successfully installed!"))

    def list_plugins(self):
        """List all installed Tempest plugins for local Tempest repo."""
        cmd_list_plugins = ["tempest", "list-plugins"]
        if not self._system_wide:
            cmd_list_plugins.insert(0, self.path("tools/with_venv.sh"))
        else:
            cmd_pip_list = ["pip", "list"]
            if "tempest" not in check_output(cmd_pip_list,
                                             cwd=self.path(), debug=False):
                return _("Cannot list Tempest plugins because Tempest "
                         "package is not installed in your environment. "
                         "Please, install Tempest package and try again.")

        return check_output(cmd_list_plugins, cwd=self.path(), debug=False)

    def uninstall_plugin(self, repo_name):
        """Uninstall Tempest plugin for local Tempest repo."""
        repo_path = self.path("plugins/system-wide/%s" % repo_name)
        if not self._system_wide:
            repo_path = self.path("plugins/%s" % repo_name)
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path)

    @logging.log_verification_wrapper(LOG.info, _("Run verification."))
    def _prepare_and_run(self, set_name, regex, tests_file,
                         tests_file_to_skip, concur, failing):
        if not self.is_configured():
            self.generate_config_file()

        testr_args = ""

        if failing:
            testr_args = "--failing"
            set_name = "re-run-failed"
        elif set_name:
            if set_name == "full":
                pass
            elif set_name in consts.TempestTestsSets:
                testr_args = set_name
            elif set_name in consts.TempestTestsAPI:
                testr_args = "tempest.api.%s" % set_name
        elif regex:
            testr_args = regex
        elif tests_file:
            testr_args = "--load-list %s" % os.path.abspath(tests_file)

        if tests_file_to_skip and not tests_file:
            tests_to_run = set(self.discover_tests(testr_args))
            with open(os.path.abspath(tests_file_to_skip), "rb") as f:
                tests_to_skip = set([line.strip() for line in f])
            tests_to_run -= tests_to_skip

            temp_file = tempfile.NamedTemporaryFile()
            with open(temp_file.name, "wb") as f:
                f.writelines("\n".join(tests_to_run))

            testr_args = "--load-list %s" % temp_file.name

        self.verification.start_verifying(set_name)
        try:
            self.run(testr_args, concur=concur)
        except subprocess.CalledProcessError:
            LOG.info(_("Test run has been finished with errors. "
                       "Check logs for details."))

    def run(self, testr_args="", log_file=None, tempest_conf=None, concur=0):
        """Run Tempest.

        :param testr_args: Arguments which will be passed to testr
        :param log_file: Path to a file for raw subunit stream logs.
                         If not specified, the value from "self.log_file_raw"
                         will be used as the path to the file
        :param tempest_conf: User specified Tempest config file location
        :param concur: How many processes to use to run Tempest tests.
                       The default value (0) auto-detects CPU count
        """
        if tempest_conf:
            self.config_file = tempest_conf
        if os.path.isfile(self.config_file):
            LOG.info(_("Using Tempest config file: %s") % self.config_file)
        else:
            msg = _("Tempest config file '%s' not found!") % self.config_file
            LOG.error(msg)
            raise exceptions.NotFoundException(message=msg)

        concur_args = "--concurrency %d" % concur
        if concur != 1:
            concur_args = "--parallel %s" % concur_args

        test_cmd = (
            "%(venv)s testr run --subunit %(concur_args)s %(testr_args)s "
            "| tee %(log_file)s "
            "| %(venv)s subunit-trace -f -n" %
            {
                "venv": self.venv_wrapper,
                "concur_args": concur_args,
                "testr_args": testr_args,
                "log_file": log_file or self.log_file_raw
            })
        # Discover or create all resources needed for Tempest before running
        # tests. Once tests finish, all created resources will be deleted.
        with config.TempestResourcesContext(
                self.deployment, self.verification, self.config_file):
            # Run tests
            LOG.debug("Test(s) started by the command: %s" % test_cmd)
            subprocess.check_call(test_cmd, cwd=self.path(),
                                  env=self.env, shell=True)

    def discover_tests(self, pattern=""):
        """Get a list of discovered tests.

        :param pattern: Test name pattern which can be used to match
        """
        cmd = ["testr", "list-tests", pattern]
        if not self._system_wide:
            cmd.insert(0, self.path("tools/with_venv.sh"))
        raw_results = subprocess.Popen(
            cmd, cwd=self.path(), env=self.env,
            stdout=subprocess.PIPE).communicate()[0]
        index = raw_results.find("tempest.")
        return raw_results[index:].split()

    def parse_results(self, log_file=None, expected_failures=None):
        """Parse subunit raw log file."""
        log_file_raw = log_file or self.log_file_raw
        if os.path.isfile(log_file_raw):
            return subunit_v2.parse_results_file(log_file_raw,
                                                 expected_failures)
        else:
            LOG.error("JSON-log file not found.")
            return None

    @logging.log_verification_wrapper(
        LOG.info, _("Saving verification results."))
    def _save_results(self, log_file=None, expected_failures=None):
        results = self.parse_results(log_file, expected_failures)
        if results and self.verification:
            self.verification.finish_verification(total=results.total,
                                                  test_cases=results.tests)
        else:
            self.verification.set_failed()

    def verify(self, set_name, regex, tests_file,
               tests_file_to_skip, expected_failures, concur, failing):
        self._prepare_and_run(set_name, regex, tests_file,
                              tests_file_to_skip, concur, failing)
        self._save_results(expected_failures=expected_failures)

    def import_results(self, set_name, log_file):
        if log_file:
            self.verification.start_verifying(set_name)
            self._save_results(log_file)
        else:
            LOG.error("No log file to import results was specified.")
