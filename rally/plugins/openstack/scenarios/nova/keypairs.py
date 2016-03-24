# Copyright 2015: Hewlett-Packard Development Company, L.P.
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

from rally.common import logging
from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.nova import utils
from rally.task import types
from rally.task import validation


class NovaKeypair(utils.NovaScenario):
    """Benchmark scenarios for Nova keypairs."""

    @validation.required_services(consts.Service.NOVA)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["nova"]})
    def create_and_list_keypairs(self, **kwargs):
        """Create a keypair with random name and list keypairs.

        This scenario creates a keypair and then lists all keypairs.

        :param kwargs: Optional additional arguments for keypair creation
        """

        self._create_keypair(**kwargs)
        self._list_keypairs()

    @validation.required_services(consts.Service.NOVA)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["nova"]})
    def create_and_delete_keypair(self, **kwargs):
        """Create a keypair with random name and delete keypair.

        This scenario creates a keypair and then delete that keypair.

        :param kwargs: Optional additional arguments for keypair creation
        """

        keypair = self._create_keypair(**kwargs)
        self._delete_keypair(keypair)

    @types.convert(image={"type": "glance_image"},
                   flavor={"type": "nova_flavor"})
    @validation.image_valid_on_flavor("flavor", "image")
    @validation.required_services(consts.Service.NOVA)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["nova"]})
    @logging.log_deprecated_args(
        "'server_kwargs' has been renamed 'boot_server_kwargs'",
        "0.3.2", ["server_kwargs"], once=True)
    def boot_and_delete_server_with_keypair(self, image, flavor,
                                            boot_server_kwargs=None,
                                            server_kwargs=None,
                                            **kwargs):
        """Boot and delete server with keypair.

        Plan of this scenario:
         - create a keypair
         - boot a VM with created keypair
         - delete server
         - delete keypair

        :param image: ID of the image to be used for server creation
        :param flavor: ID of the flavor to be used for server creation
        :param boot_server_kwargs: Optional additional arguments for VM
                                   creation
        :param server_kwargs: Deprecated alias for boot_server_kwargs
        :param kwargs: Optional additional arguments for keypair creation
        """

        boot_server_kwargs = boot_server_kwargs or server_kwargs or {}

        keypair = self._create_keypair(**kwargs)
        server = self._boot_server(image, flavor,
                                   key_name=keypair,
                                   **boot_server_kwargs)
        self._delete_server(server)
        self._delete_keypair(keypair)
