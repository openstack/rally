# Copyright 2014: Rackspace UK
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

import json
import pkgutil

from rally.common import logging
from rally.common import sshutils
from rally import consts
from rally import exceptions
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.vm import utils as vm_utils
from rally.plugins.openstack.services import heat
from rally.task import atomic
from rally.task import types
from rally.task import validation

LOG = logging.getLogger(__name__)


class VMTasks(vm_utils.VMScenario):
    """Benchmark scenarios that are to be run inside VM instances."""

    def __init__(self, *args, **kwargs):
        super(VMTasks, self).__init__(*args, **kwargs)

    @types.convert(image={"type": "glance_image"},
                   flavor={"type": "nova_flavor"})
    @validation.image_valid_on_flavor("flavor", "image")
    @validation.valid_command("command")
    @validation.number("port", minval=1, maxval=65535, nullable=True,
                       integer_only=True)
    @validation.external_network_exists("floating_network")
    @validation.required_services(consts.Service.NOVA, consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["nova", "cinder"],
                                 "keypair": {}, "allow_ssh": {}})
    def boot_runcommand_delete(self, image, flavor,
                               username,
                               password=None,
                               command=None,
                               volume_args=None,
                               floating_network=None,
                               port=22,
                               use_floating_ip=True,
                               force_delete=False,
                               wait_for_ping=True,
                               max_log_length=None,
                               **kwargs):
        """Boot a server, run script specified in command and delete server.

        Example Script in samples/tasks/support/instance_dd_test.sh

        The script to be executed is provided like command['remote_path'] or
        command['local_path'] and interpreter in command['interpreter']
        respectively.

        :param image: glance image name to use for the vm
        :param flavor: VM flavor name
        :param username: ssh username on server, str
        :param password: Password on SSH authentication
        :param command: Command-specifying dictionary that either specifies
            remote command path via `remote_path' (can be uploaded from a
            local file specified by `local_path`), an inline script via
            `script_inline' or a local script file path using `script_file'.
            Both `script_file' and `local_path' are checked to be accessible
            by the `file_exists' validator code.

            The `script_inline' and `script_file' both require an `interpreter'
            value to specify the interpreter script should be run with.

            Note that any of `interpreter' and `remote_path' can be an array
            prefixed with environment variables and suffixed with args for
            the `interpreter' command. `remote_path's last component must be
            a path to a command to execute (also upload destination if a
            `local_path' is given). Uploading an interpreter is possible
            but requires that `remote_path' and `interpreter' path do match.


            Examples::

                # Run a `local_script.pl' file sending it to a remote
                # Perl interpreter
                command = {
                    "script_file": "local_script.pl",
                    "interpreter": "/usr/bin/perl"
                }

                # Run an inline script sending it to a remote interpreter
                command = {
                    "script_inline": "echo 'Hello, World!'",
                    "interpreter": "/bin/sh"
                }

                # Run a remote command
                command = {
                    "remote_path": "/bin/false"
                }

                # Copy a local command and run it
                command = {
                    "remote_path": "/usr/local/bin/fio",
                    "local_path": "/home/foobar/myfiodir/bin/fio"
                }

                # Copy a local command and run it with environment variable
                command = {
                    "remote_path": ["HOME=/root", "/usr/local/bin/fio"],
                    "local_path": "/home/foobar/myfiodir/bin/fio"
                }

                # Run an inline script sending it to a remote interpreter
                command = {
                    "script_inline": "echo \"Hello, ${NAME:-World}\"",
                    "interpreter": ["NAME=Earth", "/bin/sh"]
                }

                # Run an inline script sending it to an uploaded remote
                # interpreter
                command = {
                    "script_inline": "echo \"Hello, ${NAME:-World}\"",
                    "interpreter": ["NAME=Earth", "/tmp/sh"],
                    "remote_path": "/tmp/sh",
                    "local_path": "/home/user/work/cve/sh-1.0/bin/sh"
                }


        :param volume_args: volume args for booting server from volume
        :param floating_network: external network name, for floating ip
        :param port: ssh port for SSH connection
        :param use_floating_ip: bool, floating or fixed IP for SSH connection
        :param force_delete: whether to use force_delete for servers
        :param wait_for_ping: whether to check connectivity on server creation
        :param **kwargs: extra arguments for booting the server
        :param max_log_length: The number of tail nova console-log lines user
                               would like to retrieve
        :returns: dictionary with keys `data' and `errors':
                  data: dict, JSON output from the script
                  errors: str, raw data from the script's stderr stream
        """

        if volume_args:
            volume = self._create_volume(volume_args["size"], imageRef=None)
            kwargs["block_device_mapping"] = {"vdrally": "%s:::1" % volume.id}

        server, fip = self._boot_server_with_fip(
            image, flavor, use_floating_ip=use_floating_ip,
            floating_network=floating_network,
            key_name=self.context["user"]["keypair"]["name"],
            **kwargs)
        try:
            if wait_for_ping:
                self._wait_for_ping(fip["ip"])

            code, out, err = self._run_command(
                fip["ip"], port, username, password, command=command)
            if code:
                raise exceptions.ScriptError(
                    "Error running command %(command)s. "
                    "Error %(code)s: %(error)s" % {
                        "command": command, "code": code, "error": err})

            try:
                data = json.loads(out)
            except ValueError as e:
                raise exceptions.ScriptError(
                    "Command %(command)s has not output valid JSON: %(error)s."
                    " Output: %(output)s" % {
                        "command": command, "error": str(e), "output": out})
        except (exceptions.TimeoutException,
                exceptions.SSHTimeout):
            console_logs = self._get_server_console_output(server,
                                                           max_log_length)
            LOG.debug("VM console logs:\n%s", console_logs)
            raise

        finally:
            self._delete_server_with_fip(server, fip,
                                         force_delete=force_delete)

        if type(data) != dict:
            raise exceptions.ScriptError(
                "Command has returned data in unexpected format.\n"
                "Expected format: {"
                "\"additive\": [{chart data}, {chart data}, ...], "
                "\"complete\": [{chart data}, {chart data}, ...]}\n"
                "Actual data: %s" % data)

        if set(data) - {"additive", "complete"}:
            LOG.warning(
                "Deprecated since Rally release 0.4.1: command has "
                "returned data in format {\"key\": <value>, ...}\n"
                "Expected format: {"
                "\"additive\": [{chart data}, {chart data}, ...], "
                "\"complete\": [{chart data}, {chart data}, ...]}")
            output = None
            try:
                output = [[str(k), float(v)] for k, v in data.items()]
            except (TypeError, ValueError):
                raise exceptions.ScriptError(
                    "Command has returned data in unexpected format.\n"
                    "Expected format: {key1: <number>, "
                    "key2: <number>, ...}.\n"
                    "Actual data: %s" % data)
            if output:
                self.add_output(additive={"title": "Command output",
                                          "chart_plugin": "Lines",
                                          "data": output})
        else:
            for chart_type, charts in data.items():
                for chart in charts:
                    self.add_output(**{chart_type: chart})

    @types.convert(image={"type": "glance_image"},
                   flavor={"type": "nova_flavor"})
    @validation.number("port", minval=1, maxval=65535, nullable=True,
                       integer_only=True)
    @validation.valid_command("command")
    @validation.external_network_exists("floating_network")
    @validation.required_services(consts.Service.NOVA, consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @validation.required_contexts("image_command_customizer")
    @scenario.configure(context={"cleanup": ["nova", "cinder"],
                                 "keypair": {}, "allow_ssh": {}})
    def boot_runcommand_delete_custom_image(self, **kwargs):
        """Boot a server from a custom image, run a command that outputs JSON.

        Example Script in rally-jobs/extra/install_benchmark.sh
        """

        return self.boot_runcommand_delete(
            image=self.context["tenant"]["custom_image"]["id"], **kwargs)

    @scenario.configure(context={"cleanup": ["nova", "heat"],
                                 "keypair": {}, "network": {}})
    def runcommand_heat(self, workload, template, files, parameters):
        """Run workload on stack deployed by heat.

        Workload can be either file or resource:

        .. code-block: json

            {"file": "/path/to/file.sh"}
            {"resource": ["package.module", "workload.py"]}

        Also it should contain "username" key.

        Given file will be uploaded to `gate_node` and started. This script
        should print `key` `value` pairs separated by colon. These pairs will
        be presented in results.

        Gate node should be accessible via ssh with keypair `key_name`, so
        heat template should accept parameter `key_name`.

        :param workload: workload to run
        :param template: path to heat template file
        :param files: additional template files
        :param parameters: parameters for heat template
        """
        keypair = self.context["user"]["keypair"]
        parameters["key_name"] = keypair["name"]
        network = self.context["tenant"]["networks"][0]
        parameters["router_id"] = network["router_id"]
        self.stack = heat.main.Stack(self, self.task,
                                     template, files=files,
                                     parameters=parameters)
        self.stack.create()
        for output in self.stack.stack.outputs:
            if output["output_key"] == "gate_node":
                ip = output["output_value"]
                break
        ssh = sshutils.SSH(workload["username"], ip, pkey=keypair["private"])
        ssh.wait()
        script = workload.get("resource")
        if script:
            script = pkgutil.get_data(*script)
        else:
            script = open(workload["file"]).read()
        ssh.execute("cat > /tmp/.rally-workload", stdin=script)
        ssh.execute("chmod +x /tmp/.rally-workload")
        with atomic.ActionTimer(self, "runcommand_heat.workload"):
            status, out, err = ssh.execute(
                "/tmp/.rally-workload",
                stdin=json.dumps(self.stack.stack.outputs))
        rows = []
        for line in out.splitlines():
            row = line.split(":")
            if len(row) != 2:
                raise exceptions.ScriptError("Invalid data '%s'" % line)
            rows.append(row)
        if not rows:
            raise exceptions.ScriptError("No data returned. Original error "
                                         "message is %s" % err)
        self.add_output(
            complete={"title": "Workload summary",
                      "description": "Data generated by workload",
                      "chart_plugin": "Table",
                      "data": {
                          "cols": ["key", "value"],
                          "rows": rows}}
        )
