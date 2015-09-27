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

from rally.common import utils
from rally import consts
from rally import exceptions
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.vm import utils as vm_utils
from rally.task import types
from rally.task import validation


class VMTasks(vm_utils.VMScenario):
    """Benchmark scenarios that are to be run inside VM instances."""

    def __init__(self, *args, **kwargs):
        super(VMTasks, self).__init__(*args, **kwargs)

    @types.set(image=types.ImageResourceType,
               flavor=types.FlavorResourceType)
    @validation.image_valid_on_flavor("flavor", "image")
    @utils.log_deprecated_args("Use `command' argument instead", "0.0.5",
                               ("script", "interpreter"), once=True)
    @validation.file_exists("script", required=False)
    @validation.valid_command("command", required=False)
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
                               script=None,
                               interpreter=None,
                               command=None,
                               volume_args=None,
                               floating_network=None,
                               port=22,
                               use_floating_ip=True,
                               force_delete=False,
                               wait_for_ping=True,
                               **kwargs):
        """Boot a server, run a script that outputs JSON, delete the server.

        Example Script in samples/tasks/support/instance_dd_test.sh

        :param image: glance image name to use for the vm
        :param flavor: VM flavor name
        :param username: ssh username on server, str
        :param password: Password on SSH authentication
        :param script: DEPRECATED. Use `command' instead. Script to run on
            server, must output JSON mapping metric names to values (see the
            sample script below)
        :param interpreter: DEPRECATED. Use `command' instead. server's
            interpreter to run the script
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

                # Run an inline script sending it to a uploaded remote
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
        :returns: dictionary with keys `data' and `errors':
                  data: dict, JSON output from the script
                  errors: str, raw data from the script's stderr stream
        """

        if command is None and script and interpreter:
            command = {"script_file": script, "interpreter": interpreter}

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
        finally:
            self._delete_server_with_fip(server, fip,
                                         force_delete=force_delete)

        return {"data": data, "errors": err}

    @types.set(image=types.ImageResourceType,
               flavor=types.FlavorResourceType)
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
