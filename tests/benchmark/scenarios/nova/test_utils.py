# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

import mock

from rally.benchmark.scenarios.nova import utils
from rally import test


# NOTE(msdubov): A set of 'Fake' classes below is of great use in the test case
#                for utils and also in the test cases for bechmark scenarios.


class FakeResource(object):

    def __init__(self, manager=None):
        self.name = "resource"
        self.status = "ACTIVE"
        self.manager = manager

    def __getattr__(self, name):
        # NOTE(msdubov): e.g. server.delete() -> manager.delete(server)
        def manager_func(*args, **kwargs):
            getattr(self.manager, name)(self, *args, **kwargs)
        return manager_func


class FakeServer(FakeResource):

    def suspend(self):
        self.status = "SUSPENDED"


class FakeImage(FakeResource):
    pass


class FakeFloatingIP(FakeResource):
    pass


class FakeManager(object):

    def get(self, resource):
        return resource

    def delete(self, resource):
        pass


class FakeServerManager(FakeManager):

    def create(self, name, image_id, flavor_id):
        return FakeServer(self)

    def create_image(self, server, name):
        return "img_uuid"

    def add_floating_ip(self, server, fip):
        pass

    def remove_floating_ip(self, server, fip):
        pass


class FakeImageManager(FakeManager):

    def create(self):
        return FakeImage(self)


class FakeFloatingIPsManager(FakeManager):

    def create(self):
        return FakeFloatingIP(self)


class FakeNovaClient(object):

    def __init__(self):
        self.servers = FakeServerManager()
        self.images = FakeImageManager()
        self.floating_ips = FakeFloatingIPsManager()


class FakeClients(object):

    def get_keystone_client(self):
        return "keystone"

    def get_nova_client(self):
        return FakeNovaClient()

    def get_glance_client(self):
        return "glance"

    def get_cinder_client(self):
        return "cinder"


class NovaScenarioTestCase(test.NoDBTestCase):

    def test_generate_random_name(self):
        for length in [8, 16, 32, 64]:
            name = utils.NovaScenario._generate_random_name(length)
            self.assertEqual(len(name), length)
            self.assertTrue(name.isalpha())

    def test_server_helper_methods(self):

        rally_utils = "rally.benchmark.scenarios.nova.utils.utils"
        utils_resource_is = "rally.benchmark.scenarios.nova.utils._resource_is"
        osclients = "rally.benchmark.base.osclients"
        servers_create = ("rally.benchmark.scenarios.nova.utils.NovaScenario."
                          "nova.servers.create")
        sleep = "rally.benchmark.scenarios.nova.utils.time.sleep"

        with mock.patch(rally_utils) as mock_rally_utils:
            with mock.patch(utils_resource_is) as mock_resource_is:
                mock_resource_is.return_value = {}
                with mock.patch(osclients) as mock_osclients:
                    mock_osclients.Clients.return_value = FakeClients()
                    keys = ["admin_username", "admin_password",
                            "admin_tenant_name", "uri"]
                    kw = dict(zip(keys, keys))
                    utils.NovaScenario.class_init(kw)
                    with mock.patch(servers_create) as mock_create:
                        fake_server = FakeServerManager().create("s1", "i1", 1)
                        mock_create.return_value = fake_server
                        with mock.patch(sleep):
                            utils.NovaScenario._boot_server("s1", "i1", 1)
                            utils.NovaScenario._create_image(fake_server)
                            utils.NovaScenario._suspend_server(fake_server)
                            utils.NovaScenario._delete_server(fake_server)

        expected = [
            mock.call.wait_for(fake_server, is_ready={},
                               update_resource=utils._get_from_manager,
                               timeout=600, check_interval=3),
            mock.call.wait_for("img_uuid", is_ready={},
                               update_resource=utils._get_from_manager,
                               timeout=600, check_interval=3),
            mock.call.wait_for(fake_server, is_ready={},
                               update_resource=utils._get_from_manager,
                               timeout=600, check_interval=3),
            mock.call.wait_for(fake_server, is_ready=utils._false,
                               update_resource=utils._get_from_manager,
                               timeout=600, check_interval=3)
        ]

        self.assertEqual(mock_rally_utils.mock_calls, expected)
