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
from rally.cmd.commands import deployment
from rally.cmd.commands import show
from rally.cmd.commands import task
from rally.cmd.commands import use
from rally.cmd.commands import verify


def deprecated():
    print("\n\n---\n\nopenstack-rally and openstack-rally-manage are "
          "deprecated, please use rally and rally-manage\n\n---\n\n")
    main()


def main():
    categories = {
        'deployment': deployment.DeploymentCommands,
        'show': show.ShowCommands,
        'task': task.TaskCommands,
        'use': use.UseCommands,
        'verify': verify.VerifyCommands
    }
    return cliutils.run(sys.argv, categories)


if __name__ == '__main__':
    main()
