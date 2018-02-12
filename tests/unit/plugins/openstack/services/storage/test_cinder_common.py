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

import ddt
import mock

from rally.common import cfg
from rally import exceptions
from rally.plugins.openstack import service
from rally.plugins.openstack.services.storage import block
from rally.plugins.openstack.services.storage import cinder_common
from tests.unit import fakes
from tests.unit import test

BASE_PATH = "rally.plugins.openstack.services.storage"
CONF = cfg.CONF


class FullCinder(service.Service, cinder_common.CinderMixin):
    """Implementation of CinderMixin with Service base class."""
    pass


@ddt.ddt
class CinderMixinTestCase(test.ScenarioTestCase):
    def setUp(self):
        super(CinderMixinTestCase, self).setUp()
        self.clients = mock.MagicMock()
        self.cinder = self.clients.cinder.return_value
        self.name_generator = uuid.uuid1
        self.version = "some"
        self.service = FullCinder(
            clients=self.clients, name_generator=self.name_generator)
        self.service.version = self.version

    def atomic_actions(self):
        return self.service._atomic_actions

    def test__get_client(self):
        self.assertEqual(self.cinder,
                         self.service._get_client())

    def test__update_resource_with_manage(self):
        resource = mock.MagicMock(id=1, manager=mock.MagicMock())
        self.assertEqual(resource.manager.get.return_value,
                         self.service._update_resource(resource))
        resource.manager.get.assert_called_once_with(
            resource.id)

    @ddt.data({"resource": block.Volume(id=1, name="vol",
                                        size=1, status="st"),
               "attr": "volumes"},
              {"resource": block.VolumeSnapshot(id=2, name="snapshot",
                                                volume_id=1, status="st"),
               "attr": "volume_snapshots"},
              {"resource": block.VolumeBackup(id=3, name="backup",
                                              volume_id=1, status="st"),
               "attr": "backups"})
    @ddt.unpack
    def test__update_resource_with_no_manage(self, resource, attr):
        self.assertEqual(getattr(self.cinder, attr).get.return_value,
                         self.service._update_resource(resource))
        getattr(self.cinder, attr).get.assert_called_once_with(
            resource.id)

    def test__update_resource_with_not_found(self):
        manager = mock.MagicMock()
        resource = fakes.FakeResource(manager=manager, status="ERROR")

        class NotFoundException(Exception):
            http_status = 404

        manager.get = mock.MagicMock(side_effect=NotFoundException)
        self.assertRaises(exceptions.GetResourceNotFound,
                          self.service._update_resource, resource)

    def test__update_resource_with_http_exception(self):
        manager = mock.MagicMock()
        resource = fakes.FakeResource(manager=manager, status="ERROR")

        class HTTPException(Exception):
            pass

        manager.get = mock.MagicMock(side_effect=HTTPException)
        self.assertRaises(exceptions.GetResourceFailure,
                          self.service._update_resource, resource)

    def test__wait_available_volume(self):
        volume = fakes.FakeVolume()
        self.assertEqual(self.mock_wait_for_status.mock.return_value,
                         self.service._wait_available_volume(volume))

        self.mock_wait_for_status.mock.assert_called_once_with(
            volume,
            ready_statuses=["available"],
            update_resource=self.service._update_resource,
            timeout=CONF.openstack.cinder_volume_create_timeout,
            check_interval=CONF.openstack.cinder_volume_create_poll_interval
        )

    def test_list_volumes(self):
        self.assertEqual(self.cinder.volumes.list.return_value,
                         self.service.list_volumes())
        self.cinder.volumes.list.assert_called_once_with(True)

    def test_get_volume(self):
        self.assertEqual(self.cinder.volumes.get.return_value,
                         self.service.get_volume(1))
        self.cinder.volumes.get.assert_called_once_with(1)

    @mock.patch("%s.block.BlockStorage.create_volume" % BASE_PATH)
    def test_delete_volume(self, mock_create_volume):
        volume = mock_create_volume.return_value
        self.service.delete_volume(volume)

        self.cinder.volumes.delete.assert_called_once_with(volume)
        self.mock_wait_for_status.mock.assert_called_once_with(
            volume,
            ready_statuses=["deleted"],
            check_deletion=True,
            update_resource=self.service._update_resource,
            timeout=CONF.openstack.cinder_volume_delete_timeout,
            check_interval=CONF.openstack.cinder_volume_delete_poll_interval
        )

    @mock.patch("%s.block.BlockStorage.create_volume" % BASE_PATH)
    def test_extend_volume(self, mock_create_volume):
        volume = mock_create_volume.return_value
        self.service._wait_available_volume = mock.MagicMock()
        self.service._wait_available_volume.return_value = fakes.FakeVolume()

        self.assertEqual(self.service._wait_available_volume.return_value,
                         self.service.extend_volume(volume, 1))

        self.cinder.volumes.extend.assert_called_once_with(volume, 1)
        self.service._wait_available_volume.assert_called_once_with(volume)

    def test_list_snapshots(self):
        self.assertEqual(self.cinder.volume_snapshots.list.return_value,
                         self.service.list_snapshots())
        self.cinder.volume_snapshots.list.assert_called_once_with(True)

    def test_set_metadata(self):
        volume = fakes.FakeVolume()

        self.service.set_metadata(volume, sets=2, set_size=4)
        calls = self.cinder.volumes.set_metadata.call_args_list
        self.assertEqual(2, len(calls))
        for call in calls:
            call_volume, metadata = call[0]
            self.assertEqual(volume, call_volume)
            self.assertEqual(4, len(metadata))

    def test_delete_metadata(self):
        volume = fakes.FakeVolume()

        keys = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"]
        self.service.delete_metadata(volume, keys, deletes=3, delete_size=4)
        calls = self.cinder.volumes.delete_metadata.call_args_list
        self.assertEqual(3, len(calls))
        all_deleted = []
        for call in calls:
            call_volume, del_keys = call[0]
            self.assertEqual(volume, call_volume)
            self.assertEqual(4, len(del_keys))
            for key in del_keys:
                self.assertIn(key, keys)
                self.assertNotIn(key, all_deleted)
                all_deleted.append(key)

    def test_delete_metadata_not_enough_keys(self):
        volume = fakes.FakeVolume()

        keys = ["a", "b", "c", "d", "e"]
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.service.delete_metadata,
                          volume, keys, deletes=2, delete_size=3)

    def test_update_readonly_flag(self):
        fake_volume = mock.MagicMock()
        self.service.update_readonly_flag(fake_volume, "fake_flag")
        self.cinder.volumes.update_readonly_flag.assert_called_once_with(
            fake_volume, "fake_flag")

    @mock.patch("rally.plugins.openstack.services.image.image.Image")
    def test_upload_volume_to_image(self, mock_image):
        volume = mock.Mock()
        image = {"os-volume_upload_image": {"image_id": 1}}
        self.cinder.volumes.upload_to_image.return_value = (None, image)
        glance = mock_image.return_value

        self.service.generate_random_name = mock.Mock(
            return_value="test_vol")
        self.service.upload_volume_to_image(volume, False,
                                            "container", "disk")

        self.cinder.volumes.upload_to_image.assert_called_once_with(
            volume, False, "test_vol", "container", "disk")
        self.mock_wait_for_status.mock.assert_has_calls([
            mock.call(
                volume,
                ready_statuses=["available"],
                update_resource=self.service._update_resource,
                timeout=CONF.openstack.cinder_volume_create_timeout,
                check_interval=CONF.openstack.
                cinder_volume_create_poll_interval),
            mock.call(
                glance.get_image.return_value,
                ready_statuses=["active"],
                update_resource=glance.get_image,
                timeout=CONF.openstack.glance_image_create_timeout,
                check_interval=CONF.openstack.
                glance_image_create_poll_interval)
        ])
        glance.get_image.assert_called_once_with(1)

    def test_create_qos(self):
        specs = {"consumer": "both",
                 "write_iops_sec": "10",
                 "read_iops_sec": "1000"}
        random_name = "random_name"
        self.service.generate_random_name = mock.MagicMock(
            return_value=random_name)

        result = self.service.create_qos(specs)
        self.assertEqual(
            self.cinder.qos_specs.create.return_value,
            result
        )
        self.cinder.qos_specs.create.assert_called_once_with(random_name,
                                                             specs)

    def test_list_qos(self):
        result = self.service.list_qos(True)
        self.assertEqual(
            self.cinder.qos_specs.list.return_value,
            result
        )
        self.cinder.qos_specs.list.assert_called_once_with(True)

    def test_get_qos(self):
        result = self.service.get_qos("qos")
        self.assertEqual(
            self.cinder.qos_specs.get.return_value,
            result)
        self.cinder.qos_specs.get.assert_called_once_with("qos")

    def test_set_qos(self):
        set_specs_args = {"test": "foo"}
        result = self.service.set_qos("qos", set_specs_args)
        self.assertEqual(
            self.cinder.qos_specs.set_keys.return_value,
            result)
        self.cinder.qos_specs.set_keys.assert_called_once_with("qos",
                                                               set_specs_args)

    def test_qos_associate_type(self):
        self.service.qos_associate_type("qos", "type_id")
        self.cinder.qos_specs.associate.assert_called_once_with(
            "qos", "type_id")

    def test_qos_disassociate_type(self):
        self.service.qos_disassociate_type("qos", "type_id")
        self.cinder.qos_specs.disassociate.assert_called_once_with(
            "qos", "type_id")

    def test_delete_snapshot(self):
        snapshot = mock.Mock()
        self.service.delete_snapshot(snapshot)
        self.cinder.volume_snapshots.delete.assert_called_once_with(snapshot)
        self.mock_wait_for_status.mock.assert_called_once_with(
            snapshot,
            ready_statuses=["deleted"],
            check_deletion=True,
            update_resource=self.service._update_resource,
            timeout=cfg.CONF.openstack.cinder_volume_create_timeout,
            check_interval=cfg.CONF.openstack
            .cinder_volume_create_poll_interval)

    def test_delete_backup(self):
        backup = mock.Mock()
        self.service.delete_backup(backup)
        self.cinder.backups.delete.assert_called_once_with(backup)
        self.mock_wait_for_status.mock.assert_called_once_with(
            backup,
            ready_statuses=["deleted"],
            check_deletion=True,
            update_resource=self.service._update_resource,
            timeout=cfg.CONF.openstack.cinder_volume_create_timeout,
            check_interval=cfg.CONF.openstack
            .cinder_volume_create_poll_interval)

    def test_restore_backup(self):
        backup = mock.Mock()
        self.service._wait_available_volume = mock.MagicMock()
        self.service._wait_available_volume.return_value = mock.Mock()

        return_restore = self.service.restore_backup(backup.id, None)

        self.cinder.restores.restore.assert_called_once_with(backup.id, None)
        self.cinder.volumes.get.assert_called_once_with(
            self.cinder.restores.restore.return_value.volume_id)
        self.service._wait_available_volume.assert_called_once_with(
            self.cinder.volumes.get.return_value)
        self.assertEqual(self.service._wait_available_volume.return_value,
                         return_restore)

    def test_list_backups(self):
        return_backups_list = self.service.list_backups()
        self.assertEqual(
            self.cinder.backups.list.return_value,
            return_backups_list)

    def test_list_transfers(self):
        return_transfers_list = self.service.list_transfers()
        self.assertEqual(
            self.cinder.transfers.list.return_value,
            return_transfers_list)

    def test_get_volume_type(self):
        self.assertEqual(self.cinder.volume_types.get.return_value,
                         self.service.get_volume_type("volume_type"))
        self.cinder.volume_types.get.assert_called_once_with(
            "volume_type")

    def test_delete_volume_type(self):
        volume_type = mock.Mock()
        self.service.delete_volume_type(volume_type)
        self.cinder.volume_types.delete.assert_called_once_with(
            volume_type)

    def test_set_volume_type_keys(self):
        volume_type = mock.Mock()
        self.assertEqual(volume_type.set_keys.return_value,
                         self.service.set_volume_type_keys(
                             volume_type, metadata="metadata"))

        volume_type.set_keys.assert_called_once_with("metadata")

    def test_transfer_create(self):
        fake_volume = mock.MagicMock()
        random_name = "random_name"
        self.service.generate_random_name = mock.MagicMock(
            return_value=random_name)
        result = self.service.transfer_create(fake_volume.id)
        self.assertEqual(
            self.cinder.transfers.create.return_value,
            result)
        self.cinder.transfers.create.assert_called_once_with(
            fake_volume.id, name=random_name)

    def test_transfer_create_with_name(self):
        fake_volume = mock.MagicMock()
        result = self.service.transfer_create(fake_volume.id, name="t")
        self.assertEqual(
            self.cinder.transfers.create.return_value,
            result)
        self.cinder.transfers.create.assert_called_once_with(
            fake_volume.id, name="t")

    def test_transfer_accept(self):
        fake_transfer = mock.MagicMock()
        result = self.service.transfer_accept(fake_transfer.id, "fake_key")
        self.assertEqual(
            self.cinder.transfers.accept.return_value,
            result)
        self.cinder.transfers.accept.assert_called_once_with(
            fake_transfer.id, "fake_key")

    def test_create_encryption_type(self):
        volume_type = mock.Mock()
        specs = {
            "provider": "foo_pro",
            "cipher": "foo_cip",
            "key_size": 512,
            "control_location": "foo_con"
        }
        result = self.service.create_encryption_type(volume_type, specs)

        self.assertEqual(
            self.cinder.volume_encryption_types.create.return_value, result)
        self.cinder.volume_encryption_types.create.assert_called_once_with(
            volume_type, specs)

    def test_get_encryption_type(self):
        volume_type = mock.Mock()
        result = self.service.get_encryption_type(volume_type)

        self.assertEqual(
            self.cinder.volume_encryption_types.get.return_value, result)
        self.cinder.volume_encryption_types.get.assert_called_once_with(
            volume_type)

    def test_list_encryption_type(self):
        return_encryption_types_list = self.service.list_encryption_type()
        self.assertEqual(self.cinder.volume_encryption_types.list.return_value,
                         return_encryption_types_list)

    def test_delete_encryption_type(self):
        resp = mock.MagicMock(status_code=202)
        self.cinder.volume_encryption_types.delete.return_value = [resp]
        self.service.delete_encryption_type("type")
        self.cinder.volume_encryption_types.delete.assert_called_once_with(
            "type")

    def test_delete_encryption_type_raise(self):
        resp = mock.MagicMock(status_code=404)
        self.cinder.volume_encryption_types.delete.return_value = [resp]
        self.assertRaises(exceptions.RallyException,
                          self.service.delete_encryption_type, "type")
        self.cinder.volume_encryption_types.delete.assert_called_once_with(
            "type")

    def test_update_encryption_type(self):
        volume_type = mock.Mock()
        specs = {
            "provider": "foo_pro",
            "cipher": "foo_cip",
            "key_size": 512,
            "control_location": "foo_con"
        }
        result = self.service.update_encryption_type(volume_type, specs)

        self.assertEqual(
            self.cinder.volume_encryption_types.update.return_value, result)
        self.cinder.volume_encryption_types.update.assert_called_once_with(
            volume_type, specs)


