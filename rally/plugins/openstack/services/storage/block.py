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

from rally.common import cfg
from rally.task import service


CONF = cfg.CONF


Volume = service.make_resource_cls(
    "Volume", properties=["id", "name", "size", "status"])
VolumeSnapshot = service.make_resource_cls(
    "VolumeSnapshot", properties=["id", "name", "volume_id", "status"])
VolumeBackup = service.make_resource_cls(
    "VolumeBackup", properties=["id", "name", "volume_id", "status"])
VolumeTransfer = service.make_resource_cls(
    "VolumeTransfer", properties=["id", "name", "volume_id", "auth_key"])
VolumeEncryptionType = service.make_resource_cls(
    "VolumeEncryptionType", properties=["id", "volume_type_id"])
QoSSpecs = service.make_resource_cls(
    "QoSSpecs", properties=["id", "name", "specs"])


class BlockStorage(service.UnifiedService):

    @service.should_be_overridden
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
        return self._impl.create_volume(
            size, consistencygroup_id=consistencygroup_id, group_id=group_id,
            snapshot_id=snapshot_id, source_volid=source_volid,
            name=name, description=description, volume_type=volume_type,
            user_id=user_id, project_id=project_id,
            availability_zone=availability_zone, metadata=metadata,
            imageRef=imageRef, scheduler_hints=scheduler_hints,
            source_replica=source_replica, multiattach=multiattach)

    @service.should_be_overridden
    def list_volumes(self, detailed=True):
        """Lists all volumes.

        :param detailed: Whether to return detailed volume info.
        :returns: Return volumes list.
        """
        return self._impl.list_volumes(detailed=detailed)

    @service.should_be_overridden
    def get_volume(self, volume_id):
        """Get a volume.

        :param volume_id: The ID of the volume to get.

        :returns: Return the volume.
        """
        return self._impl.get_volume(volume_id)

    @service.should_be_overridden
    def update_volume(self, volume_id,
                      name=None, description=None):
        """Update the name or description for a volume.

        :param volume_id: The updated volume id.
        :param name: The volume name.
        :param description: The volume description.

        :returns: The updated volume.
        """
        return self._impl.update_volume(
            volume_id, name=name, description=description)

    @service.should_be_overridden
    def delete_volume(self, volume):
        """Delete a volume."""
        self._impl.delete_volume(volume)

    @service.should_be_overridden
    def extend_volume(self, volume, new_size):
        """Extend the size of the specified volume."""
        return self._impl.extend_volume(volume, new_size=new_size)

    @service.should_be_overridden
    def list_snapshots(self, detailed=True):
        """Get a list of all snapshots."""
        return self._impl.list_snapshots(detailed=detailed)

    @service.should_be_overridden
    def list_types(self, search_opts=None, is_public=None):
        """Lists all volume types."""
        return self._impl.list_types(search_opts=search_opts,
                                     is_public=is_public)

    @service.should_be_overridden
    def set_metadata(self, volume, sets=10, set_size=3):
        """Update/Set a volume metadata.

        :param volume: The updated/setted volume.
        :param sets: how many operations to perform
        :param set_size: number of metadata keys to set in each operation
        :returns: A list of keys that were set
        """
        return self._impl.set_metadata(volume, sets=sets, set_size=set_size)

    @service.should_be_overridden
    def delete_metadata(self, volume, keys, deletes=10, delete_size=3):
        """Delete volume metadata keys.

        Note that ``len(keys)`` must be greater than or equal to
        ``deletes * delete_size``.

        :param volume: The volume to delete metadata from
        :param deletes: how many operations to perform
        :param delete_size: number of metadata keys to delete in each operation
        :param keys: a list of keys to choose deletion candidates from
        """
        self._impl.delete_metadata(volume, keys, deletes=deletes,
                                   delete_size=delete_size)

    @service.should_be_overridden
    def update_readonly_flag(self, volume, read_only):
        """Update the read-only access mode flag of the specified volume.

        :param volume: The UUID of the volume to update.
        :param read_only: The value to indicate whether to update volume to
            read-only access mode.
        :returns: A tuple of http Response and body
        """
        return self._impl.update_readonly_flag(volume, read_only=read_only)

    @service.should_be_overridden
    def upload_volume_to_image(self, volume, force=False,
                               container_format="bare", disk_format="raw"):
        """Upload the given volume to image.

        Returns created image.

        :param volume: volume object
        :param force: flag to indicate whether to snapshot a volume even if
                      it's attached to an instance
        :param container_format: container format of image. Acceptable
                                 formats: ami, ari, aki, bare, and ovf
        :param disk_format: disk format of image. Acceptable formats:
                            ami, ari, aki, vhd, vmdk, raw, qcow2, vdi and iso
        :returns: Returns created image object
        """
        return self._impl.upload_volume_to_image(
            volume, force=force, container_format=container_format,
            disk_format=disk_format)

    @service.should_be_overridden
    def create_qos(self, specs):
        """Create a qos specs.

        :param specs: A dict of key/value pairs to be set
        :rtype: :class:'QoSSpecs'
        """
        return self._impl.create_qos(specs)

    @service.should_be_overridden
    def list_qos(self, search_opts=None):
        """Get a list of all qos specs.

        :param search_opts: search options
        :rtype: list of :class: 'QoSpecs'
        """
        return self._impl.list_qos(search_opts)

    @service.should_be_overridden
    def get_qos(self, qos_id):
        """Get a specific qos specs.

        :param qos_id: The ID of the :class:`QoSSpecs` to get.
        :rtype: :class:`QoSSpecs`
        """
        return self._impl.get_qos(qos_id)

    @service.should_be_overridden
    def set_qos(self, qos, set_specs_args):
        """Add/Update keys in qos specs.

        :param qos: The instance of the :class:`QoSSpecs` to set
        :param set_specs_args: A dict of key/value pairs to be set
        :rtype: :class:`QoSSpecs`
        """
        return self._impl.set_qos(qos=qos,
                                  set_specs_args=set_specs_args)

    @service.should_be_overridden
    def qos_associate_type(self, qos_specs, volume_type):
        """Associate qos specs from volume type.

        :param qos_specs: The qos specs to be associated with
        :param volume_type: The volume type id to be associated with
        :rtype: :class:`QoSSpecs`
        """
        return self._impl.qos_associate_type(qos_specs, volume_type)

    @service.should_be_overridden
    def qos_disassociate_type(self, qos_specs, volume_type):
        """Disassociate qos specs from volume type.

        :param qos_specs: The qos specs to be associated with
        :param volume_type: The volume type id to be disassociated with
        :rtype: :class:`QoSSpecs`
        """
        return self._impl.qos_disassociate_type(qos_specs, volume_type)

    @service.should_be_overridden
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
        return self._impl.create_snapshot(
            volume_id, force=force, name=name,
            description=description, metadata=metadata)

    @service.should_be_overridden
    def delete_snapshot(self, snapshot):
        """Delete the given snapshot.

        Returns when the snapshot is actually deleted.

        :param snapshot: snapshot instance
        """
        self._impl.delete_snapshot(snapshot)

    @service.should_be_overridden
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
        return self._impl.create_backup(volume_id, container=container,
                                        name=name, description=description,
                                        incremental=incremental, force=force,
                                        snapshot_id=snapshot_id)

    @service.should_be_overridden
    def delete_backup(self, backup):
        """Delete a volume backup."""
        self._impl.delete_backup(backup)

    @service.should_be_overridden
    def restore_backup(self, backup_id, volume_id=None):
        """Restore the given backup.

        :param backup_id: The ID of the backup to restore.
        :param volume_id: The ID of the volume to restore the backup to.

        :returns: Return the restored backup.
        """
        return self._impl.restore_backup(backup_id, volume_id=volume_id)

    @service.should_be_overridden
    def list_backups(self, detailed=True):
        """Return user volume backups list."""
        return self._impl.list_backups(detailed=detailed)

    @service.should_be_overridden
    def list_transfers(self, detailed=True, search_opts=None):
        """Get a list of all volume transfers.

        :param detailed: If True, detailed information about transfer
                         should be listed
        :param search_opts: Search options to filter out volume transfers
        :returns: list of :class:`VolumeTransfer`
        """
        return self._impl.list_transfers(detailed=detailed,
                                         search_opts=search_opts)

    @service.should_be_overridden
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

    @service.should_be_overridden
    def get_volume_type(self, volume_type):
        """get details of volume_type.

        :param volume_type: The ID of the :class:`VolumeType` to get
        :returns: :class:`VolumeType`
        """
        return self._impl.get_volume_type(volume_type)

    @service.should_be_overridden
    def delete_volume_type(self, volume_type):
        """delete a volume type.

        :param volume_type: Name or Id of the volume type
        :returns: base on client response return True if the request
                  has been accepted or not
        """
        return self._impl.delete_volume_type(volume_type)

    @service.should_be_overridden
    def set_volume_type_keys(self, volume_type, metadata):
        """Set extra specs on a volume type.

        :param volume_type: The :class:`VolumeType` to set extra spec on
        :param metadata: A dict of key/value pairs to be set
        :returns: extra_specs if the request has been accepted
        """
        return self._impl.set_volume_type_keys(volume_type, metadata)

    @service.should_be_overridden
    def transfer_create(self, volume_id, name=None):
        """Creates a volume transfer.

        :param name: The name of created transfer
        :param volume_id: The ID of the volume to transfer.
        :returns: Return the created transfer.
        """
        return self._impl.transfer_create(volume_id, name=name)

    @service.should_be_overridden
    def transfer_accept(self, transfer_id, auth_key):
        """Accept a volume transfer.

        :param transfer_id: The ID of the transfer to accept.
        :param auth_key: The auth_key of the transfer.
        :returns: VolumeTransfer
        """
        return self._impl.transfer_accept(transfer_id, auth_key=auth_key)

    @service.should_be_overridden
    def create_encryption_type(self, volume_type, specs):
        """Create encryption type for a volume type. Default: admin only.

        :param volume_type: the volume type on which to add an encryption type
        :param specs: the encryption type specifications to add
        :return: an instance of :class: VolumeEncryptionType
        """
        return self._impl.create_encryption_type(volume_type, specs=specs)

    @service.should_be_overridden
    def get_encryption_type(self, volume_type):
        """Get the volume encryption type for the specified volume type.

        :param volume_type: the volume type to query
        :return: an instance of :class: VolumeEncryptionType
        """
        return self._impl.get_encryption_type(volume_type)

    @service.should_be_overridden
    def list_encryption_type(self, search_opts=None):
        """List all volume encryption types.

        :param search_opts: Options used when search for encryption types
        :return: a list of :class: VolumeEncryptionType instances
        """
        return self._impl.list_encryption_type(search_opts=search_opts)

    @service.should_be_overridden
    def delete_encryption_type(self, volume_type):
        """Delete the encryption type information for the specified volume type.

        :param volume_type: the volume type whose encryption type information
                            must be deleted
        """
        self._impl.delete_encryption_type(volume_type)

    @service.should_be_overridden
    def update_encryption_type(self, volume_type, specs):
        """Update the encryption type information for the specified volume type.

        :param volume_type: the volume type whose encryption type information
                            will be updated
        :param specs: the encryption type specifications to update
        :return: an instance of :class: VolumeEncryptionType
        """
        return self._impl.update_encryption_type(volume_type, specs=specs)
