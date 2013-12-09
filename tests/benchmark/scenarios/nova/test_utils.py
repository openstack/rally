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
from rally.benchmark import utils as butils
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
        self.id = self.uuid

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

    def __init__(self, manager=None):
        super(FakeImage, self).__init__(manager)


class FakeFloatingIP(FakeResource):
    pass


class FakeTenant(FakeResource):
    pass


class FakeUser(FakeResource):
    pass


class FakeNetwork(FakeResource):
    pass


class FakeKeypair(FakeResource):
    pass


class FakeSecurityGroup(FakeResource):
    pass


class FakeVolume(FakeResource):
    pass


class FakeVolumeType(FakeResource):
    pass


class FakeVolumeTransfer(FakeResource):
    pass


class FakeVolumeSnapshot(FakeResource):
    pass


class FakeVolumeBackup(FakeResource):
    pass


class FakeManager(object):

    def __init__(self):
        super(FakeManager, self).__init__()
        self.cache = {}

    def get(self, resource):
        uuid = getattr(resource, 'uuid', None) or resource
        return self.cache.get(uuid, None)

    def delete(self, resource):
        cached = self.get(resource)
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

    def __init__(self, image_mgr=None):
        super(FakeServerManager, self).__init__()
        self.images = image_mgr or FakeImageManager()

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
        image = self.images.create()
        return image.uuid

    def add_floating_ip(self, server, fip):
        pass

    def remove_floating_ip(self, server, fip):
        pass


class FakeFailedServerManager(FakeServerManager):

    def create(self, name, image_id, flavor_id):
        return self._create(FakeFailedServer, name)


class FakeImageManager(FakeManager):

    def create(self):
        return self._cache(FakeImage(self))

    def delete(self, image):
        cached = self.cache.get(image.uuid, None)
        if cached is not None:
            cached.status = "DELETED"


class FakeFloatingIPsManager(FakeManager):

    def create(self):
        return FakeFloatingIP(self)


class FakeTenantsManager(FakeManager):

    def create(self, name):
        return FakeTenant(self)


class FakeNetworkManager(FakeManager):

    def create(self, net_id):
        net = FakeNetwork(self)
        net.id = net_id
        return self._cache(net)


class FakeKeypairManager(FakeManager):

    def create(self, name):
        kp = FakeKeypair(self)
        kp.name = name or kp.name
        return self._cache(kp)


class FakeSecurityGroupManager(FakeManager):

    def create(self, name):
        sg = FakeSecurityGroup(self)
        sg.name = name or sg.name
        return self._cache(sg)


class FakeUsersManager(FakeManager):

    def create(self, username, password, email, tenant_id):
        return FakeUser(self)


class FakeVolumeManager(FakeManager):

    def create(self, name=None):
        volume = FakeVolume(self)
        volume.name = name or volume.name
        return self._cache(volume)


class FakeVolumeTypeManager(FakeManager):

    def create(self, name):
        vol_type = FakeVolumeType(self)
        vol_type.name = name or vol_type.name
        return self._cache(vol_type)


class FakeVolumeTransferManager(FakeManager):

    def create(self, name):
        transfer = FakeVolumeTransfer(self)
        transfer.name = name or transfer.name
        return self._cache(transfer)


class FakeVolumeSnapshotManager(FakeManager):

    def create(self, name):
        snapshot = FakeVolumeSnapshot(self)
        snapshot.name = name or snapshot.name
        return self._cache(snapshot)


class FakeVolumeBackupManager(FakeManager):

    def create(self, name):
        backup = FakeVolumeBackup(self)
        backup.name = name or backup.name
        return self._cache(backup)


class FakeGlanceClient(object):

    def __init__(self, nova_client):
        self.images = nova_client.images


class FakeCinderClient(object):

    def __init__(self):
        self.volumes = FakeVolumeManager()
        self.volume_types = FakeVolumeTypeManager()
        self.transfers = FakeVolumeTransferManager()
        self.volume_snapshots = FakeVolumeSnapshotManager()
        self.backups = FakeVolumeBackupManager()


