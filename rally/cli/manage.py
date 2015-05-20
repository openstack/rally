# Copyright 2013: Mirantis Inc.
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

""" CLI interface for Rally. """

from __future__ import print_function

import sys

from rally import api
from rally.cli import cliutils
from rally.cli import envutils
from rally import db


class DBCommands(object):
    """Commands for DB management."""

    def recreate(self):
        db.db_drop()
        db.db_create()
        envutils.clear_env()


class TempestCommands(object):
    """Commands for Tempest management."""

    @cliutils.deprecated_args(
        "--deploy-id", dest="deployment", type=str,
        required=False, help="UUID of the deployment.")
    @cliutils.args("--deployment", type=str, dest="deployment",
                   required=False, help="UUID or name of the deployment")
    @cliutils.args("--source", type=str, dest="source",
                   required=False, help="Path/URL to repo to pull tempest "
                                        "from.")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    def install(self, deployment=None, source=None):
        """Install Tempest."""
        api.Verification.install_tempest(deployment, source)

    @cliutils.args("--deployment", type=str, dest="deployment",
                   required=False, help="UUID or name of the deployment")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    def uninstall(self, deployment=None):
        """Removes deployment's local Tempest installation."""
        api.Verification.uninstall_tempest(deployment)

    @cliutils.args("--deployment", type=str, dest="deployment",
                   required=False, help="UUID or name of the deployment")
    @cliutils.args("--tempest-config", dest="tempest_config", type=str,
                   required=False,
                   help="User specified Tempest config file location")
    @cliutils.args("--source", type=str, dest="source",
                   required=False, help="New Path/URL to repo to pull tempest "
                                        "from. Use old source as default")
    @envutils.with_default_deployment(cli_arg_name="deployment")
    def reinstall(self, deployment=None, tempest_config=None, source=None):
        """Uninstall Tempest and then reinstall from new source."""
        api.Verification.reinstall_tempest(deployment, tempest_config, source)


def main():
    categories = {"db": DBCommands,
                  "tempest": TempestCommands}
    cliutils.run(sys.argv, categories)


if __name__ == "__main__":
    main()
