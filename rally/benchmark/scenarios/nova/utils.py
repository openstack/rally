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

from oslo.config import cfg
import random
import string
import time

from rally.benchmark.scenarios import base
from rally.benchmark.scenarios import utils as scenario_utils
from rally.benchmark import utils as bench_utils
from rally import utils

nova_benchmark_opts = []
option_names_and_defaults = [
    # action, prepoll delay, timeout, poll interval
    ('start', 0, 300, 1),
    ('stop', 0, 300, 2),
    ('boot', 1, 300, 1),
    ('delete', 2, 300, 2),
    ('reboot', 2, 300, 2),
    ('rescue', 2, 300, 2),
    ('unrescue', 2, 300, 2),
    ('suspend', 2, 300, 2),
    ('image_create', 0, 300, 2),
    ('image_delete', 0, 300, 2)
]

for action, prepoll, timeout, poll in option_names_and_defaults:
    nova_benchmark_opts.extend([
        cfg.FloatOpt(
            "nova_server_%s_prepoll_delay" % action,
            default=prepoll,
            help='Time to sleep after %s before polling for status' % action
        ),
        cfg.FloatOpt(
            "nova_server_%s_timeout" % action,
            default=timeout,
            help='Server %s timeout' % action
        ),
        cfg.FloatOpt(
            "nova_server_%s_poll_interval" % action,
            default=poll,
            help='Server %s poll interval' % action
        )
    ])

CONF = cfg.CONF
benchmark_group = cfg.OptGroup(name='benchmark',
                               title='benchmark options')
CONF.register_group(benchmark_group)
CONF.register_opts(nova_benchmark_opts, group=benchmark_group)


