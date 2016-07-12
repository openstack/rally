# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.ec2 import utils
from rally.task import types
from rally.task import validation


class EC2Servers(utils.EC2Scenario):
    """Benchmark scenarios for servers using EC2."""

    @validation.required_services(consts.Service.EC2)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["ec2"]})
    def list_servers(self):
        """List all servers.

        This simple scenario tests the EC2 API list function by listing
        all the servers.
        """
        self._list_servers()

    @types.convert(image={"type": "ec2_image"},
                   flavor={"type": "ec2_flavor"})
    @validation.image_valid_on_flavor("flavor", "image")
    @validation.required_services(consts.Service.EC2)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["ec2"]})
    def boot_server(self, image, flavor, **kwargs):
        """Boot a server.

        Assumes that cleanup is done elsewhere.

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param kwargs: optional additional arguments for server creation
        """
        self._boot_servers(image, flavor, **kwargs)
