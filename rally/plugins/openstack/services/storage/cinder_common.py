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

from rally import exceptions
from rally.plugins.openstack.services.image import image
from rally.plugins.openstack.services.storage import block
from rally.task import atomic
from rally.task import utils as bench_utils

CONF = block.CONF


class CinderMixin(object):

    def _get_client(self):
        return self._clients.cinder(self.version)

    def _update_resource(self, resource):
        try:
            manager = getattr(resource, "manager", None)
            if manager:
                res = manager.get(resource.id)
            else:
                if isinstance(resource, block.Volume):
                    attr = "volumes"
                elif isinstance(resource, block.VolumeSnapshot):
                    attr = "volume_snapshots"
                elif isinstance(resource, block.VolumeBackup):
                    attr = "backups"
                res = getattr(self._get_client(), attr).get(resource.id)
        except Exception as e:
            if getattr(e, "code", getattr(e, "http_status", 400)) == 404:
                raise exceptions.GetResourceNotFound(resource=resource)
            raise exceptions.GetResourceFailure(resource=resource, err=e)
        return res

    def _wait_available_volume(self, volume):
        return bench_utils.wait_for_status(
            volume,
            ready_statuses=["available"],
            update_resource=self._update_resource,
            timeout=CONF.openstack.cinder_volume_create_timeout,
            check_interval=CONF.openstack.cinder_volume_create_poll_interval
        )

    def list_volumes(self, detailed=True):
        """List all volumes."""
        aname = "cinder_v%s.list_volumes" % self.version
        with atomic.ActionTimer(self, aname):
            return self._get_client().volumes.list(detailed)

    def get_volume(self, volume_id):
        """Get target volume information."""
        aname = "cinder_v%s.get_volume" % self.version
        with atomic.ActionTimer(self, aname):
            return self._get_client().volumes.get(volume_id)

    def delete_volume(self, volume):
        """Delete target volume."""
        aname = "cinder_v%s.delete_volume" % self.version
        with atomic.ActionTimer(self, aname):
            self._get_client().volumes.delete(volume)
            bench_utils.wait_for_status(
                volume,
                ready_statuses=["deleted"],
                check_deletion=True,
                update_resource=self._update_resource,
                timeout=CONF.openstack.cinder_volume_delete_timeout,
                check_interval=(CONF.openstack
                                .cinder_volume_delete_poll_interval)
            )

    def extend_volume(self, volume, new_size):
        """Extend the size of the specified volume."""
        if isinstance(new_size, dict):
            new_size = random.randint(new_size["min"], new_size["max"])

        aname = "cinder_v%s.extend_volume" % self.version
        with atomic.ActionTimer(self, aname):
            self._get_client().volumes.extend(volume, new_size)
            return self._wait_available_volume(volume)

    def list_snapshots(self, detailed=True):
        """Get a list of all snapshots."""
        aname = "cinder_v%s.list_snapshots" % self.version
        with atomic.ActionTimer(self, aname):
            return (self._get_client()
                    .volume_snapshots.list(detailed))

    def set_metadata(self, volume, sets=10, set_size=3):
        """Set volume metadata.

        :param volume: The volume to set metadata on
        :param sets: how many operations to perform
        :param set_size: number of metadata keys to set in each operation
        :returns: A list of keys that were set
        """
        key = "cinder_v%s.set_%s_metadatas_%s_times" % (self.version,
                                                        set_size,
                                                        sets)
        with atomic.ActionTimer(self, key):
            keys = []
            for i in range(sets):
                metadata = {}
                for j in range(set_size):
                    key = self.generate_random_name()
                    keys.append(key)
                    metadata[key] = self.generate_random_name()

                self._get_client().volumes.set_metadata(volume, metadata)
            return keys

    def delete_metadata(self, volume, keys, deletes=10, delete_size=3):
        """Delete volume metadata keys.

        Note that ``len(keys)`` must be greater than or equal to
        ``deletes * delete_size``.

        :param volume: The volume to delete metadata from
        :param deletes: how many operations to perform
        :param delete_size: number of metadata keys to delete in each operation
        :param keys: a list of keys to choose deletion candidates from
        """
        if len(keys) < deletes * delete_size:
            raise exceptions.InvalidArgumentsException(
                "Not enough metadata keys to delete: "
                "%(num_keys)s keys, but asked to delete %(num_deletes)s" %
                {"num_keys": len(keys),
                 "num_deletes": deletes * delete_size})
        # make a shallow copy of the list of keys so that, when we pop
        # from it later, we don't modify the original list.
        keys = list(keys)
        random.shuffle(keys)
        action_name = ("cinder_v%s.delete_%s_metadatas_%s_times"
                       % (self.version, delete_size, deletes))
        with atomic.ActionTimer(self, action_name):
            for i in range(deletes):
                to_del = keys[i * delete_size:(i + 1) * delete_size]
                self._get_client().volumes.delete_metadata(volume, to_del)

    def update_readonly_flag(self, volume, read_only):
        """Update the read-only access mode flag of the specified volume.

        :param volume: The UUID of the volume to update.
        :param read_only: The value to indicate whether to update volume to
            read-only access mode.
        :returns: A tuple of http Response and body
        """
        aname = "cinder_v%s.update_readonly_flag" % self.version
        with atomic.ActionTimer(self, aname):
            return self._get_client().volumes.update_readonly_flag(
                volume, read_only)

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
        aname = "cinder_v%s.upload_volume_to_image" % self.version
        with atomic.ActionTimer(self, aname):
            resp, img = self._get_client().volumes.upload_to_image(
                volume, force, self.generate_random_name(), container_format,
                disk_format)
            # NOTE (e0ne): upload_to_image changes volume status to uploading
            # so we need to wait until it will be available.
            volume = self._wait_available_volume(volume)

            image_id = img["os-volume_upload_image"]["image_id"]
            glance = image.Image(self._clients)

            image_inst = glance.get_image(image_id)
            image_inst = bench_utils.wait_for_status(
                image_inst,
                ready_statuses=["active"],
                update_resource=glance.get_image,
                timeout=CONF.openstack.glance_image_create_timeout,
                check_interval=(CONF.openstack
                                .glance_image_create_poll_interval)
            )

            return image_inst

    def create_qos(self, specs):
        """Create a qos specs.

        :param specs: A dict of key/value pairs to be set
        :rtype: :class:'QoSSpecs'
        """
        aname = "cinder_v%s.create_qos" % self.version
        name = self.generate_random_name()

        with atomic.ActionTimer(self, aname):
            return self._get_client().qos_specs.create(name, specs)

    def list_qos(self, search_opts=None):
        """Get a list of all qos specs.

        :param search_opts: search options
        :rtype: list of :class: 'QoSpecs'
        """
        aname = "cinder_v%s.list_qos" % self.version
        with atomic.ActionTimer(self, aname):
            return self._get_client().qos_specs.list(search_opts)

    def get_qos(self, qos_id):
        """Get a specific qos specs.

        :param qos_id: The ID of the :class: 'QoSSpecs' to get
        :rtype: :class: 'QoSSpecs'
        """
        aname = "cinder_v%s.get_qos" % self.version
        with atomic.ActionTimer(self, aname):
            return self._get_client().qos_specs.get(qos_id)

    def set_qos(self, qos_id, set_specs_args):
        """Add/Update keys in qos specs.

        :param qos_id: The ID of the :class:`QoSSpecs` to get
        :param set_specs_args: A dict of key/value pairs to be set
        :rtype: class 'cinderclient.apiclient.base.DictWithMeta'
                {"qos_specs": set_specs_args}
        """
        aname = "cinder_v%s.set_qos" % self.version
        with atomic.ActionTimer(self, aname):
            return self._get_client().qos_specs.set_keys(qos_id,
                                                         set_specs_args)

    def qos_associate_type(self, qos_specs, vol_type_id):
        """Associate qos specs from volume type.

        :param qos_specs: The qos specs to be associated with
        :param vol_type_id: The volume type id to be associated with
        :returns: base on client response return True if the request
                  has been accepted or not
        """
        aname = "cinder_v%s.qos_associate_type" % self.version
        with atomic.ActionTimer(self, aname):
            tuple_res = self._get_client().qos_specs.associate(qos_specs,
                                                               vol_type_id)
            return (tuple_res[0].status_code == 202)

    def qos_disassociate_type(self, qos_specs, vol_type_id):
        """Disassociate qos specs from volume type.

        :param qos_specs: The qos specs to be disassociated with
        :param vol_type_id: The volume type id to be disassociated with
        :returns: base on client response return True if the request
                  has been accepted or not
        """
        aname = "cinder_v%s.qos_disassociate_type" % self.version
        with atomic.ActionTimer(self, aname):
            tuple_res = self._get_client().qos_specs.disassociate(qos_specs,
                                                                  vol_type_id)
            return (tuple_res[0].status_code == 202)

    def delete_snapshot(self, snapshot):
        """Delete the given snapshot.

        Returns when the snapshot is actually deleted.

        :param snapshot: snapshot object
        """
        aname = "cinder_v%s.delete_snapshot" % self.version
        with atomic.ActionTimer(self, aname):
            self._get_client().volume_snapshots.delete(snapshot)
            bench_utils.wait_for_status(
                snapshot,
                ready_statuses=["deleted"],
                check_deletion=True,
                update_resource=self._update_resource,
                timeout=CONF.openstack.cinder_volume_delete_timeout,
                check_interval=(CONF.openstack
                                .cinder_volume_delete_poll_interval)
            )

    def delete_backup(self, backup):
        """Delete the given backup.

        Returns when the backup is actually deleted.

        :param backup: backup instance
        """
        aname = "cinder_v%s.delete_backup" % self.version
        with atomic.ActionTimer(self, aname):
            self._get_client().backups.delete(backup)
            bench_utils.wait_for_status(
                backup,
                ready_statuses=["deleted"],
                check_deletion=True,
                update_resource=self._update_resource,
                timeout=CONF.openstack.cinder_volume_delete_timeout,
                check_interval=(CONF.openstack
                                .cinder_volume_delete_poll_interval)
            )

    def restore_backup(self, backup_id, volume_id=None):
        """Restore the given backup.

        :param backup_id: The ID of the backup to restore.
        :param volume_id: The ID of the volume to restore the backup to.
        """
        aname = "cinder_v%s.restore_backup" % self.version
        with atomic.ActionTimer(self, aname):
            restore = self._get_client().restores.restore(backup_id, volume_id)
            restored_volume = self._get_client().volumes.get(restore.volume_id)
            return self._wait_available_volume(restored_volume)

    def list_backups(self, detailed=True):
        """Return user volume backups list.

        :param detailed: True if detailed information about backup
                         should be listed
        """
        aname = "cinder_v%s.list_backups" % self.version
        with atomic.ActionTimer(self, aname):
            return self._get_client().backups.list(detailed)

    def list_transfers(self, detailed=True, search_opts=None):
        """Get a list of all volume transfers.

        :param detailed: If True, detailed information about transfer
                         should be listed
        :param search_opts: Search options to filter out volume transfers
        :returns: list of :class:`VolumeTransfer`
        """
        aname = "cinder_v%s.list_transfers" % self.version
        with atomic.ActionTimer(self, aname):
            return self._get_client().transfers.list(detailed, search_opts)

    def get_volume_type(self, volume_type):
        """get details of volume_type.

        :param volume_type: The ID of the :class:`VolumeType` to get
        :returns: :class:`VolumeType`
        """
        aname = "cinder_v%s.get_volume_type" % self.version
        with atomic.ActionTimer(self, aname):
            return self._get_client().volume_types.get(volume_type)

    def delete_volume_type(self, volume_type):
        """delete a volume type.

        :param volume_type: Name or Id of the volume type
        :returns: base on client response return True if the request
                  has been accepted or not
        """
        aname = "cinder_v%s.delete_volume_type" % self.version
        with atomic.ActionTimer(self, aname):
            tuple_res = self._get_client().volume_types.delete(
                volume_type)
            return (tuple_res[0].status_code == 202)

    def set_volume_type_keys(self, volume_type, metadata):
        """Set extra specs on a volume type.

        :param volume_type: The :class:`VolumeType` to set extra spec on
        :param metadata: A dict of key/value pairs to be set
        :returns: extra_specs if the request has been accepted
        """
        aname = "cinder_v%s.set_volume_type_keys" % self.version
        with atomic.ActionTimer(self, aname):
            return volume_type.set_keys(metadata)

    def transfer_create(self, volume_id, name=None):
        """Create a volume transfer.

        :param name: The name of created transfer
        :param volume_id: The ID of the volume to transfer
        :rtype: VolumeTransfer
        """
        name = name or self.generate_random_name()
        aname = "cinder_v%s.transfer_create" % self.version
        with atomic.ActionTimer(self, aname):
            return self._get_client().transfers.create(volume_id, name=name)

    def transfer_accept(self, transfer_id, auth_key):
        """Accept a volume transfer.

        :param transfer_id: The ID of the transfer to accept.
        :param auth_key: The auth_key of the transfer.
        :rtype: VolumeTransfer
        """
        aname = "cinder_v%s.transfer_accept" % self.version
        with atomic.ActionTimer(self, aname):
            return self._get_client().transfers.accept(transfer_id, auth_key)

    def create_encryption_type(self, volume_type, specs):
        """Create encryption type for a volume type. Default: admin only.

        :param volume_type: the volume type on which to add an encryption type
        :param specs: the encryption type specifications to add
        :return: an instance of :class: VolumeEncryptionType
        """
        aname = "cinder_v%s.create_encryption_type" % self.version
        with atomic.ActionTimer(self, aname):
            return self._get_client().volume_encryption_types.create(
                volume_type, specs)

    def get_encryption_type(self, volume_type):
        """Get the volume encryption type for the specified volume type.

        :param volume_type: the volume type to query
        :return: an instance of :class: VolumeEncryptionType
        """
        aname = "cinder_v%s.get_encryption_type" % self.version
        with atomic.ActionTimer(self, aname):
            return self._get_client().volume_encryption_types.get(
                volume_type)

    def list_encryption_type(self, search_opts=None):
        """List all volume encryption types.

        :param search_opts: Options used when search for encryption types
        :return: a list of :class: VolumeEncryptionType instances
        """
        aname = "cinder_v%s.list_encryption_type" % self.version
        with atomic.ActionTimer(self, aname):
            return self._get_client().volume_encryption_types.list(
                search_opts)

    def delete_encryption_type(self, volume_type):
        """Delete the encryption type information for the specified volume type.

        :param volume_type: the volume type whose encryption type information
                            must be deleted
        """
        aname = "cinder_v%s.delete_encryption_type" % self.version
        with atomic.ActionTimer(self, aname):
            resp = self._get_client().volume_encryption_types.delete(
                volume_type)
            if (resp[0].status_code != 202):
                raise exceptions.RallyException(
                    "EncryptionType Deletion Failed")

    def update_encryption_type(self, volume_type, specs):
        """Update the encryption type information for the specified volume type.

        :param volume_type: the volume type whose encryption type information
                            must be updated
        :param specs: the encryption type specifications to update
        :return: an instance of :class: VolumeEncryptionType
        """
        aname = "cinder_v%s.update_encryption_type" % self.version
        with atomic.ActionTimer(self, aname):
            return self._get_client().volume_encryption_types.update(
                volume_type, specs)


