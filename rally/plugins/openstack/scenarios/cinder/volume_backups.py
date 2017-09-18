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


@validation.add("number", param_name="size", minval=1, integer_only=True)
@validation.add("restricted_parameters", param_names=["name", "display_name"],
                subdict="create_volume_kwargs")
@validation.add("restricted_parameters", param_names="name",
                subdict="create_backup_kwargs")
@validation.add("required_services", services=[consts.Service.CINDER])
@validation.add("required_cinder_services", services="cinder-backup")
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(
    context={"cleanup@openstack": ["cinder"]},
    name="CinderVolumeBackups.create_incremental_volume_backup",
    platform="openstack")
class CreateIncrementalVolumeBackup(cinder_utils.CinderBasic):
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

        volume = self.cinder.create_volume(size, **create_volume_kwargs)
        backup1 = self.cinder.create_backup(volume.id, **create_backup_kwargs)

        backup2 = self.cinder.create_backup(volume.id, incremental=True)

        if do_delete:
            self.cinder.delete_backup(backup2)
            self.cinder.delete_backup(backup1)
            self.cinder.delete_volume(volume)
