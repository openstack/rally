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

import traceback

from novaclient import exceptions as nova_exceptions

from rally.benchmark.scenarios.keystone import utils as kutils
from rally import exceptions as rally_exceptions
from rally import osclients
from rally import utils


def resource_is(status):
    return lambda resource: resource.status.upper() == status.upper()


def get_from_manager(error_statuses=None):
    error_statuses = error_statuses or ["ERROR"]
    error_statuses = map(lambda str: str.upper(), error_statuses)

    def _get_from_manager(resource):
        try:
            resource = resource.manager.get(resource.id)
        except Exception as e:
            if getattr(e, 'code', 400) == 404:
                raise rally_exceptions.GetResourceNotFound(status="404")
            raise rally_exceptions.GetResourceFailure(status=e)
        status = resource.status.upper()
        if status == "DELETED":
            raise rally_exceptions.GetResourceNotFound(status="404")
        if status in error_statuses:
            raise rally_exceptions.GetResourceErrorStatus(status=status)
        return resource

    return _get_from_manager


def manager_list_size(sizes):
    def _list(mgr):
        return len(mgr.list()) in sizes
    return _list


def _wait_for_list_statuses(mgr, statuses, list_query=None,
                            timeout=10, check_interval=1):
    list_query = list_query or {}

    def _list_statuses(mgr):
        for resource in mgr.list(**list_query):
            if resource.status not in statuses:
                return False
        return True

    utils.wait_for(mgr, is_ready=_list_statuses, update_resource=None,
                   timeout=timeout, check_interval=check_interval)


def _wait_for_empty_list(mgr, timeout=10, check_interval=1):
    _wait_for_list_size(mgr, sizes=[0], timeout=timeout,
                        check_interval=check_interval)


def _wait_for_list_size(mgr, sizes=[0], timeout=10, check_interval=1):
    utils.wait_for(mgr, is_ready=manager_list_size(sizes),
                   update_resource=None, timeout=timeout,
                   check_interval=check_interval)


def format_exc(exc):
    return [str(type(exc)), str(exc), traceback.format_exc()]


def infinite_run_args(args):
    i = 0
    while True:
        yield (i,) + args
        i += 1


def create_openstack_clients(endpoint):
    client_manager = osclients.Clients(endpoint)

    clients = {
        "nova": client_manager.get_nova_client(),
        "keystone": client_manager.get_keystone_client(),
        "glance": client_manager.get_glance_client(),
        "cinder": client_manager.get_cinder_client(),
        "endpoint": client_manager.endpoint,
        # NOTE(boris-42): seems like it should be refactored
        "ssh_key_pair": getattr(endpoint, "keypair", {})
    }

    return clients


def _prepare_for_instance_ssh(users_endpoint):
    """Generate and store SSH keys, allow access to port 22.

    In order to run tests on instances it is necessary to have SSH access.
    This function generates an SSH key pair per user which is stored in the
    clients dictionary. The public key is also submitted to nova via the
    novaclient.

    A security group rule is created to allow access to instances on port 22.
    """
    nova_client = create_openstack_clients(users_endpoint)['nova']

    # NOTE(boris-42): private key is used in
    #                 NovaServers.boot_runcommand_delete_server
    #                 So seems like potential bu in case of adding support of
    #                 precreated users
    keypair = None
    if 'rally_ssh_key' not in [k.name for k in nova_client.keypairs.list()]:
        keypair = nova_client.keypairs.create('rally_ssh_key')

    if 'rally_open' not in [sg.name for sg in
                            nova_client.security_groups.list()]:
        rally_open = nova_client.security_groups.create(
            'rally_open', 'Allow all access to VMs for benchmarking')

    rally_open = nova_client.security_groups.find(name='rally_open')

    rules_to_add = [
        {
            "ip_protocol": "tcp",
            "to_port": 65535,
            "from_port": 1,
            "ip_range": {"cidr": "0.0.0.0/0"}
        },
        {
            "ip_protocol": "udp",
            "to_port": 65535,
            "from_port": 1,
            "ip_range": {"cidr": "0.0.0.0/0"}
        },
        {
            "ip_protocol": "icmp",
            "to_port": 1,
            "from_port": -1,
            "ip_range": {"cidr": "0.0.0.0/0"}
        }
    ]

    def rule_match(criteria, existing_rule):
        return all(existing_rule[key] == value
                   for key, value in criteria.iteritems())

    for new_rule in rules_to_add:
        if not any(rule_match(new_rule, existing_rule) for existing_rule
                   in rally_open.rules):
            nova_client.security_group_rules.create(
                        rally_open.id,
                        from_port=new_rule['from_port'],
                        to_port=new_rule['to_port'],
                        ip_protocol=new_rule['ip_protocol'],
                        cidr=new_rule['ip_range']['cidr'])

    return ({"private": keypair.private_key, "public": keypair.public_key}
            if keypair else None)


def delete_servers(nova):
    for server in nova.servers.list():
        server.delete()
    _wait_for_empty_list(nova.servers, timeout=600, check_interval=3)


def delete_keypairs(nova):
    for keypair in nova.keypairs.list():
        keypair.delete()
    _wait_for_empty_list(nova.keypairs)


def delete_security_groups(nova):
    for group in nova.security_groups.list():
        try:
            group.delete()
        except nova_exceptions.BadRequest as br:
            #TODO(boden): find a way to determine default security group
            if not br.message.startswith('Unable to delete system group'):
                raise br
    _wait_for_list_size(nova.security_groups, sizes=[0, 1])


def delete_images(glance, project_uuid):
    for image in glance.images.list(owner=project_uuid):
        image.delete()
    _wait_for_list_statuses(glance.images, statuses=["DELETED"],
                            list_query={'owner': project_uuid},
                            timeout=600, check_interval=3)


def delete_networks(nova):
    for network in nova.networks.list():
        network.delete()
    _wait_for_empty_list(nova.networks)


def delete_volumes(cinder):
    for vol in cinder.volumes.list():
        vol.delete()
    _wait_for_empty_list(cinder.volumes, timeout=120)


def delete_volume_types(cinder):
    for vol_type in cinder.volume_types.list():
        vol_type.delete()
    _wait_for_empty_list(cinder.volume_types)


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


def delete_keystone_resources(keystone):
    for resource in ["users", "tenants", "services", "roles"]:
        _delete_single_keystone_resource_type(keystone, resource)


def _delete_single_keystone_resource_type(keystone, resource_name):
    for resource in getattr(keystone, resource_name).list():
        if kutils.is_temporary(resource):
            resource.delete()


def delete_nova_resources(nova):
    delete_servers(nova)
    delete_keypairs(nova)
    delete_security_groups(nova)
    delete_networks(nova)


def delete_cinder_resources(cinder):
    delete_volume_transfers(cinder)
    delete_volumes(cinder)
    delete_volume_types(cinder)
    delete_volume_snapshots(cinder)
    delete_volume_backups(cinder)


def delete_glance_resources(glance, project_uuid):
    delete_images(glance, project_uuid)
