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
import inspect
import os
import re
import shutil
import sys

import pkg_resources
import six

from rally.common.io import subunit_v2
from rally.common import logging
from rally.common.plugin import plugin
from rally import exceptions
from rally.verification import context
from rally.verification import utils


LOG = logging.getLogger(__name__)

URL_RE = re.compile(
    r"^(?:(?:http|ftp)s?|ssh)://"  # http:// or https://
    r"(?:(?:[A-Z0-9](?:[A-Z0-9@-]{0,61}[A-Z0-9])?\.)+"  # domain
    r"(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain
    r"localhost|"  # localhost
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IP
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$", re.IGNORECASE)


class VerifierSetupFailure(exceptions.RallyException):
    error_code = 224
    msg_fmt = "Failed to set up verifier '%(verifier)s': %(message)s"


def configure(name, platform="default", default_repo=None,
              default_version=None, context=None):
    """Decorator to configure plugin's attributes.

    :param name: Plugin name that is used for searching purpose
    :param platform: Plugin platform
    :param default_repo: Default repository to clone
    :param default_version: Default version to checkout
    :param context: List of contexts that should be executed for verification
    """
    def decorator(plugin_inst):
        plugin_inst = plugin.configure(name, platform=platform)(plugin_inst)
        plugin_inst._meta_set("default_repo", default_repo)
        plugin_inst._meta_set("default_version", default_version)
        plugin_inst._meta_set("context", context or {})
        return plugin_inst

    return decorator


@plugin.base()
@six.add_metaclass(abc.ABCMeta)
class VerifierManager(plugin.Plugin):
    """Verifier base class.

    This class provides an interface for operating specific tool.
    """

    # These dicts will be used for building docs. PS: we should find a better
    # place for them
    RUN_ARGS = {"pattern": "a regular expression of tests to launch.",
                "concurrency": "Number of processes to be used for launching "
                               "tests. In case of 0 value, number of processes"
                               " will be equal to number of CPU cores.",
                "load_list": "a list of tests to launch.",
                "skip_list": "a list of tests to skip (actually, it is a dict "
                             "where keys are names of tests, values are "
                             "reasons).",
                "xfail_list": "a list of tests that are expected to fail "
                              "(actually, it is a dict where keys are names "
                              "of tests, values are reasons)."}

    @classmethod
    def _get_doc(cls):
        run_args = {}
        for parent in inspect.getmro(cls):
            if hasattr(parent, "RUN_ARGS"):
                for k, v in parent.RUN_ARGS.items():
                    run_args.setdefault(k, v)

        doc = cls.__doc__ or ""
        doc += "\n**Running arguments**:\n\n%s" % "\n".join(
            sorted(["* *%s*: %s" % (k, v) for k, v in run_args.items()]))

        doc += "\n\n**Installation arguments**:\n\n"
        doc += ("* *system_wide*: Whether or not to use the system-wide "
                "environment for verifier instead of a virtual environment. "
                "Defaults to False.\n"
                "* *source*: Path or URL to the repo to clone verifier from."
                " Defaults to %(default_source)s\n"
                "* *version*: Branch, tag or commit ID to checkout before "
                "verifier installation. Defaults to '%(default_version)s'.\n"
                % {"default_source": cls._meta_get("default_repo"),
                   "default_version": cls._meta_get(
                       "default_version") or "master"})

        return doc

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
        """Validate given arguments to be used for running verification.

        :param args: A dict of arguments with values
        """

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
        """Validate a verifier context and run arguments."""
        context.ContextManager.validate(self._meta_get("context"))
        self.validate_args(run_args)

    def _clone(self):
        """Clone a repo and switch to a certain version."""
        source = self.verifier.source or self._meta_get("default_repo")
        if not URL_RE.match(source) and not os.path.exists(source):
            raise exceptions.RallyException("Source path '%s' is not valid."
                                            % source)

        if logging.is_debug():
            LOG.debug("Cloning verifier repo from %s into %s."
                      % (source, self.repo_dir))
        else:
            LOG.info("Cloning verifier repo from %s." % source)

        cmd = ["git", "clone", source, self.repo_dir]

        default_version = self._meta_get("default_version")
        if default_version and default_version != "master":
            cmd.extend(["-b", default_version])

        utils.check_output(cmd)

        version = self.verifier.version
        if version:
            LOG.info("Switching verifier repo to the '%s' version." % version)
            utils.check_output(["git", "checkout", version], cwd=self.repo_dir)
        else:
            output = utils.check_output(["git", "describe", "--all"],
                                        cwd=self.repo_dir).strip()
            if output.startswith("heads/"):  # it is a branch
                version = output[6:]
            else:
                head = utils.check_output(["git", "rev-parse", "HEAD"],
                                          cwd=self.repo_dir).strip()
                if output.endswith(head[:7]):  # it is a commit ID
                    version = head
                else:  # it is a tag
                    version = output

            self.verifier.update_properties(version=version)

    def install(self):
        """Clone and install a verifier."""
        utils.create_dir(self.base_dir)

        self._clone()

        if self.verifier.system_wide:
            self.check_system_wide()
        else:
            self.install_venv()

    def uninstall(self, full=False):
        """Uninstall a verifier.

        :param full: If False (default behaviour), only deployment-specific
            data will be removed
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

        LOG.debug("Initializing virtual environment in %s directory."
                  % self.venv_dir)
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
        reqs_file_path = reqs_file_path or os.path.join(self.repo_dir,
                                                        "requirements.txt")
        with open(reqs_file_path) as f:
            required_packages = [
                p for p in f.read().split("\n")
                if p.strip() and not p.startswith("#")
            ]
        try:
            pkg_resources.require(required_packages)
        except (pkg_resources.DistributionNotFound,
                pkg_resources.VersionConflict) as e:
            raise VerifierSetupFailure(e.report(), verifier=self.verifier.name)

    def checkout(self, version):
        """Switch a verifier repo."""
        LOG.info("Switching verifier repo to the '%s' version." % version)
        utils.check_output(["git", "checkout", "master"], cwd=self.repo_dir)
        utils.check_output(["git", "remote", "update"], cwd=self.repo_dir)
        utils.check_output(["git", "pull"], cwd=self.repo_dir)
        utils.check_output(["git", "checkout", version], cwd=self.repo_dir)

    def configure(self, extra_options=None):
        """Configure a verifier.

        :param extra_options: a dictionary with external verifier specific
            options for configuration.
        :raises NotImplementedError: This feature is verifier-specific, so you
            should override this method in your plugin if it supports
            configuration
        """
        raise NotImplementedError(
            "'%s' verifiers don't support configuration at all."
            % self.get_name())

    def is_configured(self):
        """Check whether a verifier is configured or not."""
        return True

    def get_configuration(self):
        """Get verifier configuration (e.g., the config file content)."""
        return ""

    def override_configuration(self, new_configuration):
        """Override verifier configuration.

        :param new_configuration: Content which should be used while overriding
            existing configuration
        :raises NotImplementedError: This feature is verifier-specific, so you
            should override this method in your plugin if it supports
            configuration
        """
        raise NotImplementedError(
            "'%s' verifiers don't support configuration at all."
            % self.get_name())

    def extend_configuration(self, extra_options):
        """Extend verifier configuration with new options.

        :param extra_options: Options to be used for extending configuration
        :raises NotImplementedError: This feature is verifier-specific, so you
            should override this method in your plugin if it supports
            configuration
        """
        raise NotImplementedError(
            "'%s' verifiers don't support configuration at all."
            % self.get_name())

    def install_extension(self, source, version=None, extra_settings=None):
        """Install a verifier extension.

        :param source: Path or URL to the repo to clone verifier extension from
        :param version: Branch, tag or commit ID to checkout before verifier
            extension installation
        :param extra_settings: Extra installation settings for verifier
            extension
        :raises NotImplementedError: This feature is verifier-specific, so you
            should override this method in your plugin if it supports
            extensions
        """
        raise NotImplementedError(
            "'%s' verifiers don't support extensions." % self.get_name())

    def list_extensions(self):
        """List all verifier extensions."""
        return []

    def uninstall_extension(self, name):
        """Uninstall a verifier extension.

        :param name: Name of extension to uninstall
        :raises NotImplementedError: This feature is verifier-specific, so you
            should override this method in your plugin if it supports
            extensions
        """
        raise NotImplementedError(
            "'%s' verifiers don't support extensions." % self.get_name())

    @abc.abstractmethod
    def list_tests(self, pattern=""):
        """List all verifier tests.

        :param pattern: Filter tests by given pattern
        """

    def parse_results(self, results_data):
        """Parse subunit results data of a test run."""
        # TODO(andreykurilin): Support more formats.
        return subunit_v2.parse(six.StringIO(results_data))

    @abc.abstractmethod
    def run(self, context):
        """Run verifier tests.

        Verification Component API expects that this method should return an
        object. There is no special class, you do it as you want, but it should
        have the following properties:

          .. code-block:: none

            <object>.totals = {
              "tests_count": <total tests count>,
              "tests_duration": <total tests duration>,
              "failures": <total count of failed tests>,
              "skipped": <total count of skipped tests>,
              "success": <total count of successful tests>,
              "unexpected_success":
                  <total count of unexpected successful tests>,
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
