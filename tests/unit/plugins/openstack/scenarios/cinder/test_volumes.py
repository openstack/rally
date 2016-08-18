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

CINDER_VOLUMES = ("rally.plugins.openstack.scenarios.cinder.volumes"
                  ".CinderVolumes")


class fake_type(object):
    name = "fake"


@ddt.ddt
class CinderServersTestCase(test.ScenarioTestCase):

    def _get_context(self):
        context = test.get_test_context()
        context.update({
            "user": {"tenant_id": "fake",
                     "credential": mock.MagicMock()},
            "tenant": {"id": "fake", "name": "fake",
                       "volumes": [{"id": "uuid", "size": 1}],
                       "servers": [1]}})
        return context

    def test_create_and_list_volume(self):
        scenario = volumes.CreateAndListVolume(self.context)
        scenario._create_volume = mock.MagicMock()
        scenario._list_volumes = mock.MagicMock()
        scenario.run(1, True, fakearg="f")
        scenario._create_volume.assert_called_once_with(1, fakearg="f")
        scenario._list_volumes.assert_called_once_with(True)

    def test_list_volumes(self):
        scenario = volumes.ListVolumes(self.context)
        scenario._list_volumes = mock.MagicMock()
        scenario.run(True)
        scenario._list_volumes.assert_called_once_with(True)

    def test_create_and_update_volume(self):
        volume_update_args = {"dispaly_name": "_updated"}
        scenario = volumes.CreateAndUpdateVolume(self.context)
        fake_volume = mock.MagicMock()
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)
        scenario._update_volume = mock.MagicMock()
        scenario.run(1, update_volume_kwargs=volume_update_args)
        scenario._create_volume.assert_called_once_with(1)
        scenario._update_volume.assert_called_once_with(fake_volume,
                                                        **volume_update_args)

    def test_create_and_delete_volume(self):
        fake_volume = mock.MagicMock()

        scenario = volumes.CreateAndDeleteVolume(self.context)
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)
        scenario.sleep_between = mock.MagicMock()
        scenario._delete_volume = mock.MagicMock()

        scenario.run(size=1, min_sleep=10, max_sleep=20, fakearg="f")

        scenario._create_volume.assert_called_once_with(1, fakearg="f")
        scenario.sleep_between.assert_called_once_with(10, 20)
        scenario._delete_volume.assert_called_once_with(fake_volume)

    def test_create_volume(self):
        fake_volume = mock.MagicMock()
        scenario = volumes.CreateVolume(self.context)
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)

        scenario.run(1, fakearg="f")
        scenario._create_volume.assert_called_once_with(1, fakearg="f")

    def test_create_volume_and_modify_metadata(self):
        scenario = volumes.ModifyVolumeMetadata(self._get_context())
        scenario._set_metadata = mock.Mock()
        scenario._delete_metadata = mock.Mock()

        scenario.run(sets=5, set_size=4, deletes=3, delete_size=2)
        scenario._set_metadata.assert_called_once_with("uuid", 5, 4)
        scenario._delete_metadata.assert_called_once_with(
            "uuid",
            scenario._set_metadata.return_value, 3, 2)

    def test_create_and_extend_volume(self):
        fake_volume = mock.MagicMock()

        scenario = volumes.CreateAndExtendVolume(self.context)
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)
        scenario._extend_volume = mock.MagicMock(return_value=fake_volume)
        scenario.sleep_between = mock.MagicMock()
        scenario._delete_volume = mock.MagicMock()

        scenario.run(1, 2, 10, 20, fakearg="f")
        scenario._create_volume.assert_called_once_with(1, fakearg="f")
        self.assertTrue(scenario._extend_volume.called)
        scenario.sleep_between.assert_called_once_with(10, 20)
        scenario._delete_volume.assert_called_once_with(fake_volume)

    def test_create_from_image_and_delete_volume(self):
        fake_volume = mock.MagicMock()
        scenario = volumes.CreateAndDeleteVolume(self.context)
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)
        scenario._delete_volume = mock.MagicMock()

        scenario.run(1, image="fake_image")
        scenario._create_volume.assert_called_once_with(1,
                                                        imageRef="fake_image")

        scenario._delete_volume.assert_called_once_with(fake_volume)

    def test_create_volume_from_image(self):
        fake_volume = mock.MagicMock()
        scenario = volumes.CreateVolume(self.context)
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)

        scenario.run(1, image="fake_image")
        scenario._create_volume.assert_called_once_with(1,
                                                        imageRef="fake_image")

    def test_create_volume_from_image_and_list(self):
        fake_volume = mock.MagicMock()
        scenario = volumes.CreateAndListVolume(self.context)
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)
        scenario._list_volumes = mock.MagicMock()

        scenario.run(1, True, "fake_image")
        scenario._create_volume.assert_called_once_with(1,
                                                        imageRef="fake_image")
        scenario._list_volumes.assert_called_once_with(True)

    def test_create_from_volume_and_delete_volume(self):
        fake_volume = mock.MagicMock()
        vol_size = 1
        scenario = volumes.CreateFromVolumeAndDeleteVolume(self._get_context())
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)
        scenario._delete_volume = mock.MagicMock()

        scenario.run(vol_size)
        scenario._create_volume.assert_called_once_with(1, source_volid="uuid")
        scenario._delete_volume.assert_called_once_with(fake_volume)

    def test_create_and_delete_snapshot(self):
        fake_snapshot = mock.MagicMock()
        scenario = volumes.CreateAndDeleteSnapshot(self._get_context())

        scenario._create_snapshot = mock.MagicMock(return_value=fake_snapshot)
        scenario.sleep_between = mock.MagicMock()
        scenario._delete_snapshot = mock.MagicMock()

        scenario.run(False, 10, 20, fakearg="f")

        scenario._create_snapshot.assert_called_once_with("uuid", force=False,
                                                          fakearg="f")
        scenario.sleep_between.assert_called_once_with(10, 20)
        scenario._delete_snapshot.assert_called_once_with(fake_snapshot)

    def test_create_and_list_snapshots(self):
        fake_snapshot = mock.MagicMock()
        scenario = volumes.CreateAndListSnapshots(self._get_context())

        scenario._create_snapshot = mock.MagicMock(return_value=fake_snapshot)
        scenario._list_snapshots = mock.MagicMock()
        scenario.run(False, True, fakearg="f")
        scenario._create_snapshot.assert_called_once_with("uuid", force=False,
                                                          fakearg="f")
        scenario._list_snapshots.assert_called_once_with(True)

    def test_create_and_attach_volume(self):
        fake_volume = mock.MagicMock()
        fake_server = mock.MagicMock()
        fake_attach = mock.MagicMock()
        scenario = volumes.CreateAndAttachVolume(self.context)

        scenario._attach_volume = mock.MagicMock(return_value=fake_attach)
        scenario._detach_volume = mock.MagicMock()

        scenario._boot_server = mock.MagicMock(return_value=fake_server)
        scenario._delete_server = mock.MagicMock()
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)
        scenario._delete_volume = mock.MagicMock()

        volume_args = {"some_key": "some_val"}
        vm_args = {"some_key": "some_val"}

        scenario.run(10, "img", "0",
                     create_volume_params=volume_args,
                     create_vm_params=vm_args)
        scenario._attach_volume.assert_called_once_with(fake_server,
                                                        fake_volume)
        scenario._detach_volume.assert_called_once_with(fake_server,
                                                        fake_volume,
                                                        fake_attach)

        scenario._delete_volume.assert_called_once_with(fake_volume)
        scenario._delete_server.assert_called_once_with(fake_server)

    def test_create_and_upload_volume_to_image(self):
        fake_volume = mock.Mock()
        fake_image = mock.Mock()
        scenario = volumes.CreateAndUploadVolumeToImage(self.context)

        scenario._create_volume = mock.MagicMock(return_value=fake_volume)
        scenario._upload_volume_to_image = mock.MagicMock(
            return_value=fake_image)
        scenario._delete_volume = mock.MagicMock()
        scenario._delete_image = mock.MagicMock()

        scenario.run(2, image="img", container_format="fake",
                     disk_format="disk", do_delete=False, fakeargs="fakeargs")

        scenario._create_volume.assert_called_once_with(2, imageRef="img",
                                                        fakeargs="fakeargs")
        scenario._upload_volume_to_image.assert_called_once_with(fake_volume,
                                                                 False,
                                                                 "fake",
                                                                 "disk")
        scenario._create_volume.reset_mock()
        scenario._upload_volume_to_image.reset_mock()

        scenario.run(1, image=None, do_delete=True, fakeargs="fakeargs")

        scenario._create_volume.assert_called_once_with(1, fakeargs="fakeargs")
        scenario._upload_volume_to_image.assert_called_once_with(fake_volume,
                                                                 False,
                                                                 "bare",
                                                                 "raw")
        scenario._delete_volume.assert_called_once_with(fake_volume)
        scenario._delete_image.assert_called_once_with(fake_image)

    def test_create_snapshot_and_attach_volume(self):
        fake_volume = mock.MagicMock()
        fake_snapshot = mock.MagicMock()
        fake_server = mock.MagicMock()
        fake_attach = mock.MagicMock()
        scenario = volumes.CreateSnapshotAndAttachVolume(self._get_context())

        scenario._attach_volume = mock.MagicMock(return_value=fake_attach)
        scenario._detach_volume = mock.MagicMock()
        scenario._boot_server = mock.MagicMock(return_value=fake_server)
        scenario._delete_server = mock.MagicMock()
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)
        scenario._delete_volume = mock.MagicMock()
        scenario._create_snapshot = mock.MagicMock(return_value=fake_snapshot)
        scenario._delete_snapshot = mock.MagicMock()

        self.clients("nova").servers.get = mock.MagicMock(
            return_value=fake_server)

        scenario.run()

        self.assertTrue(scenario._create_volume.called)
        scenario._create_snapshot.assert_called_once_with(fake_volume.id,
                                                          False)
        scenario._delete_snapshot.assert_called_once_with(fake_snapshot)
        scenario._attach_volume.assert_called_once_with(fake_server,
                                                        fake_volume)
        scenario._detach_volume.assert_called_once_with(fake_server,
                                                        fake_volume,
                                                        fake_attach)
        scenario._delete_volume.assert_called_once_with(fake_volume)

    def test_create_snapshot_and_attach_volume_use_volume_type(self):
        fake_volume = mock.MagicMock()
        fake_snapshot = mock.MagicMock()
        fake_server = mock.MagicMock()
        fake_attach = mock.MagicMock()

        scenario = volumes.CreateSnapshotAndAttachVolume(self._get_context())

        scenario._attach_volume = mock.MagicMock(return_value=fake_attach)
        scenario._detach_volume = mock.MagicMock()
        scenario._boot_server = mock.MagicMock(return_value=fake_server)
        scenario._delete_server = mock.MagicMock()
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)
        scenario._delete_volume = mock.MagicMock()
        scenario._create_snapshot = mock.MagicMock(return_value=fake_snapshot)
        scenario._delete_snapshot = mock.MagicMock()
        fake = fake_type()

        self.clients("cinder").volume_types.list = mock.MagicMock(
            return_value=[fake])
        self.clients("nova").servers.get = mock.MagicMock(
            return_value=fake_server)

        scenario.run(volume_type=True)

        # Make sure create volume's second arg was the correct volume type.
        # fake or none (randomly selected)
        self.assertTrue(scenario._create_volume.called)
        vol_type = scenario._create_volume.call_args_list[0][1]["volume_type"]
        self.assertTrue(vol_type is fake.name or vol_type is None)
        scenario._create_snapshot.assert_called_once_with(fake_volume.id,
                                                          False)
        scenario._delete_snapshot.assert_called_once_with(fake_snapshot)
        scenario._attach_volume.assert_called_once_with(fake_server,
                                                        fake_volume)
        scenario._detach_volume.assert_called_once_with(fake_server,
                                                        fake_volume,
                                                        fake_attach)
        scenario._delete_volume.assert_called_once_with(fake_volume)

    def test_create_nested_snapshots_and_attach_volume(self):
        fake_volume = mock.MagicMock()
        fake_snapshot = mock.MagicMock()
        fake_attach = mock.MagicMock()

        scenario = volumes.CreateNestedSnapshotsAndAttachVolume(
            context=self._get_context())

        scenario._attach_volume = mock.MagicMock(return_value=fake_attach)
        scenario._detach_volume = mock.MagicMock()
        scenario._delete_server = mock.MagicMock()
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)
        scenario._delete_volume = mock.MagicMock()
        scenario._create_snapshot = mock.MagicMock(return_value=fake_snapshot)
        scenario._delete_snapshot = mock.MagicMock()

        scenario.run()

        volume_count = scenario._create_volume.call_count
        snapshots_count = scenario._create_snapshot.call_count
        attached_count = scenario._attach_volume.call_count

        self.assertEqual(scenario._delete_volume.call_count, volume_count)
        self.assertEqual(scenario._delete_snapshot.call_count, snapshots_count)
        self.assertEqual(scenario._detach_volume.call_count, attached_count)

    def test_create_nested_snapshots_and_attach_volume_kwargs(self):
        fake_volume = mock.MagicMock()
        fake_snapshot = mock.MagicMock()
        fake_attach = mock.MagicMock()

        scenario = volumes.CreateNestedSnapshotsAndAttachVolume(
            context=self._get_context())

        scenario._attach_volume = mock.MagicMock(return_value=fake_attach)
        scenario._detach_volume = mock.MagicMock()
        scenario._delete_server = mock.MagicMock()
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)
        scenario._delete_volume = mock.MagicMock()
        scenario._create_snapshot = mock.MagicMock(return_value=fake_snapshot)
        scenario._delete_snapshot = mock.MagicMock()

        volume_kwargs = {"volume_type": "type1"}
        scenario.run(size={"min": 1, "max": 1},
                     create_volume_kwargs=volume_kwargs)

        scenario._create_volume.assert_called_once_with(1, **volume_kwargs)
        self.assertEqual(fake_volume, scenario._create_volume.return_value)

    def test_create_nested_snapshots_and_attach_volume_snapshot_kwargs(self):
        fake_volume = mock.MagicMock()
        fake_volume.id = "FAKE_ID"
        fake_snapshot = mock.MagicMock()
        fake_attach = mock.MagicMock()

        scenario = volumes.CreateNestedSnapshotsAndAttachVolume(
            context=self._get_context())

        scenario._attach_volume = mock.MagicMock(return_value=fake_attach)
        scenario._detach_volume = mock.MagicMock()
        scenario._delete_server = mock.MagicMock()
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)
        scenario._delete_volume = mock.MagicMock()
        scenario._create_snapshot = mock.MagicMock(return_value=fake_snapshot)
        scenario._delete_snapshot = mock.MagicMock()

        volume_kwargs = {"volume_type": "type1"}
        snapshot_kwargs = {"name": "snapshot1", "description": "snaphot one"}
        scenario.run(size={"min": 1, "max": 1},
                     create_volume_kwargs=volume_kwargs,
                     create_snapshot_kwargs=snapshot_kwargs)

        scenario._create_snapshot.assert_called_once_with(fake_volume.id,
                                                          False,
                                                          **snapshot_kwargs)
        self.assertEqual(fake_snapshot, scenario._create_snapshot.return_value)

    def test_create_nested_snapshots_and_attach_volume_deprecate_kwargs(self):
        fake_volume = mock.MagicMock()
        fake_volume.id = "FAKE_ID"
        fake_snapshot = mock.MagicMock()
        fake_attach = mock.MagicMock()

        scenario = volumes.CreateNestedSnapshotsAndAttachVolume(
            self._get_context())

        scenario._attach_volume = mock.MagicMock(return_value=fake_attach)
        scenario._detach_volume = mock.MagicMock()
        scenario._delete_server = mock.MagicMock()
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)
        scenario._delete_volume = mock.MagicMock()
        scenario._create_snapshot = mock.MagicMock(return_value=fake_snapshot)
        scenario._delete_snapshot = mock.MagicMock()

        volume_kwargs = {"volume_type": "type1"}
        snapshot_kwargs = {"name": "snapshot1", "description": "snaphot one"}
        scenario.run(size={"min": 1, "max": 1},
                     create_volume_kwargs=volume_kwargs,
                     **snapshot_kwargs)

        scenario._create_snapshot.assert_called_once_with(fake_volume.id,
                                                          False,
                                                          **snapshot_kwargs)
        self.assertEqual(fake_snapshot, scenario._create_snapshot.return_value)

    def test_create_nested_snapshots_calls_order(self):
        fake_volume1 = mock.MagicMock()
        fake_volume2 = mock.MagicMock()
        fake_snapshot1 = mock.MagicMock()
        fake_snapshot2 = mock.MagicMock()

        scenario = volumes.CreateNestedSnapshotsAndAttachVolume(
            self._get_context())

        scenario._attach_volume = mock.MagicMock(return_value=mock.MagicMock())
        scenario._detach_volume = mock.MagicMock()
        scenario._delete_server = mock.MagicMock()
        scenario._create_volume = mock.MagicMock(
            side_effect=[fake_volume1, fake_volume2])
        scenario._delete_volume = mock.MagicMock()
        scenario._create_snapshot = mock.MagicMock(
            side_effect=[fake_snapshot1, fake_snapshot2])
        scenario._delete_snapshot = mock.MagicMock()

        scenario.run(nested_level=2)

        vol_delete_calls = [mock.call(fake_volume2), mock.call(fake_volume1)]
        snap_delete_calls = [mock.call(fake_snapshot2),
                             mock.call(fake_snapshot1)]

        scenario._delete_volume.assert_has_calls(vol_delete_calls)
        scenario._delete_snapshot.assert_has_calls(snap_delete_calls)

    @mock.patch("rally.plugins.openstack.scenarios.cinder.volumes.random")
    def test_create_nested_snapshots_check_resources_size(self, mock_random):
        mock_random.randint.return_value = 3
        fake_volume = mock.MagicMock()
        fake_snapshot = mock.MagicMock()
        fake_server = mock.MagicMock()

        scenario = volumes.CreateNestedSnapshotsAndAttachVolume(
            self._get_context())

        scenario.get_random_server = mock.MagicMock(return_value=fake_server)
        scenario._attach_volume = mock.MagicMock(return_value=mock.MagicMock())
        scenario._detach_volume = mock.MagicMock()
        scenario._delete_server = mock.MagicMock()
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)
        scenario._delete_volume = mock.MagicMock()
        scenario._create_snapshot = mock.MagicMock(return_value=fake_snapshot)
        scenario._delete_snapshot = mock.MagicMock()

        scenario.run(nested_level=2)

        # NOTE: One call for random size
        random_call_count = mock_random.randint.call_count
        self.assertEqual(1, random_call_count)

        calls = scenario._create_volume.mock_calls
        expected_calls = [mock.call(3)]
        expected_calls.extend(
            [mock.call(3, snapshot_id=fake_snapshot.id)])
        self.assertEqual(expected_calls, calls)

    def test_create_volume_backup(self):
        fake_volume = mock.MagicMock()
        fake_backup = mock.MagicMock()
        scenario = volumes.CreateVolumeBackup(self.context)
        self._get_scenario(scenario, fake_volume, fake_backup)

        volume_kwargs = {"some_var": "zaq"}
        scenario.run(1, do_delete=True, create_volume_kwargs=volume_kwargs)
        scenario._create_volume.assert_called_once_with(1, **volume_kwargs)
        scenario._create_backup.assert_called_once_with(fake_volume.id)
        scenario._delete_volume.assert_called_once_with(fake_volume)
        scenario._delete_backup.assert_called_once_with(fake_backup)

    def test_create_volume_backup_no_delete(self):
        fake_volume = mock.MagicMock()
        fake_backup = mock.MagicMock()
        scenario = volumes.CreateVolumeBackup(self.context)
        self._get_scenario(scenario, fake_volume, fake_backup)

        volume_kwargs = {"some_var": "zaq"}
        scenario.run(1, do_delete=False, create_volume_kwargs=volume_kwargs)
        scenario._create_volume.assert_called_once_with(1, **volume_kwargs)
        scenario._create_backup.assert_called_once_with(fake_volume.id)
        self.assertFalse(scenario._delete_volume.called)
        self.assertFalse(scenario._delete_backup.called)

    def _get_scenario(self, scenario, fake_volume,
                      fake_backup, fake_restore=None):
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)
        scenario._create_backup = mock.MagicMock(return_value=fake_backup)
        scenario._restore_backup = mock.MagicMock(return_value=fake_restore)
        scenario._list_backups = mock.MagicMock()
        scenario._delete_volume = mock.MagicMock()
        scenario._delete_backup = mock.MagicMock()

    def test_create_and_restore_volume_backup(self):
        fake_volume = mock.MagicMock()
        fake_backup = mock.MagicMock()
        fake_restore = mock.MagicMock()
        scenario = volumes.CreateAndRestoreVolumeBackup(self.context)
        self._get_scenario(scenario, fake_volume, fake_backup, fake_restore)

        volume_kwargs = {"some_var": "zaq"}
        scenario.run(1, do_delete=True, create_volume_kwargs=volume_kwargs)
        scenario._create_volume.assert_called_once_with(1, **volume_kwargs)
        scenario._create_backup.assert_called_once_with(fake_volume.id)
        scenario._restore_backup.assert_called_once_with(fake_backup.id)
        scenario._delete_volume.assert_called_once_with(fake_volume)
        scenario._delete_backup.assert_called_once_with(fake_backup)

    def test_create_and_restore_volume_backup_no_delete(self):
        fake_volume = mock.MagicMock()
        fake_backup = mock.MagicMock()
        fake_restore = mock.MagicMock()
        scenario = volumes.CreateAndRestoreVolumeBackup(self.context)
        self._get_scenario(scenario, fake_volume, fake_backup, fake_restore)

        volume_kwargs = {"some_var": "zaq"}
        scenario.run(1, do_delete=False, create_volume_kwargs=volume_kwargs)
        scenario._create_volume.assert_called_once_with(1, **volume_kwargs)
        scenario._create_backup.assert_called_once_with(fake_volume.id)
        scenario._restore_backup.assert_called_once_with(fake_backup.id)
        self.assertFalse(scenario._delete_volume.called)
        self.assertFalse(scenario._delete_backup.called)

    def test_create_and_list_volume_backups(self):
        fake_volume = mock.MagicMock()
        fake_backup = mock.MagicMock()
        scenario = volumes.CreateAndListVolumeBackups(self.context)
        self._get_scenario(scenario, fake_volume, fake_backup)

        volume_kwargs = {"some_var": "zaq"}
        scenario.run(1, detailed=True, do_delete=True,
                     create_volume_kwargs=volume_kwargs)
        scenario._create_volume.assert_called_once_with(1, **volume_kwargs)
        scenario._create_backup.assert_called_once_with(fake_volume.id)
        scenario._list_backups.assert_called_once_with(True)
        scenario._delete_volume.assert_called_once_with(fake_volume)
        scenario._delete_backup.assert_called_once_with(fake_backup)

    def test_create_and_list_volume_backups_no_delete(self):
        fake_volume = mock.MagicMock()
        fake_backup = mock.MagicMock()
        scenario = volumes.CreateAndListVolumeBackups(self.context)
        self._get_scenario(scenario, fake_volume, fake_backup)

        volume_kwargs = {"some_var": "zaq"}
        scenario.run(1, detailed=True, do_delete=False,
                     create_volume_kwargs=volume_kwargs)
        scenario._create_volume.assert_called_once_with(1, **volume_kwargs)
        scenario._create_backup.assert_called_once_with(fake_volume.id)
        scenario._list_backups.assert_called_once_with(True)
        self.assertFalse(scenario._delete_volume.called)
        self.assertFalse(scenario._delete_backup.called)

    @ddt.data({},
              {"nested_level": 2},
              {"image": "img"})
    @ddt.unpack
    def test_create_volume_and_clone(self, nested_level=1,
                                     image=None):
        create_volumes_count = nested_level + 1
        fake_volumes = [mock.Mock(size=1) for i in range(create_volumes_count)]
        scenario = volumes.CreateVolumeAndClone(self.context)
        scenario._create_volume = mock.MagicMock(side_effect=fake_volumes)

        scenario.run(1, image=image, nested_level=nested_level, fakearg="fake")

        expected = [mock.call(1, imageRef=image, fakearg="fake")
                    if image else mock.call(1, fakearg="fake")]
        for i in range(nested_level):
            expected.append(mock.call(fake_volumes[i].size,
                                      source_volid=fake_volumes[i].id,
                                      atomic_action=False, fakearg="fake")
                            )
            self._test_atomic_action_timer(scenario.atomic_actions(),
                                           "cinder.clone_volume")
        scenario._create_volume.assert_has_calls(expected)

    def test_create_volume_from_snapshot(self):
        fake_snapshot = mock.MagicMock(id=1)
        fake_volume = mock.MagicMock()
        create_snapshot_args = {"force": False}
        scenario = volumes.CreateVolumeFromSnapshot(self._get_context())

        scenario._create_snapshot = mock.MagicMock(return_value=fake_snapshot)
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)
        scenario._delete_snapshot = mock.MagicMock()
        scenario._delete_volume = mock.MagicMock()

        scenario.run(fakearg="f")

        scenario._create_snapshot.assert_called_once_with("uuid")
        scenario._create_volume.assert_called_once_with(
            1, snapshot_id=fake_snapshot.id, fakearg="f")
        scenario._delete_snapshot.assert_called_once_with(fake_snapshot)
        scenario._delete_volume.assert_called_once_with(fake_volume)

        scenario._create_snapshot.reset_mock()
        scenario._create_volume.reset_mock()
        scenario._delete_snapshot.reset_mock()
        scenario._delete_volume.reset_mock()

        scenario.run(do_delete=False,
                     create_snapshot_kwargs=create_snapshot_args,
                     fakearg="f")

        scenario._create_snapshot.assert_called_once_with(
            "uuid", **create_snapshot_args)
        scenario._create_volume.assert_called_once_with(
            1, snapshot_id=fake_snapshot.id, fakearg="f")
        self.assertFalse(scenario._delete_snapshot.called)
        self.assertFalse(scenario._delete_volume.called)
