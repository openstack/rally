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

import yaml

from rally.common.i18n import _LE
from rally.common import logging
from rally import exceptions
from rally.plugins.common.verification import testr
from rally.plugins.openstack.verification.tempest import config
from rally.plugins.openstack.verification.tempest import consts
from rally.verification import manager
from rally.verification import utils


LOG = logging.getLogger(__name__)


@manager.configure(name="tempest", namespace="openstack",
                   default_repo="https://git.openstack.org/openstack/tempest",
                   context={"tempest_configuration": {}, "testr_verifier": {}})
class TempestManager(testr.TestrLauncher):
    """Plugin for Tempest management."""

    @property
    def run_environ(self):
        env = super(TempestManager, self).run_environ
        env["TEMPEST_CONFIG_DIR"] = os.path.dirname(self.configfile)
        env["TEMPEST_CONFIG"] = os.path.basename(self.configfile)
        # TODO(andreykurilin): move it to Testr base class
        env["OS_TEST_PATH"] = os.path.join(self.repo_dir,
                                           "tempest/test_discover")
        return env

    @property
    def configfile(self):
        return os.path.join(self.home_dir, "tempest.conf")

    def get_configuration(self):
        return config.read_configfile(self.configfile)

    def configure(self, extra_options=None):
        if not os.path.isdir(self.home_dir):
            os.makedirs(self.home_dir)

        cm = config.TempestConfigfileManager(self.verifier.deployment)
        raw_configfile = cm.create(self.configfile, extra_options)
        return raw_configfile

    def extend_configuration(self, extra_options):
        return config.extend_configfile(self.configfile, extra_options)

    def override_configuration(self, new_content):
        with open(self.configfile, "w") as f:
            f.write(new_content)

    def install_extension(self, source, version=None, extra_settings=None):
        """Install a Tempest plugin."""
        if extra_settings:
            raise NotImplementedError(
                _LE("'%s' verifiers don't support extra installation settings "
                    "for extensions.") % self.get_name())
        version = version or "master"
        egg = re.sub("\.git$", "", os.path.basename(source.strip("/")))
        full_source = "git+{0}@{1}#egg={2}".format(source, version, egg)
        # NOTE(ylobankov): Use 'develop mode' installation to provide an
        #                  ability to advanced users to change tests or
        #                  develop new ones in verifier repo on the fly.
        cmd = ["pip", "install",
               "--src", os.path.join(self.base_dir, "extensions"),
               "-e", full_source]
        if self.verifier.system_wide:
            cmd.insert(2, "--no-deps")
        utils.check_output(cmd, cwd=self.base_dir, env=self.environ)

        # Very often Tempest plugins are inside projects and requirements
        # for plugins are listed in the test-requirements.txt file.
        test_reqs_path = os.path.join(self.base_dir, "extensions",
                                      egg, "test-requirements.txt")
        if os.path.exists(test_reqs_path):
            if not self.verifier.system_wide:
                utils.check_output(["pip", "install", "-r", test_reqs_path],
                                   cwd=self.base_dir, env=self.environ)
            else:
                self.check_system_wide(reqs_file_path=test_reqs_path)

    def list_extensions(self):
        """List all installed Tempest plugins."""
        # TODO(andreykurilin): find a better way to list tempest plugins
        cmd = ("from tempest.test_discover import plugins; "
               "plugins_manager = plugins.TempestTestPluginManager(); "
               "plugins_map = plugins_manager.get_plugin_load_tests_tuple(); "
               "plugins_list = ["
               "    {'name': p.name, "
               "     'entry_point': p.entry_point_target, "
               "     'location': plugins_map[p.name][1]} "
               "    for p in plugins_manager.ext_plugins.extensions]; "
               "print(plugins_list)")
        try:
            output = utils.check_output(["python", "-c", cmd],
                                        cwd=self.base_dir, env=self.environ,
                                        debug_output=False).strip()
        except subprocess.CalledProcessError:
            raise exceptions.RallyException(
                "Cannot list installed Tempest plugins for verifier %s." %
                self.verifier)

        return yaml.load(output)

    def uninstall_extension(self, name):
        """Uninstall a Tempest plugin."""
        for ext in self.list_extensions():
            if ext["name"] == name and os.path.exists(ext["location"]):
                shutil.rmtree(ext["location"])
                break
        else:
            raise exceptions.RallyException(
                "There is no Tempest plugin with name '%s'. "
                "Are you sure that it was installed?" % name)

    def list_tests(self, pattern=""):
        """List all Tempest tests."""
        if pattern:
            pattern = self._transform_pattern(pattern)
        return super(TempestManager, self).list_tests(pattern)

    def validate_args(self, args):
        """Validate given arguments."""
        super(TempestManager, self).validate_args(args)

        if args.get("pattern"):
            pattern = args["pattern"].split("=", 1)
            if len(pattern) == 1:
                pass  # it is just a regex
            elif pattern[0] == "set":
                available_sets = (list(consts.TempestTestSets) +
                                  list(consts.TempestApiTestSets) +
                                  list(consts.TempestScenarioTestSets))
                if pattern[1] not in available_sets:
                    raise exceptions.ValidationError(
                        "Test set '%s' not found in available "
                        "Tempest test sets. Available sets are '%s'."
                        % (pattern[1], "', '".join(available_sets)))
            else:
                raise exceptions.ValidationError(
                    "'pattern' argument should be a regexp or set name "
                    "(format: 'tempest.api.identity.v3', 'set=smoke').")

    def _transform_pattern(self, pattern):
        """Transform pattern into Tempest-specific pattern."""
        parsed_pattern = pattern.split("=", 1)
        if len(parsed_pattern) == 2:
            if parsed_pattern[0] == "set":
                if parsed_pattern[1] in consts.TempestTestSets:
                    return "smoke" if parsed_pattern[1] == "smoke" else ""
                elif parsed_pattern[1] in consts.TempestApiTestSets:
                    return "tempest.api.%s" % parsed_pattern[1]
                else:
                    return "tempest.%s" % parsed_pattern[1]

        return pattern  # it is just a regex

    def prepare_run_args(self, run_args):
        """Prepare 'run_args' for testr context."""
        if run_args.get("pattern"):
            run_args["pattern"] = self._transform_pattern(run_args["pattern"])
        return run_args
