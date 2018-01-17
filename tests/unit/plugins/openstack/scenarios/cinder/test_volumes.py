# Copyright 2013 Huawei Technologies Co.,LTD.
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

import ddt
import mock

from rally.plugins.openstack.scenarios.cinder import volumes
from tests.unit import test

CINDER_VOLUMES = ("rally.plugins.openstack.scenarios.cinder.volumes")


@ddt.ddt
class CinderServersTestCase(test.ScenarioTestCase):

    def _get_context(self):
        context = test.get_test_context()
        context.update({
            "admin": {
                "id": "fake_user_id",
                "credential": mock.MagicMock()
            },
            "user": {"id": "fake_user_id",
                     "credential": mock.MagicMock()},
            "tenant": {"id": "fake", "name": "fake",
                       "volumes": [{"id": "uuid", "size": 1}],
                       "servers": [1]}})
        return context

    def setUp(self):
        super(CinderServersTestCase, self).setUp()
        patch = mock.patch(
            "rally.plugins.openstack.services.storage.block.BlockStorage")
        self.addCleanup(patch.stop)
        self.mock_cinder = patch.start()

    def test_create_and_list_volume(self):
        mock_service = self.mock_cinder.return_value
        scenario = volumes.CreateAndListVolume(self._get_context())
        scenario.run(1, True, fakearg="f")

        mock_service.create_volume.assert_called_once_with(1, fakearg="f")
        mock_service.list_volumes.assert_called_once_with(True)

    def test_create_and_get_volume(self):
        mock_service = self.mock_cinder.return_value
        scenario = volumes.CreateAndGetVolume(self._get_context())
        scenario.run(1, fakearg="f")
        mock_service.create_volume.assert_called_once_with(1, fakearg="f")
        mock_service.get_volume.assert_called_once_with(
            mock_service.create_volume.return_value.id)

    def test_list_volumes(self):
        mock_service = self.mock_cinder.return_value
        scenario = volumes.ListVolumes(self._get_context())
        scenario.run(True)
        mock_service.list_volumes.assert_called_once_with(True)

    def test_list_types(self):
        mock_service = self.mock_cinder.return_value
        scenario = volumes.ListTypes(self._get_context())
        scenario.run(None, is_public=None)
        mock_service.list_types.assert_called_once_with(None,
                                                        is_public=None)

    def test_list_transfers(self):
        mock_service = self.mock_cinder.return_value
        scenario = volumes.ListTransfers(self._get_context())
        scenario._list_transfers = mock.MagicMock()
        scenario.run(True, search_opts=None)
        mock_service.list_transfers.assert_called_once_with(
            True, search_opts=None)

    @ddt.data({"update_args": {"description": "desp"},
               "expected": {"description": "desp"}},
              {"update_args": {"update_name": True, "description": "desp"},
               "expected": {"name": "new_name", "description": "desp"}})
    @ddt.unpack
    def test_create_and_update_volume(self, update_args, expected):
        mock_service = self.mock_cinder.return_value
        scenario = volumes.CreateAndUpdateVolume(self._get_context())
        scenario.generate_random_name = mock.MagicMock()
        scenario.generate_random_name.return_value = "new_name"
        scenario.run(1, update_volume_kwargs=update_args)
        mock_service.create_volume.assert_called_once_with(1)
        mock_service.update_volume.assert_called_once_with(
            mock_service.create_volume.return_value, **expected)
        if update_args.get("update_name", False):
            scenario.generate_random_name.assert_called_once_with()

    def test_create_volume_and_update_readonly_flag(self):
        mock_service = self.mock_cinder.return_value
        scenario = volumes.CreateVolumeAndUpdateReadonlyFlag(
            self._get_context())
        scenario.run(1, image=None, read_only=True, fakearg="f")
        mock_service.create_volume.assert_called_once_with(1, fakearg="f")
        mock_service.update_readonly_flag.assert_called_once_with(
            mock_service.create_volume.return_value.id, read_only=True)

    def test_create_and_delete_volume(self):
        mock_service = self.mock_cinder.return_value
        scenario = volumes.CreateAndDeleteVolume(self._get_context())
        scenario.sleep_between = mock.MagicMock()
        scenario.run(size=1, min_sleep=10, max_sleep=20, fakearg="f")

        mock_service.create_volume.assert_called_once_with(1, fakearg="f")
        scenario.sleep_between.assert_called_once_with(10, 20)
        mock_service.delete_volume.assert_called_once_with(
            mock_service.create_volume.return_value)

    def test_create_volume(self):
        mock_service = self.mock_cinder.return_value
        scenario = volumes.CreateVolume(self._get_context())
        scenario.run(1, fakearg="f")
        mock_service.create_volume.assert_called_once_with(1, fakearg="f")

    def test_create_volume_and_modify_metadata(self):
        mock_service = self.mock_cinder.return_value
        scenario = volumes.ModifyVolumeMetadata(self._get_context())
        scenario.run(sets=5, set_size=4, deletes=3, delete_size=2)
        mock_service.set_metadata.assert_called_once_with(
            "uuid", set_size=4, sets=5)
        mock_service.delete_metadata.assert_called_once_with(
            "uuid",
            keys=mock_service.set_metadata.return_value,
            deletes=3, delete_size=2)

    def test_create_and_extend_volume(self):
        mock_service = self.mock_cinder.return_value

        scenario = volumes.CreateAndExtendVolume(self._get_context())
        scenario.sleep_between = mock.MagicMock()

        scenario.run(1, 2, 10, 20, fakearg="f")
        mock_service.create_volume.assert_called_once_with(1, fakearg="f")
        mock_service.extend_volume.assert_called_once_with(
            mock_service.create_volume.return_value, new_size=2)
        scenario.sleep_between.assert_called_once_with(10, 20)
        mock_service.delete_volume.assert_called_once_with(
            mock_service.create_volume.return_value)

    def test_create_from_image_and_delete_volume(self):
        mock_service = self.mock_cinder.return_value
        scenario = volumes.CreateAndDeleteVolume(self._get_context())
        scenario.run(1, image="fake_image")
        mock_service.create_volume.assert_called_once_with(
            1, imageRef="fake_image")
        mock_service.delete_volume.assert_called_once_with(
            mock_service.create_volume.return_value)

    def test_create_volume_from_image(self):
        mock_service = self.mock_cinder.return_value
        scenario = volumes.CreateVolume(self._get_context())
        scenario.run(1, image="fake_image")
        mock_service.create_volume.assert_called_once_with(
            1, imageRef="fake_image")

    def test_create_volume_from_image_and_list(self):
        mock_service = self.mock_cinder.return_value
        scenario = volumes.CreateAndListVolume(self._get_context())
        scenario.run(1, True, "fake_image")
        mock_service.create_volume.assert_called_once_with(
            1, imageRef="fake_image")
        mock_service.list_volumes.assert_called_once_with(True)

    def test_create_from_volume_and_delete_volume(self):
        mock_service = self.mock_cinder.return_value
        vol_size = 1
        scenario = volumes.CreateFromVolumeAndDeleteVolume(self._get_context())
        scenario.run(vol_size)
        mock_service.create_volume.assert_called_once_with(
            1, source_volid="uuid")
        mock_service.delete_volume.assert_called_once_with(
            mock_service.create_volume.return_value)

    @mock.patch("%s.CreateAndDeleteSnapshot.sleep_between" % CINDER_VOLUMES)
    def test_create_and_delete_snapshot(self, mock_sleep_between):
        mock_service = self.mock_cinder.return_value
        scenario = volumes.CreateAndDeleteSnapshot(self._get_context())
        scenario.run(False, 10, 20, fakearg="f")

        mock_service.create_snapshot.assert_called_once_with("uuid",
                                                             force=False,
                                                             fakearg="f")
        mock_sleep_between.assert_called_once_with(10, 20)
        mock_service.delete_snapshot.assert_called_once_with(
            mock_service.create_snapshot.return_value)

    def test_create_and_list_snapshots(self):
        mock_service = self.mock_cinder.return_value
        scenario = volumes.CreateAndListSnapshots(self._get_context())
        scenario.run(False, True, fakearg="f")
        mock_service.create_snapshot.assert_called_once_with("uuid",
                                                             force=False,
                                                             fakearg="f")
        mock_service.list_snapshots.assert_called_once_with(True)

    def test_create_and_attach_volume(self):
        fake_server = mock.MagicMock()
        mock_service = self.mock_cinder.return_value
        scenario = volumes.CreateAndAttachVolume(self._get_context())

        scenario._boot_server = mock.MagicMock(return_value=fake_server)
        scenario._delete_server = mock.MagicMock()
        scenario._attach_volume = mock.MagicMock()
        scenario._detach_volume = mock.MagicMock()

        volume_args = {"some_key": "some_val"}
        vm_args = {"some_key": "some_val"}

        scenario.run(10, "img", "0",
                     create_volume_params=volume_args,
                     create_vm_params=vm_args)

        mock_service.create_volume.assert_called_once_with(
            10, **volume_args)
        scenario._attach_volume.assert_called_once_with(
            fake_server, mock_service.create_volume.return_value)
        scenario._detach_volume.assert_called_once_with(
            fake_server, mock_service.create_volume.return_value)

        mock_service.delete_volume.assert_called_once_with(
            mock_service.create_volume.return_value)
        scenario._delete_server.assert_called_once_with(fake_server)

    @mock.patch("rally.plugins.openstack.services.image.image.Image")
    def test_create_and_upload_volume_to_image(self, mock_image):
        mock_volume_service = self.mock_cinder.return_value
        mock_image_service = mock_image.return_value
        scenario = volumes.CreateAndUploadVolumeToImage(self._get_context())

        scenario.run(2, image="img", container_format="fake",
                     disk_format="disk", do_delete=False, fakeargs="fakeargs")

        mock_volume_service.create_volume.assert_called_once_with(
            2, imageRef="img", fakeargs="fakeargs")
        mock_volume_service.upload_volume_to_image.assert_called_once_with(
            mock_volume_service.create_volume.return_value,
            container_format="fake", disk_format="disk", force=False)

        mock_volume_service.create_volume.reset_mock()
        mock_volume_service.upload_volume_to_image.reset_mock()

        scenario.run(1, image=None, do_delete=True, fakeargs="fakeargs")

        mock_volume_service.create_volume.assert_called_once_with(
            1, fakeargs="fakeargs")
        mock_volume_service.upload_volume_to_image.assert_called_once_with(
            mock_volume_service.create_volume.return_value,
            container_format="bare", disk_format="raw", force=False)
        mock_volume_service.delete_volume.assert_called_once_with(
            mock_volume_service.create_volume.return_value)
        mock_image_service.delete_image.assert_called_once_with(
            mock_volume_service.upload_volume_to_image.return_value.id)

    def test_create_snapshot_and_attach_volume(self):
        mock_service = self.mock_cinder.return_value
        scenario = volumes.CreateSnapshotAndAttachVolume(self._get_context())
        scenario._boot_server = mock.MagicMock()
        scenario._attach_volume = mock.MagicMock()
        scenario._detach_volume = mock.MagicMock()
        scenario.run("img", "flavor")

        self.assertTrue(mock_service.create_volume.called)
        volume = mock_service.create_volume.return_value
        snapshot = mock_service.create_snapshot.return_value
        mock_service.create_snapshot.assert_called_once_with(volume.id,
                                                             force=False)
        mock_service.delete_snapshot.assert_called_once_with(snapshot)
        scenario._attach_volume.assert_called_once_with(
            scenario._boot_server.return_value, volume)
        scenario._detach_volume.assert_called_once_with(
            scenario._boot_server.return_value, volume)
        mock_service.delete_volume.assert_called_once_with(volume)

    @mock.patch("random.choice")
    def test_create_snapshot_and_attach_volume_use_volume_type_with_name(
            self, mock_choice):
        mock_service = self.mock_cinder.return_value

        scenario = volumes.CreateSnapshotAndAttachVolume(self._get_context())
        scenario._boot_server = mock.MagicMock()
        scenario._attach_volume = mock.MagicMock()
        scenario._detach_volume = mock.MagicMock()
        scenario.run("img", "flavor", volume_type="type")

        fake_volume = mock_service.create_volume.return_value
        fake_server = scenario._boot_server.return_value
        fake_snapshot = mock_service.create_snapshot.return_value

        mock_service.create_volume.assert_called_once_with(
            {"min": 1, "max": 5}, volume_type="type")
        mock_service.create_snapshot.assert_called_once_with(fake_volume.id,
                                                             force=False)
        mock_service.delete_snapshot.assert_called_once_with(fake_snapshot)
        scenario._attach_volume.assert_called_once_with(fake_server,
                                                        fake_volume)
        scenario._detach_volume.assert_called_once_with(fake_server,
                                                        fake_volume)
        mock_service.delete_volume.assert_called_once_with(fake_volume)

    @mock.patch("random.randint")
    def test_create_nested_snapshots_and_attach_volume(self, mock_randint):
        mock_service = self.mock_cinder.return_value
        mock_randint.return_value = 2
        volume_kwargs = {"volume_type": "type1"}
        snapshot_kwargs = {"name": "snapshot1", "description": "snaphot one"}

        scenario = volumes.CreateNestedSnapshotsAndAttachVolume(
            context=self._get_context())
        scenario._boot_server = mock.MagicMock()
        scenario._attach_volume = mock.MagicMock()
        scenario._detach_volume = mock.MagicMock()
        scenario.run("img", "flavor", create_volume_kwargs=volume_kwargs,
                     create_snapshot_kwargs=snapshot_kwargs)

        mock_service.create_volume.assert_called_once_with(
            mock_randint.return_value, **volume_kwargs)
        mock_service.create_snapshot.assert_called_once_with(
            mock_service.create_volume.return_value.id, force=False,
            **snapshot_kwargs)
        scenario._attach_volume(scenario._boot_server.return_value,
                                mock_service.create_volume.return_value)
        mock_service.delete_volume.assert_called_once_with(
            mock_service.create_volume.return_value)
        mock_service.delete_snapshot.assert_called_once_with(
            mock_service.create_snapshot.return_value)
        scenario._detach_volume.assert_called_once_with(
            scenario._boot_server.return_value,
            mock_service.create_volume.return_value)

    @mock.patch("random.randint")
    def test_create_nested_snapshots_and_attach_volume_2(self, mock_randint):
        mock_service = self.mock_cinder.return_value
        mock_randint.return_value = 2
        nested_level = 3
        volume_size = mock_randint.return_value
        fake_volumes = [mock.Mock(size=volume_size)
                        for i in range(nested_level)]
        fake_snapshots = [mock.Mock()
                          for i in range(nested_level)]
        mock_service.create_volume.side_effect = fake_volumes
        mock_service.create_snapshot.side_effect = fake_snapshots

        scenario = volumes.CreateNestedSnapshotsAndAttachVolume(
            context=self._get_context())
        scenario._boot_server = mock.MagicMock()
        scenario._attach_volume = mock.MagicMock()
        scenario._detach_volume = mock.MagicMock()
        scenario.run("img", "flavor", nested_level=nested_level)

        expected_volumes = [mock.call(volume_size)]
        expected_snapshots = [mock.call(fake_volumes[0].id, force=False)]
        expected_attachs = [mock.call(scenario._boot_server.return_value,
                                      fake_volumes[0])]
        for i in range(nested_level - 1):
            expected_volumes.append(
                mock.call(volume_size, snapshot_id=fake_snapshots[i].id))
            expected_snapshots.append(
                mock.call(fake_volumes[i + 1].id, force=False))
            expected_attachs.append(
                mock.call(scenario._boot_server.return_value,
                          fake_volumes[i + 1]))

        mock_service.create_volume.assert_has_calls(expected_volumes)
        mock_service.create_snapshot.assert_has_calls(expected_snapshots)
        scenario._attach_volume.assert_has_calls(expected_attachs)
        fake_volumes.reverse()
        fake_snapshots.reverse()
        mock_service.delete_volume.assert_has_calls(
            [mock.call(volume) for volume in fake_volumes])
        mock_service.delete_snapshot.assert_has_calls(
            [mock.call(snapshot) for snapshot in fake_snapshots])
        scenario._detach_volume.assert_has_calls(
            [mock.call(scenario._boot_server.return_value,
                       fake_volumes[i])
             for i in range(len(fake_volumes))])

    def test_create_volume_backup(self):
        mock_service = self.mock_cinder.return_value
        scenario = volumes.CreateVolumeBackup(self._get_context())

        volume_kwargs = {"some_var": "zaq"}
        scenario.run(1, do_delete=True, create_volume_kwargs=volume_kwargs)
        mock_service.create_volume.assert_called_once_with(1, **volume_kwargs)
        mock_service.create_backup.assert_called_once_with(
            mock_service.create_volume.return_value.id)
        mock_service.delete_volume.assert_called_once_with(
            mock_service.create_volume.return_value)
        mock_service.delete_backup.assert_called_once_with(
            mock_service.create_backup.return_value)

    def test_create_volume_backup_no_delete(self):
        mock_service = self.mock_cinder.return_value
        scenario = volumes.CreateVolumeBackup(self._get_context())

        volume_kwargs = {"some_var": "zaq"}
        scenario.run(1, do_delete=False, create_volume_kwargs=volume_kwargs)
        mock_service.create_volume.assert_called_once_with(1, **volume_kwargs)
        mock_service.create_backup.assert_called_once_with(
            mock_service.create_volume.return_value.id)
        self.assertFalse(mock_service.delete_volume.called)
        self.assertFalse(mock_service.delete_backup.called)

    def test_create_and_restore_volume_backup(self):
        mock_service = self.mock_cinder.return_value
        volume_kwargs = {"some_var": "zaq"}

        scenario = volumes.CreateAndRestoreVolumeBackup(self._get_context())
        scenario.run(1, do_delete=True, create_volume_kwargs=volume_kwargs)

        fake_volume = mock_service.create_volume.return_value
        fake_backup = mock_service.create_backup.return_value
        mock_service.create_volume.assert_called_once_with(1, **volume_kwargs)
        mock_service.create_backup.assert_called_once_with(fake_volume.id)
        mock_service.restore_backup.assert_called_once_with(fake_backup.id)
        mock_service.delete_volume.assert_called_once_with(fake_volume)
        mock_service.delete_backup.assert_called_once_with(fake_backup)

    def test_create_and_restore_volume_backup_no_delete(self):
        mock_service = self.mock_cinder.return_value
        volume_kwargs = {"some_var": "zaq"}
        scenario = volumes.CreateAndRestoreVolumeBackup(self._get_context())
        scenario.run(1, do_delete=False, create_volume_kwargs=volume_kwargs)

        fake_volume = mock_service.create_volume.return_value
        fake_backup = mock_service.create_backup.return_value
        mock_service.create_volume.assert_called_once_with(1, **volume_kwargs)
        mock_service.create_backup.assert_called_once_with(fake_volume.id)
        mock_service.restore_backup.assert_called_once_with(fake_backup.id)
        self.assertFalse(mock_service.delete_volume.called)
        self.assertFalse(mock_service.delete_backup.called)

    def test_create_and_list_volume_backups(self):
        mock_service = self.mock_cinder.return_value
        volume_kwargs = {"some_var": "zaq"}
        scenario = volumes.CreateAndListVolumeBackups(self._get_context())
        scenario.run(1, detailed=True, do_delete=True,
                     create_volume_kwargs=volume_kwargs)

        fake_volume = mock_service.create_volume.return_value
        fake_backup = mock_service.create_backup.return_value
        mock_service.create_volume.assert_called_once_with(1, **volume_kwargs)
        mock_service.create_backup.assert_called_once_with(fake_volume.id)
        mock_service.list_backups.assert_called_once_with(True)
        mock_service.delete_volume.assert_called_once_with(fake_volume)
        mock_service.delete_backup.assert_called_once_with(fake_backup)

    def test_create_and_list_volume_backups_no_delete(self):
        mock_service = self.mock_cinder.return_value
        volume_kwargs = {"some_var": "zaq"}
        scenario = volumes.CreateAndListVolumeBackups(self._get_context())
        scenario.run(1, detailed=True, do_delete=False,
                     create_volume_kwargs=volume_kwargs)

        fake_volume = mock_service.create_volume.return_value
        mock_service.create_volume.assert_called_once_with(1, **volume_kwargs)
        mock_service.create_backup.assert_called_once_with(fake_volume.id)
        mock_service.list_backups.assert_called_once_with(True)
        self.assertFalse(mock_service.delete_volume.called)
        self.assertFalse(mock_service.delete_backup.called)

    @ddt.data({},
              {"nested_level": 2},
              {"image": "img"})
    @ddt.unpack
    def test_create_volume_and_clone(self, nested_level=1,
                                     image=None):
        create_volumes_count = nested_level + 1
        fake_volumes = [mock.Mock(size=1)
                        for i in range(create_volumes_count)]
        mock_service = self.mock_cinder.return_value
        mock_service.create_volume.side_effect = fake_volumes

        scenario = volumes.CreateVolumeAndClone(self._get_context())
        scenario.run(1, image=image, nested_level=nested_level,
                     fakearg="fake")

        expected = [mock.call(1, imageRef=image, fakearg="fake")
                    if image else mock.call(1, fakearg="fake")]
        for i in range(nested_level):
            expected.append(mock.call(fake_volumes[i].size,
                                      source_volid=fake_volumes[i].id,
                                      fakearg="fake")
                            )
            self._test_atomic_action_timer(scenario.atomic_actions(),
                                           "cinder.clone_volume",
                                           count=nested_level)
        mock_service.create_volume.assert_has_calls(expected)

    def test_create_volume_from_snapshot(self):
        mock_service = self.mock_cinder.return_value
        create_snapshot_args = {"force": False}

        scenario = volumes.CreateVolumeFromSnapshot(self._get_context())
        scenario.run(fakearg="f")

        fake_snapshot = mock_service.create_snapshot.return_value
        fake_volume = mock_service.create_volume.return_value
        mock_service.create_snapshot.assert_called_once_with("uuid")
        mock_service.create_volume.assert_called_once_with(
            1, snapshot_id=fake_snapshot.id, fakearg="f")
        mock_service.delete_snapshot.assert_called_once_with(fake_snapshot)
        mock_service.delete_volume.assert_called_once_with(fake_volume)

        mock_service.create_snapshot.reset_mock()
        mock_service.create_volume.reset_mock()
        mock_service.delete_snapshot.reset_mock()
        mock_service.delete_volume.reset_mock()

        scenario.run(do_delete=False,
                     create_snapshot_kwargs=create_snapshot_args,
                     fakearg="f")

        mock_service.create_snapshot.assert_called_once_with(
            "uuid", **create_snapshot_args)
        mock_service.create_volume.assert_called_once_with(
            1, snapshot_id=fake_snapshot.id, fakearg="f")
        self.assertFalse(mock_service.delete_snapshot.called)
        self.assertFalse(mock_service.delete_volume.called)

    @ddt.data({},
              {"image": "img"})
    @ddt.unpack
    def test_create_and_accept_transfer(self, image=None):
        mock_service = self.mock_cinder.return_value
        scenario = volumes.CreateAndAcceptTransfer(self._get_context())
        scenario.run(1, image=image, fakearg="fake")

        expected = [mock.call(1, imageRef=image, fakearg="fake")
                    if image else mock.call(1, fakearg="fake")]
        mock_service.create_volume.assert_has_calls(expected)
        mock_service.transfer_create.assert_called_once_with(
            mock_service.create_volume.return_value.id)
        mock_service.transfer_accept.assert_called_once_with(
            mock_service.transfer_create.return_value.id,
            auth_key=mock_service.transfer_create.return_value.auth_key)