class FullUnifiedCinder(cinder_common.UnifiedCinderMixin,
                        service.Service):
    """Implementation of UnifiedCinderMixin with Service base class."""
    pass


class UnifiedCinderMixinTestCase(test.TestCase):
    def setUp(self):
        super(UnifiedCinderMixinTestCase, self).setUp()
        self.clients = mock.MagicMock()
        self.name_generator = mock.MagicMock()
        self.impl = mock.MagicMock()
        self.version = "some"
        self.service = FullUnifiedCinder(
            clients=self.clients, name_generator=self.name_generator)
        self.service._impl = self.impl
        self.service.version = self.version

    def test__unify_backup(self):
        class SomeBackup(object):
            id = 1
            name = "backup"
            volume_id = "volume"
            status = "st"
        backup = self.service._unify_backup(SomeBackup())
        self.assertEqual(1, backup.id)
        self.assertEqual("backup", backup.name)
        self.assertEqual("volume", backup.volume_id)
        self.assertEqual("st", backup.status)

    def test__unify_transfer(self):
        class SomeTransfer(object):
            id = 1
            name = "transfer"
            volume_id = "volume"
            status = "st"
        transfer = self.service._unify_backup(SomeTransfer())
        self.assertEqual(1, transfer.id)
        self.assertEqual("transfer", transfer.name)
        self.assertEqual("volume", transfer.volume_id)
        self.assertEqual("st", transfer.status)

    def test__unify_qos(self):
        class Qos(object):
            id = 1
            name = "qos"
            specs = {"key1": "value1"}
        qos = self.service._unify_qos(Qos())
        self.assertEqual(1, qos.id)
        self.assertEqual("qos", qos.name)
        self.assertEqual({"key1": "value1"}, qos.specs)

    def test__unify_encryption_type(self):
        class SomeEncryptionType(object):
            encryption_id = 1
            volume_type_id = "volume_type"
        encryption_type = self.service._unify_encryption_type(
            SomeEncryptionType())
        self.assertEqual(1, encryption_type.id)
        self.assertEqual("volume_type", encryption_type.volume_type_id)

    def test_delete_volume(self):
        self.service.delete_volume("volume")
        self.service._impl.delete_volume.assert_called_once_with("volume")

    def test_set_metadata(self):
        self.assertEqual(
            self.service._impl.set_metadata.return_value,
            self.service.set_metadata("volume", sets=10, set_size=3))
        self.service._impl.set_metadata.assert_called_once_with(
            "volume", set_size=3, sets=10)

    def test_delete_metadata(self):
        keys = ["a", "b"]
        self.service.delete_metadata("volume", keys=keys, deletes=10,
                                     delete_size=3)
        self.service._impl.delete_metadata.assert_called_once_with(
            "volume", keys=keys, delete_size=3, deletes=10)

    def test_update_readonly_flag(self):
        self.assertEqual(
            self.service._impl.update_readonly_flag.return_value,
            self.service.update_readonly_flag("volume", read_only=True))
        self.service._impl.update_readonly_flag.assert_called_once_with(
            "volume", read_only=True)

    def test_upload_volume_to_image(self):
        self.assertEqual(
            self.service._impl.upload_volume_to_image.return_value,
            self.service.upload_volume_to_image("volume",
                                                force=False,
                                                container_format="bare",
                                                disk_format="raw"))
        self.service._impl.upload_volume_to_image.assert_called_once_with(
            "volume", container_format="bare", disk_format="raw", force=False)

    def test_create_qos(self):
        specs = {"consumer": "both",
                 "write_iops_sec": "10",
                 "read_iops_sec": "1000"}
        self.service._unify_qos = mock.MagicMock()
        self.assertEqual(
            self.service._unify_qos.return_value,
            self.service.create_qos(specs)
        )
        self.service._impl.create_qos.assert_called_once_with(specs)
        self.service._unify_qos.assert_called_once_with(
            self.service._impl.create_qos.return_value
        )

    def test_list_qos(self):
        self.service._unify_qos = mock.MagicMock()
        self.service._impl.list_qos.return_value = ["qos"]
        self.assertEqual(
            [self.service._unify_qos.return_value],
            self.service.list_qos(True)
        )
        self.service._impl.list_qos.assert_called_once_with(True)
        self.service._unify_qos.assert_called_once_with("qos")

    def test_get_qos(self):
        self.service._unify_qos = mock.MagicMock()
        self.assertEqual(
            self.service._unify_qos.return_value,
            self.service.get_qos("qos"))
        self.service._impl.get_qos.assert_called_once_with("qos")
        self.service._unify_qos.assert_called_once_with(
            self.service._impl.get_qos.return_value
        )

    def test_set_qos(self):
        set_specs_args = {"test": "foo"}
        self.service._unify_qos = mock.MagicMock()
        qos = mock.MagicMock()
        self.assertEqual(
            self.service._unify_qos.return_value,
            self.service.set_qos(qos, set_specs_args))
        self.service._impl.set_qos.assert_called_once_with(qos.id,
                                                           set_specs_args)
        self.service._unify_qos.assert_called_once_with(qos)

    def test_qos_associate_type(self):
        self.service._unify_qos = mock.MagicMock()
        self.assertEqual(
            self.service._unify_qos.return_value,
            self.service.qos_associate_type("qos", "type_id"))
        self.service._impl.qos_associate_type.assert_called_once_with(
            "qos", "type_id")
        self.service._unify_qos.assert_called_once_with("qos")

    def test_qos_disassociate_type(self):
        self.service._unify_qos = mock.MagicMock()
        self.assertEqual(
            self.service._unify_qos.return_value,
            self.service.qos_disassociate_type("qos", "type_id"))
        self.service._impl.qos_disassociate_type.assert_called_once_with(
            "qos", "type_id")
        self.service._unify_qos.assert_called_once_with("qos")

    def test_delete_snapshot(self):
        self.service.delete_snapshot("snapshot")
        self.service._impl.delete_snapshot.assert_called_once_with("snapshot")

    def test_delete_backup(self):
        self.service.delete_backup("backup")
        self.service._impl.delete_backup.assert_called_once_with("backup")

    def test_list_backups(self):
        self.service._unify_backup = mock.MagicMock()
        self.service._impl.list_backups.return_value = ["backup"]
        self.assertEqual([self.service._unify_backup.return_value],
                         self.service.list_backups(detailed=True))
        self.service._impl.list_backups.assert_called_once_with(detailed=True)
        self.service._unify_backup.assert_called_once_with(
            "backup")

    def test_list_transfers(self):
        self.service._unify_transfer = mock.MagicMock()
        self.service._impl.list_transfers.return_value = ["transfer"]
        self.assertEqual(
            [self.service._unify_transfer.return_value],
            self.service.list_transfers(detailed=True, search_opts=None))
        self.service._impl.list_transfers.assert_called_once_with(
            detailed=True, search_opts=None)
        self.service._unify_transfer.assert_called_once_with(
            "transfer")

    def test_get_volume_type(self):
        self.assertEqual(self.service._impl.get_volume_type.return_value,
                         self.service.get_volume_type("volume_type"))
        self.service._impl.get_volume_type.assert_called_once_with(
            "volume_type")

    def test_delete_volume_type(self):
        self.assertEqual(self.service._impl.delete_volume_type.return_value,
                         self.service.delete_volume_type("volume_type"))
        self.service._impl.delete_volume_type.assert_called_once_with(
            "volume_type")

    def test_set_volume_type_keys(self):
        self.assertEqual(self.service._impl.set_volume_type_keys.return_value,
                         self.service.set_volume_type_keys(
                             "volume_type", metadata="metadata"))
        self.service._impl.set_volume_type_keys.assert_called_once_with(
            "volume_type", "metadata")

    def test_transfer_create(self):
        self.service._unify_transfer = mock.MagicMock()
        self.assertEqual(self.service._unify_transfer.return_value,
                         self.service.transfer_create(1))
        self.service._impl.transfer_create.assert_called_once_with(
            1, name=None)
        self.service._unify_transfer.assert_called_once_with(
            self.service._impl.transfer_create.return_value)

    def test_transfer_accept(self):
        self.service._unify_transfer = mock.MagicMock()
        self.assertEqual(self.service._unify_transfer.return_value,
                         self.service.transfer_accept(1, auth_key=2))
        self.service._impl.transfer_accept.assert_called_once_with(
            1, auth_key=2)
        self.service._unify_transfer.assert_called_once_with(
            self.service._impl.transfer_accept.return_value)

    def test_create_encryption_type(self):
        self.service._unify_encryption_type = mock.MagicMock()
        self.assertEqual(
            self.service._unify_encryption_type.return_value,
            self.service.create_encryption_type("type", specs=2))
        self.service._impl.create_encryption_type.assert_called_once_with(
            "type", specs=2)
        self.service._unify_encryption_type.assert_called_once_with(
            self.service._impl.create_encryption_type.return_value)

    def test_get_encryption_type(self):
        self.service._unify_encryption_type = mock.MagicMock()
        self.assertEqual(
            self.service._unify_encryption_type.return_value,
            self.service.get_encryption_type("type"))
        self.service._impl.get_encryption_type.assert_called_once_with(
            "type")
        self.service._unify_encryption_type.assert_called_once_with(
            self.service._impl.get_encryption_type.return_value)

    def test_list_encryption_type(self):
        self.service._unify_encryption_type = mock.MagicMock()
        self.service._impl.list_encryption_type.return_value = ["encryption"]
        self.assertEqual([self.service._unify_encryption_type.return_value],
                         self.service.list_encryption_type(search_opts=None))
        self.service._impl.list_encryption_type.assert_called_once_with(
            search_opts=None)
        self.service._unify_encryption_type.assert_called_once_with(
            "encryption")

    def test_delete_encryption_type(self):
        self.service.delete_encryption_type("type")
        self.service._impl.delete_encryption_type.assert_called_once_with(
            "type")

    def test_update_encryption_type(self):
        self.service.update_encryption_type("type", specs=3)
        self.service._impl.update_encryption_type.assert_called_once_with(
            "type", specs=3)
