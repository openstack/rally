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

from rally.plugins.openstack.scenarios.cinder import volume_backups
from tests.unit import test


class CinderBackupTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(CinderBackupTestCase, self).setUp()
        patch = mock.patch(
            "rally.plugins.openstack.services.storage.block.BlockStorage")
        self.addCleanup(patch.stop)
        self.mock_cinder = patch.start()

    def _get_context(self):
        context = test.get_test_context()
        context.update({
            "admin": {
                "id": "fake_user_id",
                "credential": mock.MagicMock()
            },
            "user": {"id": "fake_user_id",
                     "credential": mock.MagicMock()},
            "tenant": {"id": "fake", "name": "fake"}})
        return context

    def test_create_incremental_volume_backup(self):
        mock_service = self.mock_cinder.return_value
        scenario = volume_backups.CreateIncrementalVolumeBackup(
            self._get_context())

        volume_kwargs = {"some_var": "zaq"}
        backup_kwargs = {"incremental": True}

        scenario.run(1, do_delete=True, create_volume_kwargs=volume_kwargs,
                     create_backup_kwargs=backup_kwargs)

        self.assertEqual(2, mock_service.create_backup.call_count)
        mock_service.create_volume.assert_called_once_with(1, **volume_kwargs)
        mock_service.delete_backup.assert_has_calls(
            mock_service.create_backup.return_value)
        mock_service.delete_volume.assert_called_once_with(
            mock_service.create_volume.return_value)
