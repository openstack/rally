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
from oslotest import mockpatch

from rally import exceptions
from rally.plugins.openstack.scenarios.cinder import utils
from tests.unit import fakes
from tests.unit import test

BM_UTILS = "rally.benchmark.utils"
CINDER_UTILS = "rally.plugins.openstack.scenarios.cinder.utils"


class CinderScenarioTestCase(test.TestCase):

    def setUp(self):
        super(CinderScenarioTestCase, self).setUp()
        self.res_is = mockpatch.Patch(BM_UTILS + ".resource_is")
        self.get_fm = mockpatch.Patch(BM_UTILS + ".get_from_manager")
        self.wait_for = mockpatch.Patch(CINDER_UTILS + ".bench_utils.wait_for")
        self.wait_for_delete = mockpatch.Patch(
            CINDER_UTILS + ".bench_utils.wait_for_delete")
        self.useFixture(self.wait_for)
        self.useFixture(self.wait_for_delete)
        self.useFixture(self.res_is)
        self.useFixture(self.get_fm)
        self.gfm = self.get_fm.mock
        self.useFixture(mockpatch.Patch("time.sleep"))
        self.scenario = utils.CinderScenario()

    @mock.patch(CINDER_UTILS + ".CinderScenario.clients")
    def test__list_volumes(self, mock_clients):
        volumes_list = mock.Mock()
        mock_clients("cinder").volumes.list.return_value = volumes_list
        return_volumes_list = self.scenario._list_volumes()
        self.assertEqual(volumes_list, return_volumes_list)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.list_volumes")

    @mock.patch(CINDER_UTILS + ".CinderScenario.clients")
    def test__list_snapshots(self, mock_clients):
        snapsht_lst = mock.Mock()
        mock_clients("cinder").volume_snapshots.list.return_value = snapsht_lst
        return_snapshots_list = self.scenario._list_snapshots()
        self.assertEqual(snapsht_lst, return_snapshots_list)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.list_snapshots")

    @mock.patch(CINDER_UTILS + ".CinderScenario.clients")
    def test__set_metadata(self, mock_clients):
        volume = fakes.FakeVolume()

        self.scenario._set_metadata(volume, sets=2, set_size=4)
        calls = mock_clients("cinder").volumes.set_metadata.call_args_list
        self.assertEqual(len(calls), 2)
        for call in calls:
            call_volume, metadata = call[0]
            self.assertEqual(call_volume, volume)
            self.assertEqual(len(metadata), 4)

        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.set_4_metadatas_2_times")

    @mock.patch(CINDER_UTILS + ".CinderScenario.clients")
    def test__delete_metadata(self, mock_clients):
        volume = fakes.FakeVolume()

        keys = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"]
        self.scenario._delete_metadata(volume, keys, deletes=3, delete_size=4)
        calls = mock_clients("cinder").volumes.delete_metadata.call_args_list
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

    @mock.patch(CINDER_UTILS + ".CinderScenario.clients")
    def test__delete_metadata_not_enough_keys(self, mock_clients):
        volume = fakes.FakeVolume()

        keys = ["a", "b", "c", "d", "e"]
        self.assertRaises(exceptions.InvalidArgumentsException,
                          self.scenario._delete_metadata,
                          volume, keys, deletes=2, delete_size=3)

    @mock.patch(CINDER_UTILS + ".CinderScenario.clients")
    def test__create_volume(self, mock_clients):
        CONF = cfg.CONF
        volume = mock.Mock()
        mock_clients("cinder").volumes.create.return_value = volume
        return_volume = self.scenario._create_volume(1)
        self.wait_for.mock.assert_called_once_with(
            volume,
            is_ready=self.res_is.mock(),
            update_resource=self.gfm(),
            timeout=CONF.benchmark.cinder_volume_create_timeout,
            check_interval=CONF.benchmark.cinder_volume_create_poll_interval
        )
        self.res_is.mock.assert_has_calls([mock.call("available")])
        self.assertEqual(self.wait_for.mock(), return_volume)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.create_volume")

    @mock.patch("rally.plugins.openstack.scenarios.cinder.utils.random")
    @mock.patch(CINDER_UTILS + ".CinderScenario.clients")
    def test__create_volume_with_size_range(self, mock_clients, mock_random):
        CONF = cfg.CONF
        volume = mock.Mock()
        mock_clients("cinder").volumes.create.return_value = volume
        mock_random.randint.return_value = 3

        return_volume = self.scenario._create_volume(
            size={"min": 1, "max": 5},
            display_name="TestVolume")

        mock_clients("cinder").volumes.create.assert_called_once_with(
            3, display_name="TestVolume")

        self.wait_for.mock.assert_called_once_with(
            volume,
            is_ready=self.res_is.mock(),
            update_resource=self.gfm(),
            timeout=CONF.benchmark.cinder_volume_create_timeout,
            check_interval=CONF.benchmark.cinder_volume_create_poll_interval
        )
        self.res_is.mock.assert_has_calls([mock.call("available")])
        self.assertEqual(self.wait_for.mock(), return_volume)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.create_volume")

    def test__delete_volume(self):
        cinder = mock.Mock()
        self.scenario._delete_volume(cinder)
        cinder.delete.assert_called_once_with()
        self.wait_for_delete.mock.assert_called_once_with(
            cinder,
            update_resource=self.gfm(),
            timeout=cfg.CONF.benchmark.cinder_volume_create_timeout,
            check_interval=cfg.CONF.benchmark
            .cinder_volume_create_poll_interval)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.delete_volume")

    @mock.patch("rally.plugins.openstack.scenarios.cinder.utils.random")
    @mock.patch(CINDER_UTILS + ".CinderScenario.clients")
    def test__extend_volume_with_size_range(self, mock_clients, mock_random):
        CONF = cfg.CONF
        volume = mock.Mock()
        mock_random.randint.return_value = 3
        mock_clients("cinder").volumes.extend.return_value = volume

        self.scenario._extend_volume(volume, new_size={"min": 1, "max": 5})

        volume.extend.assert_called_once_with(volume, 3)
        self.wait_for.mock.assert_called_once_with(
            volume,
            is_ready=self.res_is.mock(),
            update_resource=self.gfm(),
            timeout=CONF.benchmark.cinder_volume_create_timeout,
            check_interval=CONF.benchmark.cinder_volume_create_poll_interval
        )
        self.res_is.mock.assert_has_calls([mock.call("available")])
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.extend_volume")

    @mock.patch(CINDER_UTILS + ".CinderScenario.clients")
    def test__extend_volume(self, mock_clients):
        CONF = cfg.CONF
        volume = mock.Mock()
        mock_clients("cinder").volumes.extend.return_value = volume
        self.scenario._extend_volume(volume, 2)
        self.wait_for.mock.assert_called_once_with(
            volume,
            is_ready=self.res_is.mock(),
            update_resource=self.gfm(),
            timeout=CONF.benchmark.cinder_volume_create_timeout,
            check_interval=CONF.benchmark.cinder_volume_create_poll_interval
        )
        self.res_is.mock.assert_has_calls([mock.call("available")])
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.extend_volume")

    @mock.patch(CINDER_UTILS + ".CinderScenario.clients")
    def test__upload_volume_to_image(self, mock_clients):
        volume = mock.Mock()
        image = {"os-volume_upload_image": {"image_id": 1}}
        volume.upload_to_image.return_value = (None, image)
        mock_clients("cinder").images.get.return_value = image

        self.scenario._generate_random_name = mock.Mock(
            return_value="test_vol")
        self.scenario._upload_volume_to_image(volume, False,
                                              "container", "disk")

        volume.upload_to_image.assert_called_once_with(False, "test_vol",
                                                       "container", "disk")
        self.assertTrue(self.wait_for.mock.called)
        self.assertEqual(2, self.wait_for.mock.call_count)

    @mock.patch(CINDER_UTILS + ".CinderScenario.clients")
    def test__create_snapshot(self, mock_clients):
        snapshot = mock.Mock()
        mock_clients("cinder").volume_snapshots.create.return_value = snapshot

        return_snapshot = self.scenario._create_snapshot("uuid", False)

        self.wait_for.mock.assert_called_once_with(
            snapshot,
            is_ready=self.res_is.mock(),
            update_resource=self.gfm(),
            timeout=cfg.CONF.benchmark.cinder_volume_create_timeout,
            check_interval=cfg.CONF.benchmark
            .cinder_volume_create_poll_interval)
        self.res_is.mock.assert_has_calls([mock.call("available")])
        self.assertEqual(self.wait_for.mock(), return_snapshot)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.create_snapshot")

    def test__delete_snapshot(self):
        snapshot = mock.Mock()
        self.scenario._delete_snapshot(snapshot)
        snapshot.delete.assert_called_once_with()
        self.wait_for_delete.mock.assert_called_once_with(
            snapshot,
            update_resource=self.gfm(),
            timeout=cfg.CONF.benchmark.cinder_volume_create_timeout,
            check_interval=cfg.CONF.benchmark
            .cinder_volume_create_poll_interval)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.delete_snapshot")

    @mock.patch(CINDER_UTILS + ".CinderScenario.clients")
    def test__create_backup(self, mock_clients):
        backup = mock.Mock()
        mock_clients("cinder").backups.create.return_value = backup

        return_backup = self.scenario._create_backup("uuid")

        self.wait_for.mock.assert_called_once_with(
            backup,
            is_ready=self.res_is.mock(),
            update_resource=self.gfm(),
            timeout=cfg.CONF.benchmark.cinder_volume_create_timeout,
            check_interval=cfg.CONF.benchmark
            .cinder_volume_create_poll_interval)
        self.res_is.mock.assert_has_calls([mock.call("available")])
        self.assertEqual(self.wait_for.mock(), return_backup)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.create_backup")

    def test__delete_backup(self):
        backup = mock.Mock()
        self.scenario._delete_backup(backup)
        backup.delete.assert_called_once_with()
        self.wait_for_delete.mock.assert_called_once_with(
            backup,
            update_resource=self.gfm(),
            timeout=cfg.CONF.benchmark.cinder_volume_create_timeout,
            check_interval=cfg.CONF.benchmark
            .cinder_volume_create_poll_interval)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.delete_backup")

    @mock.patch(CINDER_UTILS + ".CinderScenario.clients")
    def test__restore_backup(self, mock_clients):
        backup = mock.Mock()
        restore = mock.Mock()
        mock_clients("cinder").restores.restore.return_value = backup
        mock_clients("cinder").volumes.get.return_value = restore

        return_restore = self.scenario._restore_backup(backup.id, None)

        self.wait_for.mock.assert_called_once_with(
            restore,
            is_ready=self.res_is.mock(),
            update_resource=self.gfm(),
            timeout=cfg.CONF.benchmark.cinder_volume_create_timeout,
            check_interval=cfg.CONF.benchmark
            .cinder_volume_create_poll_interval)
        self.res_is.mock.assert_has_calls([mock.call("available")])
        self.assertEqual(self.wait_for.mock(), return_restore)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "cinder.restore_backup")

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
