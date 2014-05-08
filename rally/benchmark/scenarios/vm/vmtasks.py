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
from rally.benchmark.scenarios.nova import utils as nova_utils
from rally.benchmark.scenarios.vm import utils as vm_utils
from rally.benchmark import validation as valid
from rally.openstack.common.gettextutils import _  # noqa
from rally.openstack.common import log as logging


LOG = logging.getLogger(__name__)


class VMTasks(nova_utils.NovaScenario, vm_utils.VMScenario):

    def __init__(self, *args, **kwargs):
        super(VMTasks, self).__init__(*args, **kwargs)

    @valid.add_validator(valid.image_valid_on_flavor("flavor_id", "image_id"))
    @valid.add_validator(valid.file_exists("script"))
    @valid.add_validator(valid.number("port", minval=1, maxval=65535,
                                      nullable=True, integer_only=True))
    @base.scenario(context={"cleanup": ["nova"],
                   "keypair": {}, "allow_ssh": {}})
    def boot_runcommand_delete(self, image_id, flavor_id,
                               script, interpreter, network='private',
                               username='ubuntu', ip_version=4,
                               port=22, **kwargs):
        """Boot server, run a script that outputs JSON, delete server.

        Parameters:
        script: script to run on the server, must output JSON mapping metric
                names to values. See sample script below.
        network: Network to choose address to connect to instance from
        username: User to SSH to instance as
        ip_version: Version of ip protocol to use for connection

        returns: Dictionary containing two keys, data and errors. Data is JSON
                 data output by the script. Errors is raw data from the
                 script's standard error stream.


        Example Script in doc/samples/support/instance_dd_test.sh
        """
        server_name = self._generate_random_name(16)

        server = self._boot_server(server_name, image_id, flavor_id,
                                   key_name='rally_ssh_key', **kwargs)

        code, out, err = self.run_command(server, username, network, port,
                                          ip_version, interpreter, script)
        if code:
            LOG.error(_("Error running script on instance via SSH. "
                        "Error: %s") % err)
        try:
            out = json.loads(out)
        except ValueError:
            LOG.warning(_("Script %s did not output valid JSON.") % script)

        self._delete_server(server)
        LOG.debug(_("Output streams from in-instance script execution: "
                    "stdout: %(stdout)s, stderr: $(stderr)s") % dict(
                        stdout=out, stderr=err))
        return {"data": out, "errors": err}
