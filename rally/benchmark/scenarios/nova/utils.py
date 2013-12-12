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
import string
import time

from rally.benchmark import base
from rally.benchmark import utils as bench_utils
from rally import utils


class NovaScenario(base.Scenario):

    @classmethod
    def _boot_server(cls, server_name, image_id, flavor_id, **kwargs):
        """Boots one server.

        Returns when the server is actually booted and is in the "Active"
        state.

        :param server_name: String used to name the server
        :param image_id: ID of the image to be used for server creation
        :param flavor_id: ID of the flavor to be used for server creation
        :param **kwargs: Other optional parameters to initialize the server

        :returns: Created server object
        """
        server = cls.clients("nova").servers.create(server_name, image_id,
                                                    flavor_id, **kwargs)
        # NOTE(msdubov): It is reasonable to wait 5 secs before starting to
        #                check whether the server is ready => less API calls.
        time.sleep(5)
        server = utils.wait_for(server,
                                is_ready=bench_utils.resource_is("ACTIVE"),
                                update_resource=bench_utils.get_from_manager(),
                                timeout=600, check_interval=3)
        return server

    @classmethod
    def _reboot_server(cls, server, soft=True):
        """Reboots the given server using hard or soft reboot.

        A reboot will be issued on the given server upon which time
        this method will wait for the server to become active.

        :param server: The server to reboot.
        :param soft: False if hard reboot should be used, otherwise
        soft reboot is done (default).
        """
        server.reboot(reboot_type=("SOFT" if soft else "HARD"))
        time.sleep(5)
        utils.wait_for(server, is_ready=bench_utils.resource_is("ACTIVE"),
                       update_resource=bench_utils.get_from_manager(),
                       timeout=600, check_interval=3)

    @classmethod
    def _start_server(cls, server):
        """Starts the given server.

        A start will be issued for the given server upon which time
        this method will wait for it to become ACTIVE.

        :param server: The server to start and wait to become ACTIVE.
        """
        server.start()
        utils.wait_for(server, is_ready=bench_utils.resource_is("ACTIVE"),
                       update_resource=bench_utils.get_from_manager(),
                       timeout=600, check_interval=2)

    @classmethod
    def _stop_server(cls, server):
        """Stop the given server.

        Issues a stop on the given server and waits for the server
        to become SHUTOFF.

        :param server: The server to stop.
        """
        server.stop()
        utils.wait_for(server, is_ready=bench_utils.resource_is("SHUTOFF"),
                       update_resource=bench_utils.get_from_manager(),
                       timeout=600, check_interval=2)

    @classmethod
    def _rescue_server(cls, server):
        """Rescue the given server.

        Returns when the server is actually rescue and is in the "Rescue"
        state.

        :param server: Server object
        """
        server.rescue()
        time.sleep(2)
        utils.wait_for(server, is_ready=bench_utils.resource_is("RESCUE"),
                       update_resource=bench_utils.get_from_manager(),
                       timeout=600, check_interval=3)

    @classmethod
    def _unrescue_server(cls, server):
        """Unrescue the given server.

        Returns when the server is unrescue and waits to become ACTIVE

        :param server: Server object
        """
        server.unrescue()
        time.sleep(2)
        utils.wait_for(server, is_ready=bench_utils.resource_is("ACTIVE"),
                       update_resource=bench_utils.get_from_manager(),
                       timeout=600, check_interval=3)

    @classmethod
    def _suspend_server(cls, server):
        """Suspends the given server.

        Returns when the server is actually suspended and is in the "Suspended"
        state.

        :param server: Server object
        """
        server.suspend()
        time.sleep(2)
        utils.wait_for(server, is_ready=bench_utils.resource_is("SUSPENDED"),
                       update_resource=bench_utils.get_from_manager(),
                       timeout=600, check_interval=3)

    @classmethod
    def _delete_server(cls, server):
        """Deletes the given server.

        Returns when the server is actually deleted.

        :param server: Server object
        """
        server.delete()
        utils.wait_for(server, is_ready=bench_utils.is_none,
                       update_resource=bench_utils.get_from_manager(),
                       timeout=600, check_interval=3)

    @classmethod
    def _delete_all_servers(cls):
        """Deletes all servers in current tenant."""
        servers = cls.clients("nova").servers.list()
        for server in servers:
            cls._delete_server(server)

    @classmethod
    def _delete_image(cls, image):
        """Deletes the given image.

        Returns when the image is actually deleted.

        :param image: Image object
        """
        image.delete()
        utils.wait_for(image, is_ready=bench_utils.resource_is("DELETED"),
                       update_resource=bench_utils.get_from_manager(),
                       timeout=600, check_interval=3)

    @classmethod
    def _create_image(cls, server):
        """Creates an image of the given server

        Uses the server name to name the created image. Returns when the image
        is actually created and is in the "Active" state.

        :param server: Server object for which the image will be created

        :returns: Created image object
        """
        image_uuid = cls.clients("nova").servers.create_image(server,
                                                              server.name)
        image = cls.clients("nova").images.get(image_uuid)
        image = utils.wait_for(image,
                               is_ready=bench_utils.resource_is("ACTIVE"),
                               update_resource=bench_utils.get_from_manager(),
                               timeout=600, check_interval=3)
        return image

    @classmethod
    def _boot_servers(cls, name_prefix, image_id, flavor_id,
                      requests, instances_per_request=1, **kwargs):
        """Boots multiple servers.

        Returns when all the servers are actually booted and are in the
        "Active" state.

        :param name_prefix: The prefix to use while naming the created servers.
                            The rest of the server names will be '_No.'
        :param image_id: ID of the image to be used for server creation
        :param flavor_id: ID of the flavor to be used for server creation
        :param requests: Number of booting requests to perform
        :param instances_per_request: Number of instances to boot
                                      per each request

        :returns: List of created server objects
        """
        for i in range(requests):
            cls.clients("nova").servers.create('%s_%d' % (name_prefix, i),
                                               image_id, flavor_id,
                                               min_count=instances_per_request,
                                               max_count=instances_per_request,
                                               **kwargs)
        # NOTE(msdubov): Nova python client returns only one server even when
        #                min_count > 1, so we have to rediscover all the
        #                created servers manyally.
        servers = filter(lambda server: server.name.startswith(name_prefix),
                         cls.clients("nova").servers.list())
        time.sleep(5)
        servers = [utils.wait_for(server,
                                  is_ready=bench_utils.resource_is("ACTIVE"),
                                  update_resource=bench_utils.
                                  get_from_manager(),
                                  timeout=600, check_interval=3)
                   for server in servers]
        return servers

    @classmethod
    def _generate_random_name(cls, length):
        return ''.join(random.choice(string.lowercase) for i in range(length))
