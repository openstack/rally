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

import random

import jsonschema

from rally.benchmark.scenarios import base
from rally.benchmark.scenarios.cinder import utils as cinder_utils
from rally.benchmark.scenarios.nova import utils
from rally.benchmark.scenarios import utils as scenario_utils
from rally.benchmark import types as types
from rally.benchmark import validation
from rally import consts
from rally import exceptions as rally_exceptions
from rally.openstack.common.gettextutils import _  # noqa
from rally.openstack.common import log as logging


LOG = logging.getLogger(__name__)


class NovaServers(utils.NovaScenario,
                  cinder_utils.CinderScenario):

    RESOURCE_NAME_PREFIX = "rally_novaserver_"
    RESOURCE_NAME_LENGTH = 16

    def __init__(self, *args, **kwargs):
        super(NovaServers, self).__init__(*args, **kwargs)

    @types.set(image=types.ImageResourceType,
               flavor=types.FlavorResourceType)
    @validation.add(validation.image_valid_on_flavor("flavor", "image"))
    @base.scenario(context={"cleanup": ["nova"]})
    @validation.required_services(consts.Service.NOVA)
    def boot_and_list_server(self, image, flavor,
                             detailed=True, **kwargs):
        """Tests booting an image and then listing servers.

           This scenario is a very useful tool to measure
           the "nova list" command performance.

           If you have only 1 user in your context, you will
           add 1 server on every iteration. So you will have more
           and more servers and will be able to measure the
           performance of the "nova list" command depending on
           the number of servers owned by users.
        """
        self._boot_server(
            self._generate_random_name(), image, flavor, **kwargs)
        self._list_servers(detailed)

    @types.set(image=types.ImageResourceType,
               flavor=types.FlavorResourceType)
    @validation.add(validation.image_valid_on_flavor("flavor", "image"))
    @base.scenario(context={"cleanup": ["nova"]})
    @validation.required_services(consts.Service.NOVA)
    def boot_and_delete_server(self, image, flavor,
                               min_sleep=0, max_sleep=0, **kwargs):
        """Tests booting and then deleting an image."""
        server = self._boot_server(
            self._generate_random_name(), image, flavor, **kwargs)
        self.sleep_between(min_sleep, max_sleep)
        self._delete_server(server)

    @types.set(image=types.ImageResourceType,
               flavor=types.FlavorResourceType)
    @validation.add(validation.image_valid_on_flavor("flavor", "image"))
    @base.scenario(context={"cleanup": ["nova", "cinder"]})
    @validation.required_services(consts.Service.NOVA, consts.Service.CINDER)
    def boot_server_from_volume_and_delete(self, image, flavor,
                                           volume_size,
                                           min_sleep=0, max_sleep=0, **kwargs):
        """Tests booting from volume and then deleting an image and volume."""
        volume = self._create_volume(volume_size, imageRef=image)
        block_device_mapping = {'vda': '%s:::1' % volume.id}
        server = self._boot_server(self._generate_random_name(),
                                   image, flavor,
                                   block_device_mapping=block_device_mapping,
                                   **kwargs)
        self.sleep_between(min_sleep, max_sleep)
        self._delete_server(server)

    @types.set(image=types.ImageResourceType,
               flavor=types.FlavorResourceType)
    @validation.add(validation.image_valid_on_flavor("flavor", "image"))
    @base.scenario(context={"cleanup": ["nova"]})
    @validation.required_services(consts.Service.NOVA)
    def boot_and_bounce_server(self, image, flavor, **kwargs):
        """Test booting a server with further performing specified actions.

        Actions should be passed into kwargs. Available actions are
        'hard_reboot', 'soft_reboot', 'stop_start' and 'rescue_unrescue'.
        Delete server after all actions.
        """
        action_builder = self._bind_actions()
        actions = kwargs.get('actions', [])
        try:
            action_builder.validate(actions)
        except jsonschema.exceptions.ValidationError as error:
            raise rally_exceptions.InvalidConfigException(
                "Invalid server actions configuration \'%(actions)s\' due to: "
                "%(error)s" % {'actions': str(actions), 'error': str(error)})
        server = self._boot_server(self._generate_random_name(),
                                   image, flavor, **kwargs)
        for action in action_builder.build_actions(actions, server):
            action()
        self._delete_server(server)

    @types.set(image=types.ImageResourceType,
               flavor=types.FlavorResourceType)
    @validation.add(validation.image_valid_on_flavor("flavor", "image"))
    @base.scenario(context={"cleanup": ["nova", "glance"]})
    @validation.required_services(consts.Service.NOVA, consts.Service.GLANCE)
    def snapshot_server(self, image, flavor, **kwargs):
        """Tests Nova instance snapshotting."""
        server_name = self._generate_random_name()

        server = self._boot_server(server_name, image, flavor, **kwargs)
        image = self._create_image(server)
        self._delete_server(server)

        server = self._boot_server(server_name, image.id, flavor, **kwargs)
        self._delete_server(server)
        self._delete_image(image)

    @types.set(image=types.ImageResourceType,
               flavor=types.FlavorResourceType)
    @validation.add(validation.image_valid_on_flavor("flavor", "image"))
    @base.scenario(context={"cleanup": ["nova"]})
    @validation.required_services(consts.Service.NOVA)
    def boot_server(self, image, flavor, **kwargs):
        """Test VM boot - assumed clean-up is done elsewhere."""
        if 'nics' not in kwargs:
            nets = self.clients("nova").networks.list()
            if nets:
                random_nic = random.choice(nets)
                kwargs['nics'] = [{'net-id': random_nic.id}]
        self._boot_server(
            self._generate_random_name(), image, flavor, **kwargs)

    @types.set(image=types.ImageResourceType,
               flavor=types.FlavorResourceType)
    @validation.add(validation.image_valid_on_flavor("flavor", "image"))
    @base.scenario(context={"cleanup": ["nova", "cinder"]})
    @validation.required_services(consts.Service.NOVA, consts.Service.CINDER)
    def boot_server_from_volume(self, image, flavor,
                                volume_size, **kwargs):
        """Test VM boot from volume - assumed clean-up is done elsewhere."""
        if 'nics' not in kwargs:
            nets = self.clients("nova").networks.list()
            if nets:
                random_nic = random.choice(nets)
                kwargs['nics'] = [{'net-id': random_nic.id}]
        volume = self._create_volume(volume_size, imageRef=image)
        block_device_mapping = {'vda': '%s:::1' % volume.id}
        self._boot_server(self._generate_random_name(),
                          image, flavor,
                          block_device_mapping=block_device_mapping,
                          **kwargs)

    def _bind_actions(self):
        actions = ['hard_reboot', 'soft_reboot', 'stop_start',
                   'rescue_unrescue']
        action_builder = scenario_utils.ActionBuilder(actions)
        action_builder.bind_action('hard_reboot', self._reboot_server)
        action_builder.bind_action('soft_reboot', self._soft_reboot_server)
        action_builder.bind_action('stop_start',
                                   self._stop_and_start_server)
        action_builder.bind_action('rescue_unrescue',
                                   self._rescue_and_unrescue_server)
        return action_builder

    def _stop_and_start_server(self, server):
        """Stop and then start the given server.

        A stop will be issued on the given server upon which time
        this method will wait for the server to become 'SHUTOFF'.
        Once the server is SHUTOFF a start will be issued and this
        method will wait for the server to become 'ACTIVE' again.

        :param server: The server to stop and then start.

        """
        self._stop_server(server)
        self._start_server(server)

    def _rescue_and_unrescue_server(self, server):
        """Rescue and then unrescue the given server.

        A rescue will be issued on the given server upon which time
        this method will wait for the server to become 'RESCUE'.
        Once the server is RESCUE a unrescue will be issued and
        this method will wait for the server to become 'ACTIVE'
        again.

        :param server: The server to rescue and then unrescue.

        """
        self._rescue_server(server)
        self._unrescue_server(server)

    @types.set(image=types.ImageResourceType,
               flavor=types.FlavorResourceType,
               to_flavor=types.FlavorResourceType)
    @validation.add(validation.image_valid_on_flavor("flavor", "image"))
    @base.scenario(context={"cleanup": ["nova"]})
    @validation.required_services(consts.Service.NOVA)
    def resize_server(self, image, flavor, to_flavor, **kwargs):
        """Tests resize serveri."""
        server = self._boot_server(self._generate_random_name(),
                                   image, flavor, **kwargs)
        self._resize(server, to_flavor)
        # by default we confirm
        confirm = kwargs.get('confirm', True)
        if confirm:
            self._resize_confirm(server)
        else:
            self._resize_revert(server)
        self._delete_server(server)
