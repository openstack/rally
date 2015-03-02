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
import six

from rally.benchmark.scenarios import base
from rally.benchmark import utils as bench_utils
from rally.benchmark.wrappers import network as network_wrapper
from rally.common.i18n import _
from rally.common import log as logging
from rally.common import sshutils
from rally import exceptions

LOG = logging.getLogger(__name__)


class VMScenario(base.Scenario):
    """Base class for VM scenarios with basic atomic actions.

    VM scenarios are scenarios executed inside some launched VM instance.
    """

    @base.atomic_action_timer("vm.run_command_over_ssh")
    def _run_command_over_ssh(self, ssh, interpreter, script):
        """Run command inside an instance.

        This is a separate function so that only script execution is timed.

        :param ssh: A SSHClient instance.
        :param interpreter: The interpreter that will be used to execute
                the script.
        :param script: Path to the script file or its content in a StringIO.

        :returns: tuple (exit_status, stdout, stderr)
        """
        if isinstance(script, six.string_types):
            stdin = open(script, "rb")
        elif isinstance(script, six.moves.StringIO):
            stdin = script
        else:
            raise exceptions.ScriptError(
                "Either file path or StringIO expected, given %s" %
                type(script).__name__)

        return ssh.execute(interpreter, stdin=stdin)

    def _get_netwrap(self):
        if not hasattr(self, "_netwrap"):
            self._netwrap = network_wrapper.wrap(self.clients)
        return self._netwrap

    def _boot_server_with_fip(self, image, flavor, floating_network=None,
                              wait_for_ping=True, **kwargs):
        kwargs["auto_assign_nic"] = True
        server = self._boot_server(image, flavor, **kwargs)

        if not server.networks:
            raise RuntimeError(
                "Server `%(server)s' is not connected to any network. "
                "Use network context for auto-assigning networks "
                "or provide `nics' argument with specific net-id." % {
                    "server": server.name})

        fip = self._attach_floating_ip(server, floating_network)

        if wait_for_ping:
            self._wait_for_ping(fip["ip"])

        return server, fip

    @base.atomic_action_timer("vm.attach_floating_ip")
    def _attach_floating_ip(self, server, floating_network):
        internal_network = list(server.networks)[0]
        fixed_ip = server.addresses[internal_network][0]["addr"]

        fip = self._get_netwrap().create_floating_ip(
            ext_network=floating_network, int_network=internal_network,
            tenant_id=server.tenant_id, fixed_ip=fixed_ip)

        self._associate_floating_ip(server, fip["ip"], fixed_address=fixed_ip)

        return fip

    @base.atomic_action_timer("vm.delete_floating_ip")
    def _delete_floating_ip(self, server, fip):
        with logging.ExceptionLogger(
                LOG, _("Unable to delete IP: %s") % fip["ip"]):
            if self.check_ip_address(fip["ip"])(server):
                self._dissociate_floating_ip(server, fip["ip"])
            self._get_netwrap().delete_floating_ip(fip["id"], wait=True)

    def _delete_server_with_fip(self, server, fip, force_delete=False):
        self._delete_floating_ip(server, fip)

        return self._delete_server(server, force=force_delete)

    @base.atomic_action_timer("vm.wait_for_ssh")
    def _wait_for_ssh(self, ssh):
        ssh.wait()

    @base.atomic_action_timer("vm.wait_for_ping")
    def _wait_for_ping(self, server_ip):
        bench_utils.wait_for(
            server_ip,
            is_ready=self._ping_ip_address,
            timeout=120
        )

    def _run_command(self, server_ip, port, username, password,
                     interpreter, script, pkey=None):
        """Run command via SSH on server.

        Create SSH connection for server, wait for server to become
        available (there is a delay between server being set to ACTIVE
        and sshd being available). Then call run_command_over_ssh to actually
        execute the command.
        """
        pkey = pkey if pkey else self.context["user"]["keypair"]["private"]
        ssh = sshutils.SSH(username, server_ip, port=port,
                           pkey=pkey, password=password)
        self._wait_for_ssh(ssh)
        return self._run_command_over_ssh(ssh, interpreter, script)

    @staticmethod
    def _ping_ip_address(host, should_succeed=True):
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
        LOG.debug("Host %s is ICMP %s"
                  % (host, proc.returncode and "down" or "up"))
        return (proc.returncode == 0) == should_succeed
