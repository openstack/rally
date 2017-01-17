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

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.cinder import utils as cinder_utils
from rally.task import validation


"""Scenarios for Cinder Volume Backup."""


@validation.number("size", minval=1, integer_only=True)
@validation.required_cinder_services("cinder-backup")
@validation.required_services(consts.Service.CINDER)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["cinder"]},
                    name="CinderVolumeBackups."
                    "create_incremental_volume_backup")
class CreateIncrementalVolumeBackup(cinder_utils.CinderScenario):
    def run(self, size, do_delete=True, create_volume_kwargs=None,
            create_backup_kwargs=None):
        """Create a incremental volume backup.

        The scenario first create a volume, the create a backup, the backup
        is full backup. Because Incremental backup must be based on the
        full backup. finally create a incremental backup.

        :param size: volume size in GB
        :param do_delete: deletes backup and volume after creating if True
        :param create_volume_kwargs: optional args to create a volume
        :param create_backup_kwargs: optional args to create a volume backup
        """
        create_volume_kwargs = create_volume_kwargs or {}
        create_backup_kwargs = create_backup_kwargs or {}

        volume = self._create_volume(size, **create_volume_kwargs)
        backup1 = self._create_backup(volume.id, **create_backup_kwargs)

        backup2 = self._create_backup(volume.id, incremental=True)

        if do_delete:
            self._delete_backup(backup2)
            self._delete_backup(backup1)
            self._delete_volume(volume)
