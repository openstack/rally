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

from neutronclient.common import exceptions as neutron_exceptions

from rally.benchmark.scenarios.keystone import utils as kutils
from rally.benchmark import utils as bench_utils
from rally.benchmark.wrappers import keystone as keystone_wrapper

LOG = logging.getLogger(__name__)


def delete_cinder_resources(cinder):
    delete_volume_transfers(cinder)
    delete_volumes(cinder)
    delete_volume_snapshots(cinder)
    delete_volume_backups(cinder)


def delete_glance_resources(glance, project_uuid):
    delete_images(glance, project_uuid)


def delete_heat_resources(heat):
    delete_stacks(heat)


def delete_admin_quotas(client, tenants):
    for tenant in tenants:
        delete_quotas(client, tenant["id"])


def delete_keystone_resources(keystone):
    keystone = keystone_wrapper.wrap(keystone)
    for resource in ["user", "project", "service", "role"]:
        _delete_single_keystone_resource_type(keystone, resource)


def _delete_single_keystone_resource_type(keystone, resource_name):
    for resource in getattr(keystone, "list_%ss" % resource_name)():
        if kutils.is_temporary(resource):
            getattr(keystone, "delete_%s" % resource_name)(resource.id)


def delete_images(glance, project_uuid):
    for image in glance.images.list(owner=project_uuid):
        image.delete()
    _wait_for_list_statuses(glance.images, statuses=["DELETED"],
                            list_query={'owner': project_uuid},
                            timeout=600, check_interval=3)


def delete_quotas(admin_clients, project_uuid):
    admin_clients.nova().quotas.delete(project_uuid)
    admin_clients.cinder().quotas.delete(project_uuid)


def delete_stacks(heat):
    for stack in heat.stacks.list():
        stack.delete()
    _wait_for_list_statuses(heat.stacks, statuses=["DELETE_COMPLETE"],
                            timeout=600, check_interval=3)


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
    delete_secgroups(nova)


def delete_secgroups(nova):
    for secgroup in nova.security_groups.list():
        if secgroup.name != "default":  # inc0: we shouldn't mess with default
            secgroup.delete()


def delete_servers(nova):
    for server in nova.servers.list():
        server.delete()
    _wait_for_empty_list(nova.servers, timeout=600, check_interval=3)


def delete_keypairs(nova):
    for keypair in nova.keypairs.list():
        keypair.delete()
    _wait_for_empty_list(nova.keypairs)


def delete_neutron_resources(neutron, project_uuid):
    search_opts = {"tenant_id": project_uuid}
    # Ports
    for port in neutron.list_ports(**search_opts)["ports"]:
        # Detach routers
        if port["device_owner"] == "network:router_interface":
            neutron.remove_interface_router(
                port["device_id"], {
                    "port_id": port["id"]
                })
        else:
            try:
                neutron.delete_port(port["id"])
            except neutron_exceptions.PortNotFoundClient:
                # Port can be already auto-deleted, skip silently
                pass
    # Routers
    for router in neutron.list_routers(**search_opts)["routers"]:
        neutron.delete_router(router["id"])

    # Subnets
    for subnet in neutron.list_subnets(**search_opts)["subnets"]:
        neutron.delete_subnet(subnet["id"])

    # Networks
    for network in neutron.list_networks(**search_opts)["networks"]:
        neutron.delete_network(network["id"])


def delete_ceilometer_resources(ceilometer, project_uuid):
    delete_alarms(ceilometer, project_uuid)


def delete_alarms(ceilometer, project_uuid):
    alarms = ceilometer.alarms.list(q=[{"field": "project_id",
                                        "op": "eq",
                                        "value": project_uuid}])
    for alarm in alarms:
        ceilometer.alarms.delete(alarm.alarm_id)


def delete_sahara_resources(sahara):
    # Delete EDP related objects
    delete_job_executions(sahara)
    delete_jobs(sahara)
    delete_job_binaries(sahara)
    delete_data_sources(sahara)

    # Delete cluster related objects
    delete_clusters(sahara)
    delete_cluster_templates(sahara)
    delete_node_group_templates(sahara)


def delete_job_executions(sahara):
    for je in sahara.job_executions.list():
        sahara.job_executions.delete(je.id)

    _wait_for_empty_list(sahara.job_executions)


def delete_jobs(sahara):
    for job in sahara.jobs.list():
        sahara.jobs.delete(job.id)


def delete_job_binaries(sahara):
    for jb in sahara.job_binaries.list():
        sahara.job_binaries.delete(jb.id)


def delete_data_sources(sahara):
    for ds in sahara.data_sources.list():
        sahara.data_sources.delete(ds.id)


def delete_clusters(sahara):
    for cluster in sahara.clusters.list():
        sahara.clusters.delete(cluster.id)

    _wait_for_empty_list(sahara.clusters)


def delete_cluster_templates(sahara):
    for ct in sahara.cluster_templates.list():
        sahara.cluster_templates.delete(ct.id)


def delete_node_group_templates(sahara):
    for ngt in sahara.node_group_templates.list():
        sahara.node_group_templates.delete(ngt.id)


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
            status = bench_utils.get_status(resource)
            if status not in statuses:
                return False
        return True

    bench_utils.wait_for(mgr, is_ready=_list_statuses, update_resource=None,
                         timeout=timeout, check_interval=check_interval)
