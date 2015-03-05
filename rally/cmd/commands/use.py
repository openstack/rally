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

""" Rally command: use """

from rally.cmd import cliutils
from rally.cmd.commands import deployment as cmd_deployment
from rally.cmd.commands import task
from rally.cmd.commands import verify
from rally.common import log as logging


LOG = logging.getLogger(__name__)


class UseCommands(object):
    """Set of commands that allow you to set an active deployment and task.

    Active deployment and task allow you not to specify deployment UUID and
    task UUID in the commands requiring this parameter.
    """

    @cliutils.deprecated_args(
        "--uuid", dest="deployment", type=str,
        required=False, help="UUID of the deployment.")
    @cliutils.deprecated_args(
        "--name", dest="deployment", type=str,
        required=False, help="Name of the deployment.")
    @cliutils.args("--deployment", type=str, dest="deployment",
                   help="UUID or name of the deployment")
    def deployment(self, deployment=None):
        """Set active deployment.

        :param deployment: UUID or name of a deployment
        """
        LOG.warning("Deprecated command 'rally use deployment', "
                    "'rally deployment use' should be used instead.")
        cmd_deployment.DeploymentCommands().use(deployment)

    @cliutils.args("--uuid", type=str, dest="task_id", required=False,
                   help="UUID of the task")
    def task(self, task_id):
        """Set active task.

        :param task_id: a UUID of task
        """
        LOG.warning("Deprecated command 'rally use task', "
                    "'rally task use' should be used instead.")
        task.TaskCommands().use(task_id)

    @cliutils.args("--uuid", type=str, dest="verification_id", required=False,
                   help="UUID of the verification")
    def verification(self, verification_id):
        """Set active verification.

        :param verification_id: a UUID of verification
        """
        LOG.warning("Deprecated command 'rally use verification', "
                    "'rally verify use' should be used instead.")
        verify.VerifyCommands.use(verification_id)
