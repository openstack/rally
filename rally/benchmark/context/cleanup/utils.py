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

import logging

from rally.benchmark.scenarios.keystone import utils as kutils
from rally.benchmark import utils as bench_utils

LOG = logging.getLogger(__name__)


def delete_cinder_resources(cinder):
    delete_volume_transfers(cinder)
    delete_volumes(cinder)
    delete_volume_snapshots(cinder)
    delete_volume_backups(cinder)


def delete_glance_resources(glance, project_uuid):
    delete_images(glance, project_uuid)


def delete_keystone_resources(keystone):
    for resource in ["users", "tenants", "services", "roles"]:
        _delete_single_keystone_resource_type(keystone, resource)


def _delete_single_keystone_resource_type(keystone, resource_name):
    for resource in getattr(keystone, resource_name).list():
        if kutils.is_temporary(resource):
            resource.delete()


def delete_images(glance, project_uuid):
    for image in glance.images.list(owner=project_uuid):
        image.delete()
    _wait_for_list_statuses(glance.images, statuses=["DELETED"],
                            list_query={'owner': project_uuid},
                            timeout=600, check_interval=3)


def delete_quotas(admin_clients, project_uuid):
    # TODO(yingjun): We need to add the cinder part for deleting
    #                quotas when the new cinderclient released.
    admin_clients.nova().quotas.delete(project_uuid)


def delete_volumes(cinder):
    for vol in cinder.volumes.list():
        vol.delete()
    _wait_for_empty_list(cinder.volumes, timeout=120)


def delete_volume_transfers(cinder):
    for transfer in cinder.transfers.list():
        transfer.delete()
    _wait_for_empty_list(cinder.transfers)


def delete_volume_snapshots(cinder):
    for snapshot in cinder.volume_snapshots.list():
        snapshot.delete()
    _wait_for_empty_list(cinder.volume_snapshots, timeout=240)


def delete_volume_backups(cinder):
    for backup in cinder.backups.list():
        backup.delete()
    _wait_for_empty_list(cinder.backups, timeout=240)


def delete_nova_resources(nova):
    delete_servers(nova)
    delete_keypairs(nova)


def delete_servers(nova):
    for server in nova.servers.list():
        server.delete()
    _wait_for_empty_list(nova.servers, timeout=600, check_interval=3)


def delete_keypairs(nova):
    for keypair in nova.keypairs.list():
        keypair.delete()
    _wait_for_empty_list(nova.keypairs)


def delete_neutron_networks(neutron, project_uuid):
    for network in neutron.list_networks()['networks']:
        if network['tenant_id'] == project_uuid:
            neutron.delete_network(network['id'])


def delete_neutron_resources(neutron, project_uuid):
    delete_neutron_networks(neutron, project_uuid)


def _wait_for_empty_list(mgr, timeout=10, check_interval=1):
    _wait_for_list_size(mgr, sizes=[0], timeout=timeout,
                        check_interval=check_interval)


def _wait_for_list_size(mgr, sizes=[0], timeout=10, check_interval=1):
    bench_utils.wait_for(mgr, is_ready=bench_utils.manager_list_size(sizes),
                         update_resource=None, timeout=timeout,
                         check_interval=check_interval)


def _wait_for_list_statuses(mgr, statuses, list_query=None,
                            timeout=10, check_interval=1):
    list_query = list_query or {}

    def _list_statuses(mgr):
        for resource in mgr.list(**list_query):
            if resource.status not in statuses:
                return False
        return True

    bench_utils.wait_for(mgr, is_ready=_list_statuses, update_resource=None,
                         timeout=timeout, check_interval=check_interval)
