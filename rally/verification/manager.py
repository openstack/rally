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

import abc
import os
import shutil
import sys

import six

from rally.common.i18n import _LE, _LI
from rally.common.io import subunit_v2
from rally.common import logging
from rally.common.plugin import plugin
from rally import exceptions
from rally.verification import context
from rally.verification import utils


LOG = logging.getLogger(__name__)


class VerifierSetupFailure(exceptions.RallyException):
    msg_fmt = "Failed to set up verifier '%(verifier)s': %(message)s"


def configure(name, namespace="default", default_repo=None,
              default_version=None, context=None):
    """Decorator to configure plugin's attributes.

    :param name: Plugin name that is used for searching purpose
    :param namespace: Plugin namespace
    :param default_repo: Default repository to clone
    :param default_version: Default version to checkout
    :param context: List of contexts that should be executed for verification
    """
    def decorator(plugin):
        plugin._configure(name, namespace)
        plugin._meta_set("default_repo", default_repo)
        plugin._meta_set("default_version", default_version)
        plugin._meta_set("context", context or {})
        return plugin

    return decorator


@plugin.base()
@six.add_metaclass(abc.ABCMeta)
class VerifierManager(plugin.Plugin):

    def __init__(self, verifier):
        """Init a verifier manager.

        :param verifier: `rally.common.objects.verifier.Verifier` instance
        """
        self.verifier = verifier

    @property
    def base_dir(self):
        return os.path.expanduser(
            "~/.rally/verification/verifier-%s" % self.verifier.uuid)

    @property
    def home_dir(self):
        return os.path.join(self.base_dir, "for-deployment-%s"
                            % self.verifier.deployment["uuid"])

    @property
    def repo_dir(self):
        return os.path.join(self.base_dir, "repo")

    @property
    def venv_dir(self):
        return os.path.join(self.base_dir, ".venv")

    @property
    def environ(self):
        env = os.environ.copy()
        if not self.verifier.system_wide:
            # activate virtual environment
            env["VIRTUAL_ENV"] = self.venv_dir
            env["PATH"] = "%s:%s" % (
                os.path.join(self.venv_dir, "bin"), env["PATH"])
        return env

    def validate_args(self, args):
        """Validate given arguments."""

        # NOTE(andreykurilin): By default we do not use jsonschema here.
        # So it cannot be extended by inheritors => requires duplication.
        if "pattern" in args:
            if not isinstance(args["pattern"], six.string_types):
                raise exceptions.ValidationError(
                    "'pattern' argument should be a string.")
        if "concurrency" in args:
            if (not isinstance(args["concurrency"], int) or
                    args["concurrency"] < 0):
                raise exceptions.ValidationError(
                    "'concurrency' argument should be a positive integer or "
                    "zero.")
        if "load_list" in args:
            if not isinstance(args["load_list"], list):
                raise exceptions.ValidationError(
                    "'load_list' argument should be a list of tests.")
        if "skip_list" in args:
            if not isinstance(args["skip_list"], dict):
                raise exceptions.ValidationError(
                    "'skip_list' argument should be a dict of tests "
                    "where keys are test names and values are reasons.")
        if "xfail_list" in args:
            if not isinstance(args["xfail_list"], dict):
                raise exceptions.ValidationError(
                    "'xfail_list' argument should be a dict of tests "
                    "where keys are test names and values are reasons.")

    def validate(self, run_args):
        context.ContextManager.validate(self._meta_get("context"))
        self.validate_args(run_args)

    def _clone(self):
        """Clone a repo and switch to a certain version."""
        source = self.verifier.source or self._meta_get("default_repo")
        if logging.is_debug():
            LOG.debug("Cloning verifier repo from %s into %s.", source,
                      self.repo_dir)
        else:
            LOG.info("Cloning verifier repo from %s.", source)
        utils.check_output(["git", "clone", source, self.repo_dir])

        version = self.verifier.version or self._meta_get("default_version")
        if version and version != "master":
            LOG.info("Switching verifier repo to the '%s' version." % version)
            utils.check_output(["git", "checkout", version], cwd=self.repo_dir)

    def install(self):
        """Install a verifier."""
        utils.create_dir(self.base_dir)

        self._clone()

        if self.verifier.system_wide:
            self.check_system_wide()
        else:
            self.install_venv()

    def uninstall(self, full=False):
        """Uninstall a verifier.

        :param full: If False, only deployment-specific data will be removed
        """
        path = self.base_dir if full else self.home_dir
        if os.path.exists(path):
            shutil.rmtree(path)

    def install_venv(self):
        """Install a virtual environment for a verifier."""
        if os.path.exists(self.venv_dir):
            # NOTE(andreykurilin): It is necessary to remove the old env while
            #                      performing update action.
            LOG.info("Deleting old virtual environment.")
            shutil.rmtree(self.venv_dir)

        LOG.info("Creating virtual environment. It may take a few minutes.")

        LOG.debug("Initializing virtual environment in %s directory.",
                  self.venv_dir)
        utils.check_output(["virtualenv", "-p", sys.executable, self.venv_dir],
                           cwd=self.repo_dir,
                           msg_on_err="Failed to initialize virtual env "
                                      "in %s directory." % self.venv_dir)

        LOG.debug("Installing verifier in virtual environment.")
        # NOTE(ylobankov): Use 'develop mode' installation to provide an
        #                  ability to advanced users to change tests or
        #                  develop new ones in verifier repo on the fly.
        utils.check_output(["pip", "install", "-e", "./"],
                           cwd=self.repo_dir, env=self.environ)

    def check_system_wide(self, reqs_file_path=None):
        """Check that all required verifier packages are installed."""
        LOG.debug("Checking system-wide packages for verifier.")
        import pip
        reqs_file_path = reqs_file_path or os.path.join(self.repo_dir,
                                                        "requirements.txt")
        required_packages = set(
            [r.name.lower() for r in pip.req.parse_requirements(
                reqs_file_path, session=False)])
        installed_packages = set(
            [r.key for r in pip.get_installed_distributions()])
        missed_packages = required_packages - installed_packages
        if missed_packages:
            raise VerifierSetupFailure(
                "Missed package(s) for system-wide installation found. "
                "Please install '%s'." % "', '".join(sorted(missed_packages)),
                verifier=self.verifier.name)

    def checkout(self, version):
        """Switch a verifier repo."""
        LOG.info("Switching verifier repo to the '%s' version.", version)
        utils.check_output(["git", "checkout", "master"], cwd=self.repo_dir)
        utils.check_output(["git", "remote", "update"], cwd=self.repo_dir)
        utils.check_output(["git", "pull"], cwd=self.repo_dir)
        utils.check_output(["git", "checkout", version], cwd=self.repo_dir)

    def configure(self, extra_options=None):
        """Configure a verifier."""
        # NOTE(andreykurilin): Verifier may not require any kind of
        #   configuration and works with cli arguments or with environment
        #   variables. Since we do not store anywhere information about require
        #   verifier configuration or not and we have hardcoded calls to
        #   configure from different places, let's do not raise
        #   NotImplementedError by default. Only do it in case of extra options
        if extra_options is not None:
            raise NotImplementedError(
                _LE("'%s' verifiers don't support configuration at all.") %
                self.get_name())
        LOG.info(_LI("Nothing to do. '%s' verifiers don't support "
                     "configuration.") % self.get_name())

    def override_configuration(self, new_content):
        """Override verifier configuration."""
        raise NotImplementedError(
            _LE("'%s' verifiers don't support configuration at all.")
            % self.get_name())

    def extend_configuration(self, extra_options):
        """Extend verifier configuration with new options."""
        raise NotImplementedError(
            _LE("'%s' verifiers don't support configuration at all.")
            % self.get_name())

    def get_configuration(self):
        """Get verifier configuration (e.g., the config file content)."""
        return ""

    def install_extension(self, source, version=None, extra_settings=None):
        """Install a verifier extension."""
        raise NotImplementedError(
            _LE("'%s' verifiers don't support extensions.") % self.get_name())

    def list_extensions(self):
        """List all verifier extensions."""
        return []

    def uninstall_extension(self, name):
        """Uninstall a verifier extension."""
        raise NotImplementedError(
            _LE("'%s' verifiers don't support extensions.") % self.get_name())

    @abc.abstractmethod
    def list_tests(self, pattern=""):
        """List all verifier tests."""

    def parse_results(self, results_data):
        """Parse subunit results data of a test run."""
        # TODO(andreykurilin): Support more formats.
        return subunit_v2.parse(six.StringIO(results_data))

    @abc.abstractmethod
    def run(self, context):
        """Run verifier tests.

        This method should return an object with the following attributes:

        <object>.totals = {
            "tests_count": <total tests count>,
            "tests_duration": <total tests duration>,
            "failures": <total count of failed tests>,
            "skipped": <total count of skipped tests>,
            "success": <total count of successful tests>,
            "unexpected_success": <total count of unexpected successful tests>,
            "expected_failures": <total count of expected failed tests>
        }

        <object>.tests = {
            <test_id>: {
                "status": <test status>,
                "name": <test name>,
                "duration": <test duration>,
                "reason": <reason>,  # optional
                "traceback": <traceback>  # optional
            },
            ...
        }
        """