class NovaScenario(base.Scenario):

    @scenario_utils.atomic_action_timer('nova.boot_server')
    def _boot_server(self, server_name, image_id, flavor_id, **kwargs):
        """Boots one server.

        Returns when the server is actually booted and is in the "Active"
        state.

        :param server_name: String used to name the server
        :param image_id: ID of the image to be used for server creation
        :param flavor_id: ID of the flavor to be used for server creation
        :param **kwargs: Other optional parameters to initialize the server

        :returns: Created server object
        """

        if 'security_groups' not in kwargs:
            kwargs['security_groups'] = ['rally_open']
        else:
            if 'rally_open' not in kwargs['security_groups']:
                kwargs['security_groups'].append('rally_open')

        server = self.clients("nova").servers.create(server_name, image_id,
                                                     flavor_id, **kwargs)
        time.sleep(CONF.benchmark.nova_server_boot_prepoll_delay)
        server = utils.wait_for(
            server,
            is_ready=bench_utils.resource_is("ACTIVE"),
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_boot_timeout,
            check_interval=CONF.benchmark.nova_server_boot_poll_interval
        )
        return server

    @scenario_utils.atomic_action_timer('nova.reboot_server')
    def _reboot_server(self, server, soft=True):
        """Reboots the given server using hard or soft reboot.

        A reboot will be issued on the given server upon which time
        this method will wait for the server to become active.

        :param server: The server to reboot.
        :param soft: False if hard reboot should be used, otherwise
        soft reboot is done (default).
        """
        server.reboot(reboot_type=("SOFT" if soft else "HARD"))
        time.sleep(CONF.benchmark.nova_server_reboot_prepoll_delay)
        utils.wait_for(
            server, is_ready=bench_utils.resource_is("ACTIVE"),
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_reboot_timeout,
            check_interval=CONF.benchmark.nova_server_reboot_poll_interval
        )

    @scenario_utils.atomic_action_timer('nova.start_server')
    def _start_server(self, server):
        """Starts the given server.

        A start will be issued for the given server upon which time
        this method will wait for it to become ACTIVE.

        :param server: The server to start and wait to become ACTIVE.
        """
        server.start()
        utils.wait_for(
            server, is_ready=bench_utils.resource_is("ACTIVE"),
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_start_timeout,
            check_interval=CONF.benchmark.nova_server_start_poll_interval
        )

    @scenario_utils.atomic_action_timer('nova.stop_server')
    def _stop_server(self, server):
        """Stop the given server.

        Issues a stop on the given server and waits for the server
        to become SHUTOFF.

        :param server: The server to stop.
        """
        server.stop()
        utils.wait_for(
            server, is_ready=bench_utils.resource_is("SHUTOFF"),
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_stop_timeout,
            check_interval=CONF.benchmark.nova_server_stop_poll_interval
        )

    @scenario_utils.atomic_action_timer('nova.rescue_server')
    def _rescue_server(self, server):
        """Rescue the given server.

        Returns when the server is actually rescue and is in the "Rescue"
        state.

        :param server: Server object
        """
        server.rescue()
        time.sleep(CONF.benchmark.nova_server_rescue_prepoll_delay)
        utils.wait_for(
            server, is_ready=bench_utils.resource_is("RESCUE"),
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_rescue_timeout,
            check_interval=CONF.benchmark.nova_server_rescue_poll_interval
        )

    @scenario_utils.atomic_action_timer('nova.unrescue_server')
    def _unrescue_server(self, server):
        """Unrescue the given server.

        Returns when the server is unrescue and waits to become ACTIVE

        :param server: Server object
        """
        server.unrescue()
        time.sleep(CONF.benchmark.nova_server_unrescue_prepoll_delay)
        utils.wait_for(
            server, is_ready=bench_utils.resource_is("ACTIVE"),
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_unrescue_timeout,
            check_interval=CONF.benchmark.nova_server_unrescue_poll_interval
        )

    @scenario_utils.atomic_action_timer('nova.suspend_server')
    def _suspend_server(self, server):
        """Suspends the given server.

        Returns when the server is actually suspended and is in the "Suspended"
        state.

        :param server: Server object
        """
        server.suspend()
        time.sleep(CONF.benchmark.nova_server_suspend_prepoll_delay)
        utils.wait_for(
            server, is_ready=bench_utils.resource_is("SUSPENDED"),
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_suspend_timeout,
            check_interval=CONF.benchmark.nova_server_suspend_poll_interval
        )

    @scenario_utils.atomic_action_timer('nova.delete_server')
    def _delete_server(self, server):
        """Deletes the given server.

        Returns when the server is actually deleted.

        :param server: Server object
        """
        server.delete()
        utils.wait_for_delete(
            server,
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_delete_timeout,
            check_interval=CONF.benchmark.nova_server_delete_poll_interval
        )

    @scenario_utils.atomic_action_timer('nova.delete_all_servers')
    def _delete_all_servers(self):
        """Deletes all servers in current tenant."""
        servers = self.clients("nova").servers.list()
        for server in servers:
            self._delete_server(server)

    @scenario_utils.atomic_action_timer('nova.delete_image')
    def _delete_image(self, image):
        """Deletes the given image.

        Returns when the image is actually deleted.

        :param image: Image object
        """
        image.delete()
        utils.wait_for_delete(
            image,
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_image_delete_timeout,
            check_interval=
                CONF.benchmark.nova_server_image_delete_poll_interval
        )

    @scenario_utils.atomic_action_timer('nova.create_image')
    def _create_image(self, server):
        """Creates an image of the given server

        Uses the server name to name the created image. Returns when the image
        is actually created and is in the "Active" state.

        :param server: Server object for which the image will be created

        :returns: Created image object
        """
        image_uuid = self.clients("nova").servers.create_image(server,
                                                               server.name)
        image = self.clients("nova").images.get(image_uuid)
        image = utils.wait_for(
            image,
            is_ready=bench_utils.resource_is("ACTIVE"),
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_image_create_timeout,
            check_interval=
                CONF.benchmark.nova_server_image_create_poll_interval
        )
        return image

    @scenario_utils.atomic_action_timer('nova.boot_servers')
    def _boot_servers(self, name_prefix, image_id, flavor_id,
                      requests, instances_amount=1, **kwargs):
        """Boots multiple servers.

        Returns when all the servers are actually booted and are in the
        "Active" state.

        :param name_prefix: The prefix to use while naming the created servers.
                            The rest of the server names will be '_No.'
        :param image_id: ID of the image to be used for server creation
        :param flavor_id: ID of the flavor to be used for server creation
        :param requests: Number of booting requests to perform
        :param instances_amount: Number of instances to boot per each request

        :returns: List of created server objects
        """
        for i in range(requests):
            self.clients("nova").servers.create('%s_%d' % (name_prefix, i),
                                                image_id, flavor_id,
                                                min_count=instances_amount,
                                                max_count=instances_amount,
                                                **kwargs)
        # NOTE(msdubov): Nova python client returns only one server even when
        #                min_count > 1, so we have to rediscover all the
        #                created servers manyally.
        servers = filter(lambda server: server.name.startswith(name_prefix),
                         self.clients("nova").servers.list())
        time.sleep(CONF.benchmark.nova_server_boot_prepoll_delay)
        servers = [utils.wait_for(
            server,
            is_ready=bench_utils.resource_is("ACTIVE"),
            update_resource=bench_utils.
            get_from_manager(),
            timeout=CONF.benchmark.nova_server_boot_timeout,
            check_interval=CONF.benchmark.nova_server_boot_poll_interval
        ) for server in servers]
        return servers

    def _generate_random_name(self, length):
        return ''.join(random.choice(string.lowercase) for i in range(length))
