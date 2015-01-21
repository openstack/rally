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

import subprocess
import sys

import netaddr

from rally.benchmark.scenarios import base
from rally.benchmark import utils as bench_utils
from rally.common import sshutils


class VMScenario(base.Scenario):
    """Base class for VM scenarios with basic atomic actions.

    VM scenarios are scenarios executed inside some launched VM instance.
    """

    @base.atomic_action_timer("vm.run_command")
    def run_action(self, ssh, interpreter, script):
        """Run command inside an instance.

        This is a separate function so that only script execution is timed.

        :returns: tuple (exit_status, stdout, stderr)
        """
        return ssh.execute(interpreter, stdin=open(script, "rb"))

    @base.atomic_action_timer("vm.wait_for_ssh")
    def wait_for_ssh(self, ssh):
        ssh.wait()

    @base.atomic_action_timer("vm.wait_for_ping")
    def wait_for_ping(self, server_ip):
        bench_utils.wait_for(
            server_ip,
            is_ready=self.ping_ip_address,
            timeout=120
        )

    def run_command(self, server_ip, port, username, password,
                    interpreter, script):
        """Run command via SSH on server.

        Create SSH connection for server, wait for server to become
        available (there is a delay between server being set to ACTIVE
        and sshd being available). Then call __run_command to actually
        execute the command.
        """
        self.wait_for_ping(server_ip)
        ssh = sshutils.SSH(username, server_ip, port=port,
                           pkey=self.context["user"]["keypair"]["private"],
                           password=password)

        self.wait_for_ssh(ssh)
        return self.run_action(ssh, interpreter, script)

    @staticmethod
    def ping_ip_address(host, should_succeed=True):
        ip = netaddr.IPAddress(host)
        ping = "ping" if ip.version == 4 else "ping6"
        if sys.platform.startswith("linux"):
            cmd = [ping, "-c1", "-w1", host]
        else:
            cmd = [ping, "-c1", host]

        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        proc.wait()
        return (proc.returncode == 0) == should_succeed
