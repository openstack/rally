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


from rally.benchmark.scenarios import base
from rally.benchmark.scenarios import utils as scenario_utils
from rally import sshutils


class VMScenario(base.Scenario):

    @scenario_utils.atomic_action_timer('vm.run_command')
    def run_action(self, ssh, interpreter, script):
        """Run command inside an instance.

        This is a separate function so that only script execution is timed
        """
        return ssh.execute(interpreter, stdin=open(script, "rb"))

    @scenario_utils.atomic_action_timer('vm.wait_for_network')
    def wait_for_network(self, ssh):
        ssh.wait()

    def run_command(self, server, username, network, port, ip_version,
                    interpreter, script):
        """Run command via SSH on server.

        Create SSH connection for server, wait for server to become
        available (there is a delay between server being set to ACTIVE
        and sshd being available). Then call __run_command to actually
        execute the command.
        """

        if network not in server.addresses:
            raise ValueError(
                "Can't find cloud network %(network)s, so cannot boot "
                "instance for Rally scenario boot-runcommand-delete. "
                "Available networks: %(networks)s" % (
                    dict(network=network,
                         networks=server.addresses.keys()
                         )
                )
            )
        server_ip = [ip for ip in server.addresses[network] if
                     ip["version"] == ip_version][0]["addr"]
        ssh = sshutils.SSH(username, server_ip, port=port,
                           pkey=self.context()["user"]["keypair"]["private"])

        self.wait_for_network(ssh)
        return self.run_action(ssh, interpreter, script)
