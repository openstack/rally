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

    def test_create_incremental_volume_backup(self):
        fake_volume = mock.MagicMock()
        fake_backup = mock.MagicMock()
        scenario = volume_backups.CreateIncrementalVolumeBackup(self.context)
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)
        scenario._create_backup = mock.MagicMock(return_value=fake_backup)
        scenario._delete_volume = mock.MagicMock()
        scenario._delete_backup = mock.MagicMock()

        volume_kwargs = {"some_var": "zaq"}
        backup_kwargs = {"incremental": True}

        scenario.run(1, do_delete=True, create_volume_kwargs=volume_kwargs,
                     create_backup_kwargs=backup_kwargs)

        self.assertEqual(2, scenario._create_backup.call_count)
        scenario._create_volume.assert_called_once_with(1, **volume_kwargs)
        scenario._delete_backup.assert_has_calls(fake_backup)
        scenario._delete_volume.assert_called_once_with(fake_volume)
