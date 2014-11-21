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

from rally.cmd import cliutils
from rally.cmd import envutils
from rally import db
from rally.verification.verifiers.tempest import tempest


class DBCommands(object):
    """Commands for DB management."""

    def recreate(self):
        db.db_drop()
        db.db_create()
        envutils.clear_env()


class TempestCommands(object):
    """Commands for Tempest management."""

    @cliutils.args("--deployment", type=str, dest="deployment",
                   required=False, help="UUID or name of the deployment")
    @envutils.with_default_deployment
    def install(self, deployment=None):
        """Install tempest."""

        deployment_uuid = db.deployment_get(deployment)['uuid']
        verifier = tempest.Tempest(deployment_uuid)
        verifier.install()


def main():
    categories = {'db': DBCommands,
                  'tempest': TempestCommands}
    cliutils.run(sys.argv, categories)


if __name__ == '__main__':
    main()