class UnifiedCinderMixin(object):

    @staticmethod
    def _unify_backup(backup):
        return block.VolumeBackup(id=backup.id, name=backup.name,
                                  volume_id=backup.volume_id,
                                  status=backup.status)

    @staticmethod
    def _unify_transfer(transfer):
        auth_key = transfer.auth_key if hasattr(transfer, "auth_key") else None
        return block.VolumeTransfer(id=transfer.id, name=transfer.name,
                                    volume_id=transfer.volume_id,
                                    auth_key=auth_key)

    @staticmethod
    def _unify_qos(qos):
        return block.QoSSpecs(id=qos.id, name=qos.name, specs=qos.specs)

    @staticmethod
    def _unify_encryption_type(encryption_type):
        return block.VolumeEncryptionType(
            id=encryption_type.encryption_id,
            volume_type_id=encryption_type.volume_type_id)

    def delete_volume(self, volume):
        """Delete a volume."""
        self._impl.delete_volume(volume)

    def set_metadata(self, volume, sets=10, set_size=3):
        """Update/Set a volume metadata.

        :param volume: The updated/setted volume.
        :param sets: how many operations to perform
        :param set_size: number of metadata keys to set in each operation
        :returns: A list of keys that were set
        """
        return self._impl.set_metadata(volume, sets=sets, set_size=set_size)

    def delete_metadata(self, volume, keys, deletes=10, delete_size=3):
        """Delete volume metadata keys.

        Note that ``len(keys)`` must be greater than or equal to
        ``deletes * delete_size``.

        :param volume: The volume to delete metadata from
        :param deletes: how many operations to perform
        :param delete_size: number of metadata keys to delete in each operation
        :param keys: a list of keys to choose deletion candidates from
        """
        self._impl.delete_metadata(volume, keys=keys, deletes=10,
                                   delete_size=3)

    def update_readonly_flag(self, volume, read_only):
        """Update the read-only access mode flag of the specified volume.

        :param volume: The UUID of the volume to update.
        :param read_only: The value to indicate whether to update volume to
            read-only access mode.
        :returns: A tuple of http Response and body
        """
        return self._impl.update_readonly_flag(volume, read_only=read_only)

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

    def create_qos(self, specs):
        """Create a qos specs.

        :param specs: A dict of key/value pairs to be set
        :rtype: :class:'QoSSpecs'
        """
        return self._unify_qos(self._impl.create_qos(specs))

    def list_qos(self, search_opts=None):
        """Get a list of all qos specs.

        :param search_opts: search options
        :rtype: list of :class: 'QoSpecs'
        """
        return [self._unify_qos(qos)
                for qos in self._impl.list_qos(search_opts)]

    def get_qos(self, qos_id):
        """Get a specific qos specs.

        :param qos_id: The ID of the :class: 'QoSSpecs' to get
        :rtype: :class: 'QoSSpecs'
        """
        return self._unify_qos(self._impl.get_qos(qos_id))

    def set_qos(self, qos, set_specs_args):
        """Add/Update keys in qos specs.

        :param qos: The instance of the :class:`QoSSpecs` to set
        :param set_specs_args: A dict of key/value pairs to be set
        :rtype: :class: 'QoSSpecs'
        """
        self._impl.set_qos(qos.id, set_specs_args)
        return self._unify_qos(qos)

    def qos_associate_type(self, qos_specs, vol_type_id):
        """Associate qos specs from volume type.

        :param qos_specs: The qos specs to be associated with
        :param vol_type_id: The volume type id to be associated with
        """
        self._impl.qos_associate_type(qos_specs, vol_type_id)
        return self._unify_qos(qos_specs)

    def qos_disassociate_type(self, qos_specs, vol_type_id):
        """Disassociate qos specs from volume type.

        :param qos_specs: The qos specs to be disassociated with
        :param vol_type_id: The volume type id to be disassociated with
        """
        self._impl.qos_disassociate_type(qos_specs, vol_type_id)
        return self._unify_qos(qos_specs)

    def delete_snapshot(self, snapshot):
        """Delete the given backup.

        Returns when the backup is actually deleted.

        :param backup: backup instance
        """
        self._impl.delete_snapshot(snapshot)

    def delete_backup(self, backup):
        """Delete a volume backup."""
        self._impl.delete_backup(backup)

    def list_backups(self, detailed=True):
        """Return user volume backups list."""
        return [self._unify_backup(backup)
                for backup in self._impl.list_backups(detailed=detailed)]

    def list_transfers(self, detailed=True, search_opts=None):
        """Get a list of all volume transfers.

        :param detailed: If True, detailed information about transfer
                         should be listed
        :param search_opts: Search options to filter out volume transfers
        :returns: list of :class:`VolumeTransfer`
        """
        return [self._unify_transfer(transfer)
                for transfer in self._impl.list_transfers(
                    detailed=detailed, search_opts=search_opts)]

    def get_volume_type(self, volume_type):
        """get details of volume_type.

        :param volume_type: The ID of the :class:`VolumeType` to get
        :returns: :class:`VolumeType`
        """
        return self._impl.get_volume_type(volume_type)

    def delete_volume_type(self, volume_type):
        """delete a volume type.

        :param volume_type: Name or Id of the volume type
        :returns: base on client response return True if the request
                  has been accepted or not
        """
        return self._impl.delete_volume_type(volume_type)

    def set_volume_type_keys(self, volume_type, metadata):
        """Set extra specs on a volume type.

        :param volume_type: The :class:`VolumeType` to set extra spec on
        :param metadata: A dict of key/value pairs to be set
        :returns: extra_specs if the request has been accepted
        """
        return self._impl.set_volume_type_keys(volume_type, metadata)

    def transfer_create(self, volume_id, name=None):
        """Creates a volume transfer.

        :param name: The name of created transfer
        :param volume_id: The ID of the volume to transfer.
        :returns: Return the created transfer.
        """
        return self._unify_transfer(
            self._impl.transfer_create(volume_id, name=name))

    def transfer_accept(self, transfer_id, auth_key):
        """Accept a volume transfer.

        :param transfer_id: The ID of the transfer to accept.
        :param auth_key: The auth_key of the transfer.
        :returns: VolumeTransfer
        """
        return self._unify_transfer(
            self._impl.transfer_accept(transfer_id, auth_key=auth_key))

    def create_encryption_type(self, volume_type, specs):
        """Create encryption type for a volume type. Default: admin only.

        :param volume_type: the volume type on which to add an encryption type
        :param specs: the encryption type specifications to add
        :return: an instance of :class: VolumeEncryptionType
        """
        return self._unify_encryption_type(
            self._impl.create_encryption_type(volume_type, specs=specs))

    def get_encryption_type(self, volume_type):
        """Get the volume encryption type for the specified volume type.

        :param volume_type: the volume type to query
        :return: an instance of :class: VolumeEncryptionType
        """
        return self._unify_encryption_type(
            self._impl.get_encryption_type(volume_type))

    def list_encryption_type(self, search_opts=None):
        """List all volume encryption types.

        :param search_opts: Options used when search for encryption types
        :return: a list of :class: VolumeEncryptionType instances
        """
        return [self._unify_encryption_type(encryption_type)
                for encryption_type in self._impl.list_encryption_type(
                    search_opts=search_opts)]

    def delete_encryption_type(self, volume_type):
        """Delete the encryption type information for the specified volume type.

        :param volume_type: the volume type whose encryption type information
                            must be deleted
        """
        return self._impl.delete_encryption_type(volume_type)

    def update_encryption_type(self, volume_type, specs):
        """Update the encryption type information for the specified volume type.

        :param volume_type: the volume type whose encryption type information
                            must be updated
        :param specs: the encryption type specifications to update
        :return: an instance of :class: VolumeEncryptionType
        """
        return self._impl.update_encryption_type(volume_type, specs=specs)
