# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 IBM Corp.
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

from novaclient import exceptions as nova_exceptions
import utils


def _delete_servers(nova):
    for server in nova.servers.list():
        server.delete()
    utils._wait_for_empty_list(nova.servers, timeout=600, check_interval=3)


def _delete_keypairs(nova):
    for keypair in nova.keypairs.list():
        keypair.delete()
    utils._wait_for_empty_list(nova.keypairs)


def _delete_security_groups(nova):
    for group in nova.security_groups.list():
        try:
            group.delete()
        except nova_exceptions.BadRequest as br:
            #TODO(boden): find a way to determine default security group
            if not br.message.startswith('Unable to delete system group'):
                raise br
    utils._wait_for_list_size(nova.security_groups, sizes=[0, 1])


def _delete_images(glance, project_uuid):
    for image in glance.images.list(owner=project_uuid):
        image.delete()
    utils._wait_for_list_statuses(glance.images, statuses=["DELETED"],
                                  list_query={'owner': project_uuid},
                                  timeout=600, check_interval=3)


def _delete_networks(nova):
    for network in nova.networks.list():
        network.delete()
    utils._wait_for_empty_list(nova.networks)


def _delete_volumes(cinder):
    for vol in cinder.volumes.list():
        vol.delete()
    utils._wait_for_empty_list(cinder.volumes, timeout=120)


def _delete_volume_types(cinder):
    for vol_type in cinder.volume_types.list():
        cinder.volume_types.delete(vol_type.id)
    utils._wait_for_empty_list(cinder.volume_types)


def _delete_volume_transfers(cinder):
    for transfer in cinder.transfers.list():
        transfer.delete()
    utils._wait_for_empty_list(cinder.transfers)


def _delete_volume_snapshots(cinder):
    for snapshot in cinder.volume_snapshots.list():
        snapshot.delete()
    utils._wait_for_empty_list(cinder.volume_snapshots, timeout=240)


def _delete_volume_backups(cinder):
    for backup in cinder.backups.list():
        backup.delete()
    utils._wait_for_empty_list(cinder.backups, timeout=240)
