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

import itertools
import logging
import multiprocessing
import time
import traceback

from novaclient.v1_1 import servers
from rally.benchmark.scenarios.keystone import utils as kutils
from rally import exceptions


LOG = logging.getLogger(__name__)


def resource_is(status):
    return lambda resource: resource.status.upper() == status.upper()


def get_from_manager(error_statuses=None):
    error_statuses = error_statuses or ["ERROR"]
    error_statuses = map(lambda str: str.upper(), error_statuses)

    def _get_from_manager(resource):
        # catch client side errors
        try:
            res = resource.manager.get(resource.id)
        except Exception as e:
            if getattr(e, 'code', 400) == 404:
                raise exceptions.GetResourceNotFound(resource=resource)
            raise exceptions.GetResourceFailure(resource=resource, err=e)

        # catch abnormal status, such as "no valid host" for servers
        status = res.status.upper()
        if status == "DELETED":
            raise exceptions.GetResourceNotFound(resource=res)
        if status in error_statuses:
            if isinstance(res.manager, servers.ServerManager):
                msg = res.fault['message']
            else:
                msg = ''
            raise exceptions.GetResourceErrorStatus(resource=res,
                                                    status=status, fault=msg)

        return res

    return _get_from_manager


def manager_list_size(sizes):
    def _list(mgr):
        return len(mgr.list()) in sizes
    return _list


def wait_for(resource, is_ready, update_resource=None, timeout=60,
             check_interval=1):
    """Waits for the given resource to come into the desired state.

    Uses the readiness check function passed as a parameter and (optionally)
    a function that updates the resource being waited for.

    :param is_ready: A predicate that should take the resource object and
                     return True iff it is ready to be returned
    :param update_resource: Function that should take the resource object
                          and return an 'updated' resource. If set to
                          None, no result updating is performed
    :param timeout: Timeout in seconds after which a TimeoutException will be
                    raised
    :param check_interval: Interval in seconds between the two consecutive
                           readiness checks

    :returns: The "ready" resource object
    """

    start = time.time()
    while True:
        # NOTE(boden): mitigate 1st iteration waits by updating immediately
        if update_resource:
            resource = update_resource(resource)
        if is_ready(resource):
            break
        time.sleep(check_interval)
        if time.time() - start > timeout:
            raise exceptions.TimeoutException()
    return resource


def _wait_for_list_statuses(mgr, statuses, list_query=None,
                            timeout=10, check_interval=1):
    list_query = list_query or {}

    def _list_statuses(mgr):
        for resource in mgr.list(**list_query):
            if resource.status not in statuses:
                return False
        return True

    wait_for(mgr, is_ready=_list_statuses, update_resource=None,
             timeout=timeout, check_interval=check_interval)


def _wait_for_empty_list(mgr, timeout=10, check_interval=1):
    _wait_for_list_size(mgr, sizes=[0], timeout=timeout,
                        check_interval=check_interval)


def _wait_for_list_size(mgr, sizes=[0], timeout=10, check_interval=1):
    wait_for(mgr, is_ready=manager_list_size(sizes), update_resource=None,
             timeout=timeout, check_interval=check_interval)


def wait_for_delete(resource, update_resource=None, timeout=60,
                    check_interval=1):
    """Waits for the full deletion of resource.

    :param update_resource: Function that should take the resource object
                            and return an 'updated' resource, or raise
                            exception rally.exceptions.GetResourceNotFound
                            that means that resource is deleted.

    :param timeout: Timeout in seconds after which a TimeoutException will be
                    raised
    :param check_interval: Interval in seconds between the two consecutive
                           readiness checks
    """
    start = time.time()
    while True:
        try:
            resource = update_resource(resource)
        except exceptions.GetResourceNotFound:
            break
        time.sleep(check_interval)
        if time.time() - start > timeout:
            raise exceptions.TimeoutException()


def format_exc(exc):
    return [str(type(exc)), str(exc), traceback.format_exc()]


def infinite_run_args(args):
    for i in itertools.count():
        yield (i,) + args


def run_concurrent(concurrent, fn, fn_args):
    """Run given function using pool of threads.

    :param concurrent: number of threads in the pool
    :param fn: function to be called in the pool
    :param fn_args: list of arguments for function fn() in the pool
    :returns: iterator from Pool.imap()
    """

    pool = multiprocessing.pool.ThreadPool(concurrent)
    iterator = pool.imap(fn, fn_args)
    pool.close()
    pool.join()

    return iterator


def delete_servers(nova):
    for server in nova.servers.list():
        server.delete()
    _wait_for_empty_list(nova.servers, timeout=600, check_interval=3)


def delete_keypairs(nova):
    for keypair in nova.keypairs.list():
        keypair.delete()
    _wait_for_empty_list(nova.keypairs)


def delete_images(glance, project_uuid):
    for image in glance.images.list(owner=project_uuid):
        image.delete()
    _wait_for_list_statuses(glance.images, statuses=["DELETED"],
                            list_query={'owner': project_uuid},
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


def delete_cinder_resources(cinder):
    delete_volume_transfers(cinder)
    delete_volumes(cinder)
    delete_volume_snapshots(cinder)
    delete_volume_backups(cinder)


def delete_glance_resources(glance, project_uuid):
    delete_images(glance, project_uuid)
