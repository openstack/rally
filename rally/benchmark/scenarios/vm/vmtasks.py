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

from rally.benchmark.scenarios import base
from rally.benchmark.scenarios.cinder import utils as cinder_utils
from rally.benchmark.scenarios.nova import utils as nova_utils
from rally.benchmark.scenarios.vm import utils as vm_utils
from rally.benchmark import types as types
from rally.benchmark import validation
from rally import consts
from rally import exceptions


class VMTasks(nova_utils.NovaScenario, vm_utils.VMScenario,
              cinder_utils.CinderScenario):
    """Benchmark scenarios that are to be run inside VM instances."""

    def __init__(self, *args, **kwargs):
        super(VMTasks, self).__init__(*args, **kwargs)

    @types.set(image=types.ImageResourceType,
               flavor=types.FlavorResourceType)
    @validation.image_valid_on_flavor("flavor", "image")
    @validation.file_exists("script")
    @validation.number("port", minval=1, maxval=65535, nullable=True,
                       integer_only=True)
    @validation.external_network_exists("floating_network", "use_floatingip")
    @validation.required_services(consts.Service.NOVA, consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["nova", "cinder"],
                            "keypair": {}, "allow_ssh": {}})
    def boot_runcommand_delete(self, image, flavor,
                               script, interpreter, username,
                               volume_args=None,
                               fixed_network="private",
                               floating_network="public",
                               ip_version=4, port=22,
                               use_floatingip=True,
                               force_delete=False,
                               **kwargs):
        """Boot a server, run a script that outputs JSON, delete the server.

        Example Script in doc/samples/tasks/support/instance_dd_test.sh

        :param image: glance image name to use for the vm
        :param flavor: VM flavor name
        :param script: script to run on the server, must output JSON mapping
                       metric names to values (see the sample script below)
        :param interpreter: The shell interpreter to use when running script
        :param username: User to SSH to instance as
        :param volume_args: volume args when boot VM from volume
        :param fixed_network: Network where instance is part of
        :param floating_network: External network used to get floating ip from
        :param ip_version: Version of ip protocol to use for connection
        :param port: Port to use for SSH connection
        :param use_floatingip: Whether to associate a floating ip for
                               connection
        :param force_delete: Whether to use force_delete for instances

        :returns: Dictionary containing two keys, data and errors. Data is JSON
                  data output by the script. Errors is raw data from the
                  script's standard error stream.
        """
        if volume_args:
            volume = self._create_volume(volume_args['size'], imageRef=None)
            kwargs['block_device_mapping'] = {'vda': '%s:::1' % volume.id}

        server = None
        floating_ip = None
        try:
            server = self._boot_server(
                self._generate_random_name("rally_novaserver_"),
                image, flavor, key_name='rally_ssh_key', **kwargs)

            self.check_network(server, fixed_network)

            fixed_ip = [ip for ip in server.addresses[fixed_network] if
                        ip["version"] == ip_version][0]["addr"]

            if use_floatingip:
                floating_ip = self._create_floating_ip(floating_network)
                self._associate_floating_ip(server, floating_ip)
                server_ip = floating_ip.ip
            else:
                server_ip = fixed_ip

            code, out, err = self.run_command(server_ip, port,
                                              username, interpreter, script)

            if code:
                raise exceptions.ScriptError(
                    "Error running script %(script)s."
                    "Error %(code)s: %(error)s" % {
                        "script": script,
                        "code": code,
                        "error": err
                    })

            try:
                out = json.loads(out)
            except ValueError as e:
                raise exceptions.ScriptError(
                    "Script %(script)s did not output valid JSON: %(error)s" %
                    {
                        "script": script,
                        "error": str(e)
                    }
                )

        # Always try to free resources
        finally:
            if use_floatingip:
                self._release_server_floating_ip(server, floating_ip)
            if server:
                self._delete_server(server, force=force_delete)

        return {"data": out, "errors": err}

    def _release_server_floating_ip(self, server, floating_ip):
        """Release a floating ip associated to a server.

        This method check that the given floating ip is associated with the
        specified server and tries to dissociate it.
        Once dissociated, release the floating ip to reintegrate
        it to the pool of available ips.

        :param server: The server to dissociate the floating ip from
        :param floating_ip: The floating ip to release
        """
        if floating_ip and server:
            if self.check_ip_address(floating_ip)(server):
                self._dissociate_floating_ip(server, floating_ip)
        if floating_ip:
            self._delete_floating_ip(floating_ip)
