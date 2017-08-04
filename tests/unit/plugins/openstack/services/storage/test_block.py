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

from rally.plugins.openstack.services.storage import block
from tests.unit import test


class BlockTestCase(test.TestCase):
    def setUp(self):
        super(BlockTestCase, self).setUp()
        self.clients = mock.MagicMock()
        self.service = self._get_service_with_fake_impl()

    def _get_service_with_fake_impl(self):
        path = "rally.plugins.openstack.services.storage.block"
        path = "%s.BlockStorage.discover_impl" % path
        with mock.patch(path) as mock_discover:
            mock_discover.return_value = mock.MagicMock(), None
            service = block.BlockStorage(self.clients)
        return service

    def test_create_volume(self):
        self.assertEqual(self.service._impl.create_volume.return_value,
                         self.service.create_volume("fake_volume"))
        self.service._impl.create_volume.assert_called_once_with(
            "fake_volume", availability_zone=None, consistencygroup_id=None,
            description=None, group_id=None, imageRef=None, metadata=None,
            multiattach=False, name=None, project_id=None,
            scheduler_hints=None, snapshot_id=None, source_replica=None,
            source_volid=None, user_id=None, volume_type=None)

    def test_list_volumes(self):
        self.assertEqual(self.service._impl.list_volumes.return_value,
                         self.service.list_volumes(detailed=True))
        self.service._impl.list_volumes.assert_called_once_with(detailed=True)

    def test_get_volume(self):
        self.assertTrue(self.service._impl.get_volume.return_value,
                        self.service.get_volume(1))
        self.service._impl.get_volume.assert_called_once_with(1)

    def test_update_volume(self):
        self.assertTrue(self.service._impl.update_volume.return_value,
                        self.service.update_volume(1, name="name",
                                                   description="desp"))
        self.service._impl.update_volume.assert_called_once_with(
            1, name="name", description="desp")

    def test_delete_volume(self):
        self.service.delete_volume("volume")
        self.service._impl.delete_volume.assert_called_once_with("volume")

    def test_extend_volume(self):
        self.assertEqual(self.service._impl.extend_volume.return_value,
                         self.service.extend_volume("volume", new_size=1))
        self.service._impl.extend_volume.assert_called_once_with("volume",
                                                                 new_size=1)

    def test_list_snapshots(self):
        self.assertEqual(self.service._impl.list_snapshots.return_value,
                         self.service.list_snapshots(detailed=True))
        self.service._impl.list_snapshots.assert_called_once_with(
            detailed=True)

    def test_list_types(self):
        self.assertEqual(
            self.service._impl.list_types.return_value,
            self.service.list_types(search_opts=None, is_public=None))
        self.service._impl.list_types.assert_called_once_with(is_public=None,
                                                              search_opts=None)

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
            "volume", keys, delete_size=3, deletes=10)

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
        spaces = {"consumer": "both",
                  "write_iops_sec": "10",
                  "read_iops_sec": "1000"}

        self.assertEqual(
            self.service._impl.create_qos.return_value,
            self.service.create_qos(spaces)
        )
        self.service._impl.create_qos.assert_called_once_with(spaces)

    def test_list_qos(self):
        self.assertEqual(
            self.service._impl.list_qos.return_value,
            self.service.list_qos(True)
        )
        self.service._impl.list_qos.assert_called_once_with(True)

    def test_get_qos(self):
        self.assertEqual(
            self.service._impl.get_qos.return_value,
            self.service.get_qos("qos"))
        self.service._impl.get_qos.assert_called_once_with("qos")

    def test_set_qos(self):
        set_specs_args = {"test": "foo"}
        self.assertEqual(
            self.service._impl.set_qos.return_value,
            self.service.set_qos(qos="qos", set_specs_args=set_specs_args))
        self.service._impl.set_qos.assert_called_once_with(
            qos="qos", set_specs_args=set_specs_args)

    def test_qos_associate_type(self):
        self.assertEqual(
            self.service._impl.qos_associate_type.return_value,
            self.service.qos_associate_type(qos_specs="fake_qos",
                                            volume_type="fake_type"))
        self.service._impl.qos_associate_type.assert_called_once_with(
            "fake_qos", "fake_type")

    def test_qos_disassociate_type(self):
        self.assertEqual(
            self.service._impl.qos_disassociate_type.return_value,
            self.service.qos_disassociate_type(qos_specs="fake_qos",
                                               volume_type="fake_type"))
        self.service._impl.qos_disassociate_type.assert_called_once_with(
            "fake_qos", "fake_type")

    def test_create_snapshot(self):
        self.assertEqual(
            self.service._impl.create_snapshot.return_value,
            self.service.create_snapshot(1, force=False, name=None,
                                         description=None, metadata=None))
        self.service._impl.create_snapshot.assert_called_once_with(
            1, force=False, name=None, description=None, metadata=None)

    def test_delete_snapshot(self):
        self.service.delete_snapshot("snapshot")
        self.service._impl.delete_snapshot.assert_called_once_with("snapshot")

    def test_create_backup(self):
        self.assertEqual(
            self.service._impl.create_backup.return_value,
            self.service.create_backup(1, container=None,
                                       name=None, description=None,
                                       incremental=False, force=False,
                                       snapshot_id=None))
        self.service._impl.create_backup.assert_called_once_with(
            1, container=None, name=None, description=None, incremental=False,
            force=False, snapshot_id=None)

    def test_delete_backup(self):
        self.service.delete_backup("backup")
        self.service._impl.delete_backup.assert_called_once_with("backup")

    def test_restore_backup(self):
        self.assertEqual(self.service._impl.restore_backup.return_value,
                         self.service.restore_backup(1, volume_id=1))
        self.service._impl.restore_backup.assert_called_once_with(
            1, volume_id=1)

    def test_list_backups(self):
        self.assertEqual(self.service._impl.list_backups.return_value,
                         self.service.list_backups(detailed=True))
        self.service._impl.list_backups.assert_called_once_with(detailed=True)

    def test_list_transfers(self):
        self.assertEqual(
            self.service._impl.list_transfers.return_value,
            self.service.list_transfers(detailed=True, search_opts=None))
        self.service._impl.list_transfers.assert_called_once_with(
            detailed=True, search_opts=None)

    def test_create_volume_type(self):
        self.assertEqual(
            self.service._impl.create_volume_type.return_value,
            self.service.create_volume_type(name="type",
                                            description=None,
                                            is_public=True))
        self.service._impl.create_volume_type.assert_called_once_with(
            name="type", description=None, is_public=True)

    def test_get_volume_type(self):
        self.assertEqual(
            self.service._impl.get_volume_type.return_value,
            self.service.get_volume_type("volume_type"))
        self.service._impl.get_volume_type.assert_called_once_with(
            "volume_type")

    def test_delete_volume_type(self):
        self.service.delete_volume_type("volume_type")
        self.service._impl.delete_volume_type.assert_called_once_with(
            "volume_type")

    def test_set_volume_type_keys(self):
        self.assertEqual(
            self.service._impl.set_volume_type_keys.return_value,
            self.service.set_volume_type_keys("volume_type",
                                              metadata="metadata"))
        self.service._impl.set_volume_type_keys.assert_called_once_with(
            "volume_type", "metadata")

    def test_transfer_create(self):
        self.assertEqual(self.service._impl.transfer_create.return_value,
                         self.service.transfer_create(1, name="t"))
        self.service._impl.transfer_create.assert_called_once_with(
            1, name="t")

    def test_transfer_accept(self):
        self.assertEqual(self.service._impl.transfer_accept.return_value,
                         self.service.transfer_accept(1, auth_key=2))
        self.service._impl.transfer_accept.assert_called_once_with(
            1, auth_key=2)

    def test_create_encryption_type(self):
        self.assertEqual(
            self.service._impl.create_encryption_type.return_value,
            self.service.create_encryption_type("type", specs=2))
        self.service._impl.create_encryption_type.assert_called_once_with(
            "type", specs=2)

    def test_get_encryption_type(self):
        self.assertEqual(
            self.service._impl.get_encryption_type.return_value,
            self.service.get_encryption_type("type"))
        self.service._impl.get_encryption_type.assert_called_once_with(
            "type")

    def test_list_encryption_type(self):
        self.assertEqual(self.service._impl.list_encryption_type.return_value,
                         self.service.list_encryption_type(search_opts=None))
        self.service._impl.list_encryption_type.assert_called_once_with(
            search_opts=None)

    def test_delete_encryption_type(self):
        self.service.delete_encryption_type("type")
        self.service._impl.delete_encryption_type.assert_called_once_with(
            "type")

    def test_update_encryption_type(self):
        self.assertEqual(
            self.service._impl.update_encryption_type.return_value,
            self.service.update_encryption_type("type", specs=3))
        self.service._impl.update_encryption_type.assert_called_once_with(
            "type", specs=3)
