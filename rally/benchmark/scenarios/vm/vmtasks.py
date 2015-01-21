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

from rally.benchmark.context import keypair
from rally.benchmark.scenarios import base
from rally.benchmark.scenarios.cinder import utils as cinder_utils
from rally.benchmark.scenarios.nova import utils as nova_utils
from rally.benchmark.scenarios.vm import utils as vm_utils
from rally.benchmark import types as types
from rally.benchmark import validation
from rally.benchmark.wrappers import network as network_wrapper
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
    @validation.external_network_exists("floating_network")
    @validation.required_services(consts.Service.NOVA, consts.Service.CINDER)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["nova", "cinder"],
                            "keypair": {}, "allow_ssh": {}})
    def boot_runcommand_delete(self, image, flavor,
                               script, interpreter, username,
                               password=None,
                               volume_args=None,
                               floating_network=None,
                               port=22,
                               force_delete=False,
                               **kwargs):
        """Boot a server, run a script that outputs JSON, delete the server.

        Example Script in doc/samples/tasks/support/instance_dd_test.sh

        :param image: glance image name to use for the vm
        :param flavor: VM flavor name
        :param script: script to run on server, must output JSON mapping
                       metric names to values (see the sample script below)
        :param interpreter: server's interpreter to run the script
        :param username: ssh username on server, str
        :param password: Password on SSH authentication
        :param volume_args: volume args for booting server from volume
        :param floating_network: external network name, for floating ip
        :param port: ssh port for SSH connection
        :param force_delete: whether to use force_delete for servers
        :param **kwargs: extra arguments for booting the server
        :returns: dictionary with keys `data' and `errors':
                  data: dict, JSON output from the script
                  errors: str, raw data from the script's stderr stream
        """

        if volume_args:
            volume = self._create_volume(volume_args["size"], imageRef=None)
            kwargs["block_device_mapping"] = {"vdrally": "%s:::1" % volume.id}

        fip = server = None
        net_wrap = network_wrapper.wrap(self.clients)
        kwargs.update({"auto_assign_nic": True,
                       "key_name": keypair.Keypair.KEYPAIR_NAME})
        server = self._boot_server(
            self._generate_random_name("rally_novaserver_"),
            image, flavor, **kwargs)

        if not server.networks:
            raise RuntimeError(
                "Server `%(server)s' is not connected to any network. "
                "Use network context for auto-assigning networks "
                "or provide `nics' argument with specific net-id." % {
                    "server": server.name})

        internal_network = server.networks.keys()[0]
        fixed_ip = server.addresses[internal_network][0]["addr"]
        try:
            fip = net_wrap.create_floating_ip(ext_network=floating_network,
                                              int_network=internal_network,
                                              tenant_id=server.tenant_id,
                                              fixed_ip=fixed_ip)

            self._associate_floating_ip(server, fip["ip"],
                                        fixed_address=fixed_ip)

            code, out, err = self.run_command(fip["ip"], port, username,
                                              password, interpreter, script)
            if code:
                raise exceptions.ScriptError(
                    "Error running script %(script)s."
                    "Error %(code)s: %(error)s" % {
                        "script": script, "code": code, "error": err})
            try:
                data = json.loads(out)
            except ValueError as e:
                raise exceptions.ScriptError(
                    "Script %(script)s has not output valid JSON: "
                    "%(error)s" % {"script": script, "error": str(e)})

            return {"data": data, "errors": err}

        finally:
            if server:
                if fip:
                    if self.check_ip_address(fip["ip"])(server):
                        self._dissociate_floating_ip(server, fip["ip"])
                    net_wrap.delete_floating_ip(fip["id"], wait=True)
                self._delete_server(server, force=force_delete)
