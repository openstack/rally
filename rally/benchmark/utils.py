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

from rally import exceptions as rally_exceptions
from rally import osclients
from rally import utils


def resource_is(status):
    return lambda resource: resource.status == status


def is_none(obj):
    return obj is None


def get_from_manager(error_statuses=None):
    error_statuses = error_statuses or ["ERROR"]

    def _get_from_manager(resource):
        try:
            resource = resource.manager.get(resource.id)
        except Exception as e:
            if getattr(e, 'http_status', 400) == 404:
                return None
            raise e
        if resource.status in error_statuses:
            raise rally_exceptions.GetResourceFailure(status=resource.status)
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


def false(resource):
    return False


def async_cleanup(cls, indicies):
    cls._cleanup_with_clients(indicies)


def format_exc(exc):
    return [str(type(exc)), str(exc), traceback.format_exc()]


def infinite_run_args(args):
    i = 0
    while True:
        yield (i,) + args
        i += 1


def create_openstack_clients(users_endpoints, keys):
    # NOTE(msdubov): Creating here separate openstack clients for each of
    #                the temporary users involved in benchmarking.
    client_managers = [osclients.Clients(*[credentials[k] for k in keys])
                       for credentials in users_endpoints]

    clients = [
        dict((
            ("nova", cl.get_nova_client()),
            ("keystone", cl.get_keystone_client()),
            ("glance", cl.get_glance_client()),
            ("cinder", cl.get_cinder_client())
        )) for cl in client_managers
    ]

    return clients
