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
import uuid

from novaclient import exceptions
from rally.benchmark.scenarios.nova import utils
from rally import exceptions as rally_exceptions
from rally import test


# NOTE(msdubov): A set of 'Fake' classes below is of great use in the test case
#                for utils and also in the test cases for bechmark scenarios.


class FakeResource(object):

    def __init__(self, manager=None):
        self.name = uuid.uuid4()
        self.status = "ACTIVE"
        self.manager = manager
        self.uuid = uuid.uuid4()

    def __getattr__(self, name):
        # NOTE(msdubov): e.g. server.delete() -> manager.delete(server)
        def manager_func(*args, **kwargs):
            getattr(self.manager, name)(self, *args, **kwargs)
        return manager_func


class FakeServer(FakeResource):

    def __init__(self, manager=None):
        super(FakeServer, self).__init__(manager)

    def suspend(self):
        self.status = "SUSPENDED"


class FakeFailedServer(FakeResource):

    def __init__(self, manager=None):
        super(FakeFailedServer, self).__init__(manager)
        self.status = "ERROR"


class FakeImage(FakeResource):
    pass


class FakeFloatingIP(FakeResource):
    pass


class FakeManager(object):

    def __init__(self):
        super(FakeManager, self).__init__()
        self.cache = {}

    def get(self, resource):
        if resource == 'img_uuid':
            return 'img_uuid'
        return self.cache.get(resource.uuid, None)

    def delete(self, resource):
        cached = self.cache.get(resource.uuid, None)
        if cached is not None:
            del self.cache[cached.uuid]

    def _cache(self, resource):
        self.cache[resource.uuid] = resource
        return resource

    def list(self, **kwargs):
        resources = []
        for uuid in self.cache.keys():
            resources.append(self.cache[uuid])
        return resources


class FakeServerManager(FakeManager):

    def __init__(self):
        super(FakeServerManager, self).__init__()

    def get(self, resource):
        server = self.cache.get(resource.uuid, None)
        if server is not None:
            return server
        raise exceptions.NotFound("Server %s not found" % (resource.name))

    def _create(self, server_class=FakeServer, name=None):
        server = self._cache(server_class(self))
        if name is not None:
            server.name = name
        return server

    def create(self, name, image_id, flavor_id):
        return self._create(name=name)

    def create_image(self, server, name):
        return "img_uuid"

    def add_floating_ip(self, server, fip):
        pass

    def remove_floating_ip(self, server, fip):
        pass


class FakeFailedServerManager(FakeServerManager):

    def create(self, name, image_id, flavor_id):
        return self._create(FakeFailedServer, name)


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

    def setUp(self):
        super(NovaScenarioTestCase, self).setUp()
        self.rally_utils = "rally.benchmark.scenarios.nova.utils.utils"
        self.utils_resource_is = "rally.benchmark.scenarios.nova.utils"\
            "._resource_is"
        self.osclients = "rally.benchmark.base.osclients"
        self.nova_scenario = "rally.benchmark.scenarios.nova.utils."\
            "NovaScenario"
        self.servers_create = ("rally.benchmark.scenarios.nova.utils"
                               ".NovaScenario.nova.servers.create")
        self.sleep = "rally.benchmark.scenarios.nova.utils.time.sleep"

    def test_generate_random_name(self):
        for length in [8, 16, 32, 64]:
            name = utils.NovaScenario._generate_random_name(length)
            self.assertEqual(len(name), length)
            self.assertTrue(name.isalpha())

    def test_failed_server_status(self):
        server_manager = FakeFailedServerManager()
        self.assertRaises(rally_exceptions.GetResourceFailure,
                          utils._get_from_manager,
                          server_manager.create('fails', '1', '2'))

    def test_cleanup_failed(self):
        with mock.patch(self.osclients) as mock_osclients:
            mock_osclients.Clients.return_value = FakeClients()
            keys = ["admin_username", "admin_password",
                    "admin_tenant_name", "uri"]
            kw = dict(zip(keys, keys))
            utils.NovaScenario.class_init(kw)

            manager = FakeFailedServerManager()
            utils.NovaScenario.nova.servers = manager

            # NOTE(boden): verify failed server cleanup
            self.assertRaises(rally_exceptions.GetResourceFailure,
                              utils.NovaScenario._boot_server, "fails", 0, 1)
            self.assertEquals(len(manager.list()), 1, "Server not created")
            utils.NovaScenario.cleanup({})
            self.assertEquals(len(manager.list()), 0, "Servers not purged")

    def test_cleanup(self):
        with mock.patch(self.osclients) as mock_osclients:
            mock_osclients.Clients.return_value = FakeClients()
            keys = ["admin_username", "admin_password",
                    "admin_tenant_name", "uri"]
            kw = dict(zip(keys, keys))
            utils.NovaScenario.class_init(kw)

            # NOTE(boden): verify active server cleanup
            manager = FakeServerManager()
            utils.NovaScenario.nova.servers = manager
            for i in range(5):
                utils.NovaScenario._boot_server("server-%s" % i, 0, 1)
            self.assertEquals(len(manager.list()), 5, "Server not created")
            utils.NovaScenario.cleanup({})
            self.assertEquals(len(manager.list()), 0, "Servers not purged")

    def test_server_helper_methods(self):

        with mock.patch(self.rally_utils) as mock_rally_utils:
            with mock.patch(self.utils_resource_is) as mock_resource_is:
                mock_resource_is.return_value = {}
                with mock.patch(self.osclients) as mock_osclients:
                    mock_osclients.Clients.return_value = FakeClients()
                    keys = ["admin_username", "admin_password",
                            "admin_tenant_name", "uri"]
                    kw = dict(zip(keys, keys))
                    utils.NovaScenario.class_init(kw)
                    with mock.patch(self.servers_create) as mock_create:
                        fake_server = FakeServerManager().create("s1", "i1", 1)
                        mock_create.return_value = fake_server
                        with mock.patch(self.sleep):
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
