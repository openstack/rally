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
from oslo_config import cfg

from rally import exceptions
from rally import osclients
from rally.plugins.openstack.scenarios.cinder import utils
from tests.unit import fakes
from tests.unit import test

CINDER_UTILS = "rally.plugins.openstack.scenarios.cinder.utils"
CONF = cfg.CONF


class CinderScenarioTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(CinderScenarioTestCase, self).setUp()
        wrap = mock.patch("rally.plugins.openstack.wrappers.cinder.wrap")
        self.mock_wrap = wrap.start()
        self.addCleanup(self.mock_wrap.stop)
        self.scenario = utils.CinderScenario(
            self.context,
            clients=osclients.Clients(
                fakes.FakeUserContext.user["credential"]))

    def test__list_volumes(self):
        return_volumes_list = self.scenario._list_volumes()
        self.assertEqual(self.clients("cinder").volumes.list.return_value,
                         return_volumes_list)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.list_volumes")

    def test__list_types(self):
        return_types_list = self.scenario._list_types()
        self.assertEqual(self.clients("cinder").volume_types.list.return_value,
                         return_types_list)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.list_types")

    def test__get_volume(self):
        volume = fakes.FakeVolume()
        self.assertEqual(self.clients("cinder").volumes.get.return_value,
                         self.scenario._get_volume(volume.id))
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.get_volume")

    def test__list_snapshots(self):
        return_snapshots_list = self.scenario._list_snapshots()
        self.assertEqual(
            self.clients("cinder").volume_snapshots.list.return_value,
            return_snapshots_list)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.list_snapshots")

    def test__list_transfers(self):
        return_transfers_list = self.scenario._list_transfers()
        self.assertEqual(
            self.clients("cinder").transfers.list.return_value,
            return_transfers_list)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.list_transfers")

    def test__set_metadata(self):
        volume = fakes.FakeVolume()

        self.scenario._set_metadata(volume, sets=2, set_size=4)
        calls = self.clients("cinder").volumes.set_metadata.call_args_list
        self.assertEqual(len(calls), 2)
        for call in calls:
            call_volume, metadata = call[0]
            self.assertEqual(call_volume, volume)
            self.assertEqual(len(metadata), 4)

        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.set_4_metadatas_2_times")

    def test__delete_metadata(self):
        volume = fakes.FakeVolume()

        keys = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"]
        self.scenario._delete_metadata(volume, keys, deletes=3, delete_size=4)
        calls = self.clients("cinder").volumes.delete_metadata.call_args_list
        self.assertEqual(len(calls), 3)
        all_deleted = []
        for call in calls:
            call_volume, del_keys = call[0]
            self.assertEqual(call_volume, volume)
            self.assertEqual(len(del_keys), 4)
            for key in del_keys:
                self.assertIn(key, keys)
                self.assertNotIn(key, all_deleted)
                all_deleted.append(key)

        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.delete_4_metadatas_3_times")

    def test__delete_metadata_not_enough_keys(self):
        volume = fakes.FakeVolume()

        keys = ["a", "b", "c", "d", "e"]
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.scenario._delete_metadata,
                          volume, keys, deletes=2, delete_size=3)

    def test__create_volume(self):
        return_volume = self.scenario._create_volume(1)
        self.mock_wait_for.mock.assert_called_once_with(
            self.mock_wrap.return_value.create_volume.return_value,
            ready_statuses=["available"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            timeout=CONF.benchmark.cinder_volume_create_timeout,
            check_interval=CONF.benchmark.cinder_volume_create_poll_interval
        )
        self.mock_get_from_manager.mock.assert_called_once_with()
        self.assertEqual(self.mock_wait_for.mock.return_value, return_volume)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.create_volume")

    @mock.patch("rally.plugins.openstack.scenarios.cinder.utils.random")
    def test__create_volume_with_size_range(self, mock_random):
        mock_random.randint.return_value = 3

        return_volume = self.scenario._create_volume(
            size={"min": 1, "max": 5},
            display_name="TestVolume")

        self.mock_wrap.return_value.create_volume.assert_called_once_with(
            3, display_name="TestVolume")

        self.mock_wait_for.mock.assert_called_once_with(
            self.mock_wrap.return_value.create_volume.return_value,
            ready_statuses=["available"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            timeout=CONF.benchmark.cinder_volume_create_timeout,
            check_interval=CONF.benchmark.cinder_volume_create_poll_interval
        )
        self.mock_get_from_manager.mock.assert_called_once_with()
        self.assertEqual(self.mock_wait_for.mock.return_value, return_volume)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.create_volume")

    def test__update_volume(self):
        fake_volume = mock.MagicMock()
        volume_update_args = {"display_name": "_updated",
                              "display_description": "_updated"}

        self.scenario._update_volume(fake_volume, **volume_update_args)
        self.mock_wrap.return_value.update_volume.assert_called_once_with(
            fake_volume,
            display_name="_updated",
            display_description="_updated")
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.update_volume")

    def test__update_readonly_flag(self):
        fake_volume = mock.MagicMock()
        self.scenario._update_readonly_flag(fake_volume, "fake_flag")
        self.clients(
            "cinder").volumes.update_readonly_flag.assert_called_once_with(
            fake_volume, "fake_flag")
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.update_readonly_flag")

    def test__delete_volume(self):
        cinder = mock.Mock()
        self.scenario._delete_volume(cinder)
        cinder.delete.assert_called_once_with()
        self.mock_wait_for_status.mock.assert_called_once_with(
            cinder,
            ready_statuses=["deleted"],
            check_deletion=True,
            update_resource=self.mock_get_from_manager.mock.return_value,
            timeout=cfg.CONF.benchmark.cinder_volume_create_timeout,
            check_interval=cfg.CONF.benchmark
            .cinder_volume_create_poll_interval)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.delete_volume")

    @mock.patch("rally.plugins.openstack.scenarios.cinder.utils.random")
    def test__extend_volume_with_size_range(self, mock_random):
        volume = mock.Mock()
        mock_random.randint.return_value = 3
        self.clients("cinder").volumes.extend.return_value = volume

        self.scenario._extend_volume(volume, new_size={"min": 1, "max": 5})

        volume.extend.assert_called_once_with(volume, 3)
        self.mock_wait_for.mock.assert_called_once_with(
            volume,
            ready_statuses=["available"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            timeout=CONF.benchmark.cinder_volume_create_timeout,
            check_interval=CONF.benchmark.cinder_volume_create_poll_interval
        )
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.extend_volume")

    def test__extend_volume(self):
        volume = mock.Mock()
        self.clients("cinder").volumes.extend.return_value = volume
        self.scenario._extend_volume(volume, 2)
        self.mock_wait_for.mock.assert_called_once_with(
            volume,
            ready_statuses=["available"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            timeout=CONF.benchmark.cinder_volume_create_timeout,
            check_interval=CONF.benchmark.cinder_volume_create_poll_interval
        )
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.extend_volume")

    @mock.patch("rally.plugins.openstack.wrappers.glance.wrap")
    def test__upload_volume_to_image(self, mock_wrap):
        volume = mock.Mock()
        image = {"os-volume_upload_image": {"image_id": 1}}
        volume.upload_to_image.return_value = (None, image)
        self.clients("cinder").images.get.return_value = image

        self.scenario.generate_random_name = mock.Mock(
            return_value="test_vol")
        self.scenario._upload_volume_to_image(volume, False,
                                              "container", "disk")

        volume.upload_to_image.assert_called_once_with(False, "test_vol",
                                                       "container", "disk")
        self.mock_wait_for.mock.assert_has_calls([
            mock.call(
                volume,
                ready_statuses=["available"],
                update_resource=self.mock_get_from_manager.mock.return_value,
                timeout=CONF.benchmark.cinder_volume_create_timeout,
                check_interval=CONF.benchmark.
                cinder_volume_create_poll_interval),
            mock.call(
                self.clients("glance").images.get.return_value,
                ready_statuses=["active"],
                update_resource=mock_wrap.return_value.get_image,
                timeout=CONF.benchmark.glance_image_create_timeout,
                check_interval=CONF.benchmark.
                glance_image_create_poll_interval)
        ])
        self.mock_get_from_manager.mock.assert_called_once_with()
        self.clients("glance").images.get.assert_called_once_with(1)

    def test__create_snapshot(self):
        return_snapshot = self.scenario._create_snapshot("uuid", False)

        self.mock_wait_for.mock.assert_called_once_with(
            self.mock_wrap.return_value.create_snapshot.return_value,
            ready_statuses=["available"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            timeout=cfg.CONF.benchmark.cinder_volume_create_timeout,
            check_interval=cfg.CONF.benchmark
            .cinder_volume_create_poll_interval)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self.assertEqual(self.mock_wait_for.mock.return_value, return_snapshot)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.create_snapshot")

    def test__delete_snapshot(self):
        snapshot = mock.Mock()
        self.scenario._delete_snapshot(snapshot)
        snapshot.delete.assert_called_once_with()
        self.mock_wait_for_status.mock.assert_called_once_with(
            snapshot,
            ready_statuses=["deleted"],
            check_deletion=True,
            update_resource=self.mock_get_from_manager.mock.return_value,
            timeout=cfg.CONF.benchmark.cinder_volume_create_timeout,
            check_interval=cfg.CONF.benchmark
            .cinder_volume_create_poll_interval)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.delete_snapshot")

    def test__create_backup(self):
        return_backup = self.scenario._create_backup("uuid")

        self.mock_wait_for.mock.assert_called_once_with(
            self.clients("cinder").backups.create.return_value,
            ready_statuses=["available"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            timeout=cfg.CONF.benchmark.cinder_volume_create_timeout,
            check_interval=cfg.CONF.benchmark
            .cinder_volume_create_poll_interval)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self.assertEqual(self.mock_wait_for.mock.return_value, return_backup)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.create_backup")

    def test__delete_backup(self):
        backup = mock.Mock()
        self.scenario._delete_backup(backup)
        backup.delete.assert_called_once_with()
        self.mock_wait_for_status.mock.assert_called_once_with(
            backup,
            ready_statuses=["deleted"],
            check_deletion=True,
            update_resource=self.mock_get_from_manager.mock.return_value,
            timeout=cfg.CONF.benchmark.cinder_volume_create_timeout,
            check_interval=cfg.CONF.benchmark
            .cinder_volume_create_poll_interval)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.delete_backup")

    def test__restore_backup(self):
        backup = mock.Mock()
        restore = mock.Mock()
        self.clients("cinder").restores.restore.return_value = backup
        self.clients("cinder").volumes.get.return_value = restore

        return_restore = self.scenario._restore_backup(backup.id, None)

        self.mock_wait_for.mock.assert_called_once_with(
            restore,
            ready_statuses=["available"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            timeout=cfg.CONF.benchmark.cinder_volume_create_timeout,
            check_interval=cfg.CONF.benchmark
            .cinder_volume_create_poll_interval)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self.assertEqual(self.mock_wait_for.mock.return_value, return_restore)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.restore_backup")

    def test__list_backups(self):
        return_backups_list = self.scenario._list_backups()
        self.assertEqual(
            self.clients("cinder").backups.list.return_value,
            return_backups_list)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.list_backups")

    def test__get_random_server(self):
        servers = [1, 2, 3]
        context = {"user": {"tenant_id": "fake"},
                   "users": [{"tenant_id": "fake",
                              "users_per_tenant": 1}],
                   "tenant": {"id": "fake", "servers": servers}}
        self.scenario.context = context
        self.scenario.clients = mock.Mock()
        self.scenario.clients("nova").servers.get = mock.Mock(
            side_effect=lambda arg: arg)

        server_id = self.scenario.get_random_server()

        self.assertIn(server_id, servers)

    def test__create_volume_type(self, **kwargs):
        random_name = "random_name"
        self.scenario.generate_random_name = mock.Mock(
            return_value=random_name)

        result = self.scenario._create_volume_type()

        self.assertEqual(
            self.admin_clients("cinder").volume_types.create.return_value,
            result)
        admin_clients = self.admin_clients("cinder")
        admin_clients.volume_types.create.assert_called_once_with(
            name="random_name")
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.create_volume_type")

    def test__create_encryption_type(self):
        volume_type = mock.Mock()
        specs = {
            "provider": "foo_pro",
            "cipher": "foo_cip",
            "key_size": 512,
            "control_location": "foo_con"
        }
        result = self.scenario._create_encryption_type(volume_type, specs)

        self.assertEqual(
            self.admin_clients(
                "cinder").volume_encryption_types.create.return_value, result)
        self.admin_clients(
            "cinder").volume_encryption_types.create.assert_called_once_with(
                volume_type, specs)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.create_encryption_type")

    def test__delete_volume_type(self):
        volume_type = mock.Mock()
        self.scenario._delete_volume_type(volume_type)
        admin_clients = self.admin_clients("cinder")
        admin_clients.volume_types.delete.assert_called_once_with(
            volume_type)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.delete_volume_type")

    def test__transfer_create(self):
        fake_volume = mock.MagicMock()
        random_name = "random_name"
        self.scenario.generate_random_name = mock.MagicMock(
            return_value=random_name)
        result = self.scenario._transfer_create(fake_volume.id)
        self.assertEqual(
            self.clients("cinder").transfers.create.return_value,
            result)
        self.clients("cinder").transfers.create.assert_called_once_with(
            fake_volume.id, random_name)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.transfer_create")

    def test__transfer_accept(self):
        fake_transfer = mock.MagicMock()
        result = self.scenario._transfer_accept(fake_transfer.id, "fake_key")
        self.assertEqual(
            self.clients("cinder").transfers.accept.return_value,
            result)
        self.clients("cinder").transfers.accept.assert_called_once_with(
            fake_transfer.id, "fake_key")
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.transfer_accept")