class FakeNovaClient(object):

    def __init__(self, failed_server_manager=False):
        self.images = FakeImageManager()
        if failed_server_manager:
            self.servers = FakeFailedServerManager(self.images)
        else:
            self.servers = FakeServerManager(self.images)
        self.floating_ips = FakeFloatingIPsManager()
        self.networks = FakeNetworkManager()
        self.keypairs = FakeKeypairManager()
        self.security_groups = FakeSecurityGroupManager()


class FakeKeystoneClient(object):

    def __init__(self):
        self.tenants = FakeTenantsManager()
        self.users = FakeUsersManager()
        self.project_id = 'abc123'


class FakeClients(object):

    def __init__(self):
        self.nova = None
        self.glance = None
        self.keystone = None
        self.cinder = None

    def get_keystone_client(self):
        if self.keystone is not None:
            return self.keystone
        self.keystone = FakeKeystoneClient()
        return self.keystone

    def get_nova_client(self):
        if self.nova is not None:
            return self.nova
        self.nova = FakeNovaClient()
        return self.nova

    def get_glance_client(self):
        if self.glance is not None:
            return self.glance
        self.glance = FakeGlanceClient(self.get_nova_client())
        return self.glance

    def get_cinder_client(self):
        if self.cinder is not None:
            return self.cinder
        self.cinder = FakeCinderClient()
        return self.cinder


class NovaScenarioTestCase(test.TestCase):

    def setUp(self):
        super(NovaScenarioTestCase, self).setUp()

    def test_generate_random_name(self):
        for length in [8, 16, 32, 64]:
            name = utils.NovaScenario._generate_random_name(length)
            self.assertEqual(len(name), length)
            self.assertTrue(name.isalpha())

    def test_failed_server_status(self):
        server_manager = FakeFailedServerManager()
        self.assertRaises(rally_exceptions.GetResourceFailure,
                          butils.get_from_manager(),
                          server_manager.create('fails', '1', '2'))

    @mock.patch("rally.benchmark.scenarios.nova.utils.time.sleep")
    @mock.patch("rally.utils")
    @mock.patch("rally.benchmark.utils.osclients")
    @mock.patch("rally.benchmark.utils.resource_is")
    def test_server_helper_methods(self, mock_ris, mock_osclients,
                                   mock_rally_utils, mock_sleep):

        def _is_ready(resource):
            return resource.status == "ACTIVE"

        mock_ris.return_value = _is_ready
        get_from_mgr = butils.get_from_manager()

        fc = FakeClients()
        mock_osclients.Clients.return_value = fc
        fake_nova = FakeNovaClient()
        fc.get_nova_client = lambda: fake_nova
        fsm = FakeServerManager(fake_nova.images)
        fake_server = fsm.create("s1", "i1", 1)
        fsm.create = lambda name, iid, fid: fake_server
        fake_nova.servers = fsm
        fake_image_id = fsm.create_image(fake_server, 'img')
        fake_image = fsm.images.get(fake_image_id)
        fsm.create_image = lambda svr, name: fake_image
        temp_keys = ["username", "password", "tenant_name", "uri"]
        users_endpoints = [dict(zip(temp_keys, temp_keys))]
        utils.NovaScenario._clients = butils.\
            _create_openstack_clients(users_endpoints, temp_keys)[0]
        utils.utils = mock_rally_utils
        utils.bench_utils.get_from_manager = lambda: get_from_mgr

        utils.NovaScenario._boot_server("s1", "i1", 1)
        utils.NovaScenario._create_image(fake_server)
        utils.NovaScenario._suspend_server(fake_server)
        utils.NovaScenario._delete_server(fake_server)

        expected = [
            mock.call.wait_for(fake_server, is_ready=_is_ready,
                               update_resource=butils.get_from_manager(),
                               check_interval=3, timeout=600),
            mock.call.wait_for(fake_image, is_ready=_is_ready,
                               update_resource=butils.get_from_manager(),
                               check_interval=3, timeout=600),
            mock.call.wait_for(fake_server, is_ready=_is_ready,
                               update_resource=butils.get_from_manager(),
                               check_interval=3, timeout=600),
            mock.call.wait_for(fake_server, is_ready=butils.is_none,
                               update_resource=butils.get_from_manager(),
                               check_interval=3, timeout=600)
        ]

        self.assertEqual(expected, mock_rally_utils.mock_calls)
