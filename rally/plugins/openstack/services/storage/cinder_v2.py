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

import random

from rally.common import utils as rutils
from rally.plugins.openstack import service
from rally.plugins.openstack.services.storage import block
from rally.plugins.openstack.services.storage import cinder_common
from rally.task import atomic

CONF = block.CONF


@service.service("cinder", service_type="block-storage", version="2")
class CinderV2Service(service.Service, cinder_common.CinderMixin):

    @atomic.action_timer("cinder_v2.create_volume")
    def create_volume(self, size, consistencygroup_id=None,
                      snapshot_id=None, source_volid=None, name=None,
                      description=None, volume_type=None, user_id=None,
                      project_id=None, availability_zone=None,
                      metadata=None, imageRef=None, scheduler_hints=None,
                      source_replica=None, multiattach=False):
        """Creates a volume.

        :param size: Size of volume in GB
        :param consistencygroup_id: ID of the consistencygroup
        :param snapshot_id: ID of the snapshot
        :param name: Name of the volume
        :param description: Description of the volume
        :param volume_type: Type of volume
        :param user_id: User id derived from context
        :param project_id: Project id derived from context
        :param availability_zone: Availability Zone to use
        :param metadata: Optional metadata to set on volume creation
        :param imageRef: reference to an image stored in glance
        :param source_volid: ID of source volume to clone from
        :param source_replica: ID of source volume to clone replica
        :param scheduler_hints: (optional extension) arbitrary key-value pairs
                            specified by the client to help boot an instance
        :param multiattach: Allow the volume to be attached to more than
                            one instance

        :returns: Return a new volume.
        """
        kwargs = {"name": name or self.generate_random_name(),
                  "description": description,
                  "consistencygroup_id": consistencygroup_id,
                  "snapshot_id": snapshot_id,
                  "source_volid": source_volid,
                  "volume_type": volume_type,
                  "user_id": user_id,
                  "project_id": project_id,
                  "availability_zone": availability_zone,
                  "metadata": metadata,
                  "imageRef": imageRef,
                  "scheduler_hints": scheduler_hints,
                  "source_replica": source_replica,
                  "multiattach": multiattach}
        if isinstance(size, dict):
            size = random.randint(size["min"], size["max"])

        volume = (self._get_client()
                  .volumes.create(size, **kwargs))

        # NOTE(msdubov): It is reasonable to wait 5 secs before starting to
        #                check whether the volume is ready => less API calls.
        rutils.interruptable_sleep(
            CONF.openstack.cinder_volume_create_prepoll_delay)

        return self._wait_available_volume(volume)

    @atomic.action_timer("cinder_v2.update_volume")
    def update_volume(self, volume_id, name=None, description=None):
        """Update the name or description for a volume.

        :param volume_id: The updated volume id.
        :param name: The volume name.
        :param description: The volume description.

        :returns: The updated volume.
        """
        kwargs = {}
        if name is not None:
            kwargs["name"] = name
        if description is not None:
            kwargs["description"] = description
        updated_volume = self._get_client().volumes.update(
            volume_id, **kwargs)
        return updated_volume["volume"]

    @atomic.action_timer("cinder_v2.list_types")
    def list_types(self, search_opts=None, is_public=None):
        """Lists all volume types."""
        return (self._get_client()
                .volume_types.list(search_opts=search_opts,
                                   is_public=is_public))

    @atomic.action_timer("cinder_v2.create_snapshot")
    def create_snapshot(self, volume_id, force=False,
                        name=None, description=None, metadata=None):
        """Create one snapshot.

        Returns when the snapshot is actually created and is in the "Available"
        state.

        :param volume_id: volume uuid for creating snapshot
        :param force: flag to indicate whether to snapshot a volume even if
                      it's attached to an instance
        :param name: Name of the snapshot
        :param description: Description of the snapshot
        :returns: Created snapshot object
        """
        kwargs = {"force": force,
                  "name": name or self.generate_random_name(),
                  "description": description,
                  "metadata": metadata}

        snapshot = self._get_client().volume_snapshots.create(volume_id,
                                                              **kwargs)
        rutils.interruptable_sleep(
            CONF.openstack.cinder_volume_create_prepoll_delay)
        snapshot = self._wait_available_volume(snapshot)
        return snapshot

    @atomic.action_timer("cinder_v2.create_backup")
    def create_backup(self, volume_id, container=None,
                      name=None, description=None,
                      incremental=False, force=False,
                      snapshot_id=None):
        """Create a volume backup of the given volume.

        :param volume_id: The ID of the volume to backup.
        :param container: The name of the backup service container.
        :param name: The name of the backup.
        :param description: The description of the backup.
        :param incremental: Incremental backup.
        :param force: If True, allows an in-use volume to be backed up.
        :param snapshot_id: The ID of the snapshot to backup.
        """
        kwargs = {"force": force,
                  "name": name or self.generate_random_name(),
                  "description": description,
                  "container": container,
                  "incremental": incremental,
                  "force": force,
                  "snapshot_id": snapshot_id}
        backup = self._get_client().backups.create(volume_id, **kwargs)
        return self._wait_available_volume(backup)

    @atomic.action_timer("cinder_v2.create_volume_type")
    def create_volume_type(self, name=None, description=None, is_public=True):
        """create volume type.

        :param name: Descriptive name of the volume type
        :param description: Description of the volume type
        :param is_public: Volume type visibility
        :returns: Return the created volume type.
        :returns: VolumeType object
        """
        kwargs = {"name": name or self.generate_random_name(),
                  "description": description,
                  "is_public": is_public}
        return self._get_client().volume_types.create(**kwargs)

    @atomic.action_timer("cinder_v2.update_volume_type")
    def update_volume_type(self, volume_type, name=None,
                           description=None, is_public=None):
        """Update the name and/or description for a volume type.

        :param volume_type: The ID or an instance of the :class:`VolumeType`
                            to update.
        :param name: if None, updates name by generating random name.
                     else updates name with provided name
        :param description: Description of the volume type.
        :rtype: :class:`VolumeType`
        """
        name = name or self.generate_random_name()

        return self._get_client().volume_types.update(volume_type, name,
                                                      description, is_public)

    @atomic.action_timer("cinder_v2.add_type_access")
    def add_type_access(self, volume_type, project):
        """Add a project to the given volume type access list.

        :param volume_type: Volume type name or ID to add access for the given
                            project
        :project: Project ID to add volume type access for
        :return: An instance of cinderclient.apiclient.base.TupleWithMeta
        """
        return self._get_client().volume_type_access.add_project_access(
            volume_type, project)

    @atomic.action_timer("cinder_v2.list_type_access")
    def list_type_access(self, volume_type):
        """Print access information about the given volume type

        :param volume_type: Filter results by volume type name or ID
        :return: VolumeTypeAcces of specific project
        """
        return self._get_client().volume_type_access.list(volume_type)


