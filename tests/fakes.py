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

import uuid

from novaclient import exceptions
from rally.benchmark import base
from rally import utils as rally_utils


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

    def __init__(self, manager=None):
        super(FakeSecurityGroup, self).__init__(manager)
        self.rules = []


class FakeSecurityGroupRule(FakeResource):
    def __init__(self, name, **kwargs):
        super(FakeSecurityGroupRule, self).__init__(name)
        for key, value in kwargs.items():
            setattr(self, key, value)


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

    def get(self, resource_uuid):
        return self.cache.get(resource_uuid, None)

    def delete(self, resource):
        cached = self.get(resource.uuid)
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

    def find(self, **kwargs):
        for resource in self.cache.values():
            match = True
            for key, value in kwargs.items():
                if getattr(resource, key, None) != value:
                    match = False
                    break
            if match:
                return resource


class FakeServerManager(FakeManager):

    def __init__(self, image_mgr=None):
        super(FakeServerManager, self).__init__()
        self.images = image_mgr or FakeImageManager()

    def get(self, resource_uuid):
        server = self.cache.get(resource_uuid, None)
        if server is not None:
            return server
        raise exceptions.NotFound("Server %s not found" % (resource_uuid))

    def _create(self, server_class=FakeServer, name=None):
        server = self._cache(server_class(self))
        if name is not None:
            server.name = name
        return server

    def create(self, name, image_id, flavor_id, **kwargs):
        return self._create(name=name)

    def create_image(self, server, name):
        image = self.images.create()
        return image.uuid

    def add_floating_ip(self, server, fip):
        pass

    def remove_floating_ip(self, server, fip):
        pass


class FakeFailedServerManager(FakeServerManager):

    def create(self, name, image_id, flavor_id, **kwargs):
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

    def create(self, name, public_key=None):
        kp = FakeKeypair(self)
        kp.name = name or kp.name
        return self._cache(kp)


class FakeSecurityGroupManager(FakeManager):

    def __init__(self):
        super(FakeSecurityGroupManager, self).__init__()
        self.create('default')

    def create(self, name, description=""):
        sg = FakeSecurityGroup(self)
        sg.name = name or sg.name
        sg.description = description
        return self._cache(sg)


class FakeSecurityGroupRuleManager(FakeManager):

    def __init__(self):
        super(FakeSecurityGroupRuleManager, self).__init__()

    def create(self, name, **kwargs):
        sgr = FakeSecurityGroupRule(self, **kwargs)
        sgr.name = name or sgr.name
        return self._cache(sgr)


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


class FakeServiceCatalog(object):
    def get_endpoints(self):
        return {'image': [{'publicURL': 'http://fake.to'}]}


class FakeGlanceClient(object):

    def __init__(self, nova_client=None):
        if nova_client:
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
        self.security_group_rules = FakeSecurityGroupRuleManager()


class FakeKeystoneClient(object):

    def __init__(self):
        self.tenants = FakeTenantsManager()
        self.users = FakeUsersManager()
        self.project_id = 'abc123'
        self.auth_token = 'fake'
        self.service_catalog = FakeServiceCatalog()

    def authenticate(self):
        return True


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


class FakeScenario(base.Scenario):

    idle_time = 0

    @classmethod
    def class_init(cls, endpoints):
        pass

    @classmethod
    def do_it(cls, **kwargs):
        pass

    @classmethod
    def too_long(cls, **kwargs):
        pass

    @classmethod
    def something_went_wrong(cls, **kwargs):
        raise Exception("Something went wrong")


class FakeTimer(rally_utils.Timer):

    def duration(self):
        return 10