@service.compat_layer(CinderV2Service)
class UnifiedCinderV2Service(cinder_common.UnifiedCinderMixin,
                             block.BlockStorage):

    @staticmethod
    def _unify_volume(volume):
        if isinstance(volume, dict):
            return block.Volume(id=volume["id"], name=volume["name"],
                                size=volume["size"], status=volume["status"])
        else:
            return block.Volume(id=volume.id, name=volume.name,
                                size=volume.size, status=volume.status)

    @staticmethod
    def _unify_snapshot(snapshot):
        return block.VolumeSnapshot(id=snapshot.id, name=snapshot.name,
                                    volume_id=snapshot.volume_id,
                                    status=snapshot.status)

    def create_volume(self, size, consistencygroup_id=None,
                      group_id=None, snapshot_id=None, source_volid=None,
                      name=None, description=None,
                      volume_type=None, user_id=None,
                      project_id=None, availability_zone=None,
                      metadata=None, imageRef=None, scheduler_hints=None,
                      source_replica=None, multiattach=False):
        """Creates a volume.

        :param size: Size of volume in GB
        :param consistencygroup_id: ID of the consistencygroup
        :param group_id: ID of the group
        :param snapshot_id: ID of the snapshot
        :param name: Name of the volume
        :param description: Description of the volume
        :param volume_type: Type of volume
        :param user_id: User id derived from context
        :param project_id: Project id derived from context
        :param availability_zone: Availability Zone to use
        :param metadata: Optional metadata to set on volume creation
        :param imageRef: reference to an image stored in glance
        :param source_volid: ID of source volume to clone from
        :param source_replica: ID of source volume to clone replica
        :param scheduler_hints: (optional extension) arbitrary key-value pairs
                            specified by the client to help boot an instance
        :param multiattach: Allow the volume to be attached to more than
                            one instance

        :returns: Return a new volume.
        """
        return self._unify_volume(self._impl.create_volume(
            size, consistencygroup_id=consistencygroup_id,
            snapshot_id=snapshot_id,
            source_volid=source_volid, name=name,
            description=description, volume_type=volume_type,
            user_id=user_id, project_id=project_id,
            availability_zone=availability_zone, metadata=metadata,
            imageRef=imageRef, scheduler_hints=scheduler_hints,
            source_replica=source_replica, multiattach=multiattach))

    def list_volumes(self, detailed=True):
        """Lists all volumes.

        :param detailed: Whether to return detailed volume info.
        :returns: Return volumes list.
        """
        return [self._unify_volume(volume)
                for volume in self._impl.list_volumes(detailed=detailed)]

    def get_volume(self, volume_id):
        """Get a volume.

        :param volume_id: The ID of the volume to get.

        :returns: Return the volume.
        """
        return self._unify_volume(self._impl.get_volume(volume_id))

    def extend_volume(self, volume, new_size):
        """Extend the size of the specified volume."""
        return self._unify_volume(
            self._impl.extend_volume(volume, new_size=new_size))

    def update_volume(self, volume_id,
                      name=None, description=None):
        """Update the name or description for a volume.

        :param volume_id: The updated volume id.
        :param name: The volume name.
        :param description: The volume description.

        :returns: The updated volume.
        """
        return self._unify_volume(self._impl.update_volume(
            volume_id, name=name, description=description))

    def list_types(self, search_opts=None, is_public=None):
        """Lists all volume types."""
        return self._impl.list_types(search_opts=search_opts,
                                     is_public=is_public)

    def create_snapshot(self, volume_id, force=False,
                        name=None, description=None, metadata=None):
        """Create one snapshot.

        Returns when the snapshot is actually created and is in the "Available"
        state.

        :param volume_id: volume uuid for creating snapshot
        :param force: If force is True, create a snapshot even if the volume is
                      attached to an instance. Default is False.
        :param name: Name of the snapshot
        :param description: Description of the snapshot
        :param metadata: Metadata of the snapshot
        :returns: Created snapshot object
        """
        return self._unify_snapshot(self._impl.create_snapshot(
            volume_id, force=force, name=name,
            description=description, metadata=metadata))

    def list_snapshots(self, detailed=True):
        """Get a list of all snapshots."""
        return [self._unify_snapshot(snapshot)
                for snapshot in self._impl.list_snapshots(detailed=detailed)]

    def create_backup(self, volume_id, container=None,
                      name=None, description=None,
                      incremental=False, force=False,
                      snapshot_id=None):
        """Creates a volume backup.

        :param volume_id: The ID of the volume to backup.
        :param container: The name of the backup service container.
        :param name: The name of the backup.
        :param description: The description of the backup.
        :param incremental: Incremental backup.
        :param force: If True, allows an in-use volume to be backed up.
        :param snapshot_id: The ID of the snapshot to backup.

        :returns: The created backup object.
        """
        return self._unify_backup(self._impl.create_backup(
            volume_id, container=container, name=name, description=description,
            incremental=incremental, force=force, snapshot_id=snapshot_id))

    def create_volume_type(self, name=None, description=None, is_public=True):
        """Creates a volume type.

        :param name: Descriptive name of the volume type
        :param description: Description of the volume type
        :param is_public: Volume type visibility
        :returns: Return the created volume type.
        """
        return self._impl.create_volume_type(name=name,
                                             description=description,
                                             is_public=is_public)

    def restore_backup(self, backup_id, volume_id=None):
        """Restore the given backup.

        :param backup_id: The ID of the backup to restore.
        :param volume_id: The ID of the volume to restore the backup to.

        :returns: Return the restored backup.
        """
        return self._unify_volume(self._impl.restore_backup(
            backup_id, volume_id=volume_id))
