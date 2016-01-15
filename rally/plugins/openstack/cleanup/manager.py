# Copyright 2014: Mirantis Inc.
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

import time

from rally.common import broker
from rally.common.i18n import _
from rally.common import logging
from rally.common.plugin import discover
from rally.common import utils as rutils
from rally import osclients
from rally.plugins.openstack.cleanup import base


LOG = logging.getLogger(__name__)


class SeekAndDestroy(object):
    cache = {}

    def __init__(self, manager_cls, admin, users, api_versions=None):
        """Resource deletion class.

        This class contains method exterminate() that finds and deletes
        all resources created by Rally.

        :param manager_cls: subclass of base.ResourceManager
        :param admin: admin credential like in context["admin"]
        :param users: users credentials like in context["users"]
        :param api_versions: dict of client API versions
        """
        self.manager_cls = manager_cls
        self.admin = admin
        self.users = users or []
        self.api_versions = api_versions

    def _get_cached_client(self, user):
        """Simplifies initialization and caching OpenStack clients."""
        if not user:
            return None

        if self.api_versions:
            key = str((user["credential"], sorted(self.api_versions.items())))
        else:
            key = user["credential"]
        if key not in self.cache:
            self.cache[key] = osclients.Clients(
                user["credential"], api_info=self.api_versions)
        return self.cache[key]

    def _delete_single_resource(self, resource):
        """Safe resource deletion with retries and timeouts.

        Send request to delete resource, in case of failures repeat it few
        times. After that pull status of resource until it's deleted.

        Writes in LOG warning with UUID of resource that wasn't deleted

        :param resource: instance of resource manager initiated with resource
                         that should be deleted.
        """

        msg_kw = {
            "uuid": resource.id(),
            "name": resource.name() or "",
            "service": resource._service,
            "resource": resource._resource
        }

        LOG.debug(
            "Deleting %(service)s %(resource)s object %(name)s (%(uuid)s)" %
            msg_kw)

        try:
            rutils.retry(resource._max_attempts, resource.delete)
        except Exception as e:
            msg_kw["reason"] = e
            LOG.warning(
                _("Resource deletion failed, max retries exceeded for "
                  "%(service)s.%(resource)s: %(uuid)s. Reason: %(reason)s")
                % msg_kw)
            if logging.is_debug():
                LOG.exception(e)
        else:
            started = time.time()
            failures_count = 0
            while time.time() - started < resource._timeout:
                try:
                    if resource.is_deleted():
                        return
                except Exception as e:
                    LOG.warning(
                        _("Seems like %s.%s.is_deleted(self) method is broken "
                          "It shouldn't raise any exceptions.")
                        % (resource.__module__, type(resource).__name__))
                    LOG.exception(e)

                    # NOTE(boris-42): Avoid LOG spamming in case of bad
                    #                 is_deleted() method
                    failures_count += 1
                    if failures_count > resource._max_attempts:
                        break

                finally:
                    time.sleep(resource._interval)

            LOG.warning(_("Resource deletion failed, timeout occurred for "
                          "%(service)s.%(resource)s: %(uuid)s.")
                        % msg_kw)

    def _gen_publisher(self):
        """Returns publisher for deletion jobs.

        This method iterates over all users, lists all resources
        (using manager_cls) and puts jobs for deletion.

        Every deletion job contains tuple with two values: user and resource
        uuid that should be deleted.

        In case of tenant based resource, uuids are fetched only from one user
        per tenant.
        """

        def publisher(queue):

            def _publish(admin, user, manager):
                try:
                    for raw_resource in rutils.retry(3, manager.list):
                        queue.append((admin, user, raw_resource))
                except Exception as e:
                    LOG.warning(
                        _("Seems like %s.%s.list(self) method is broken. "
                          "It shouldn't raise any exceptions.")
                        % (manager.__module__, type(manager).__name__))
                    LOG.exception(e)

            if self.admin and (not self.users
                               or self.manager_cls._perform_for_admin_only):
                manager = self.manager_cls(
                    admin=self._get_cached_client(self.admin))
                _publish(self.admin, None, manager)

            else:
                visited_tenants = set()
                admin_client = self._get_cached_client(self.admin)
                for user in self.users:
                    if (self.manager_cls._tenant_resource
                       and user["tenant_id"] in visited_tenants):
                        continue

                    visited_tenants.add(user["tenant_id"])
                    manager = self.manager_cls(
                        admin=admin_client,
                        user=self._get_cached_client(user),
                        tenant_uuid=user["tenant_id"])

                    _publish(self.admin, user, manager)

        return publisher

    def _gen_consumer(self):
        """Generate method that consumes single deletion job."""

        def consumer(cache, args):
            """Execute deletion job."""
            admin, user, raw_resource = args

            manager = self.manager_cls(
                resource=raw_resource,
                admin=self._get_cached_client(admin),
                user=self._get_cached_client(user),
                tenant_uuid=user and user["tenant_id"])

            self._delete_single_resource(manager)

        return consumer

    def exterminate(self):
        """Delete all resources for passed users, admin and resource_mgr."""

        broker.run(self._gen_publisher(), self._gen_consumer(),
                   consumers_count=self.manager_cls._threads)


def list_resource_names(admin_required=None):
    """List all resource managers names.

    Returns all service names and all combination of service.resource names.

    :param admin_required: None -> returns all ResourceManagers
                           True -> returns only admin ResourceManagers
                           False -> returns only non admin ResourceManagers
    """
    res_mgrs = discover.itersubclasses(base.ResourceManager)
    if admin_required is not None:
        res_mgrs = filter(lambda cls: cls._admin_required == admin_required,
                          res_mgrs)

    names = set()
    for cls in res_mgrs:
        names.add(cls._service)
        names.add("%s.%s" % (cls._service, cls._resource))

    return names


def find_resource_managers(names=None, admin_required=None):
    """Returns resource managers.

    :param names: List of names in format <service> or <service>.<resource>
                  that is used for filtering resource manager classes
    :param admin_required: None -> returns all ResourceManagers
                           True -> returns only admin ResourceManagers
                           False -> returns only non admin ResourceManagers
    """
    names = set(names or [])

    resource_managers = []
    for manager in discover.itersubclasses(base.ResourceManager):
        if admin_required is not None:
            if admin_required != manager._admin_required:
                continue

        if (manager._service in names
           or "%s.%s" % (manager._service, manager._resource) in names):
            resource_managers.append(manager)

    resource_managers.sort(key=lambda x: x._order)

    found_names = set()
    for mgr in resource_managers:
        found_names.add(mgr._service)
        found_names.add("%s.%s" % (mgr._service, mgr._resource))

    missing = names - found_names
    if missing:
        LOG.warning("Missing resource managers: %s" % ", ".join(missing))

    return resource_managers


def cleanup(names=None, admin_required=None, admin=None, users=None,
            api_versions=None):
    """Generic cleaner.

    This method goes through all plugins. Filter those and left only plugins
    with _service from services or _resource from resources.

    Then goes through all passed users and using cleaners cleans all related
    resources.

    :param names: Use only resource manages that has name from this list.
                  There are in as _service or
                  (%s.%s % (_service, _resource)) from

    :param admin_required: If None -> return all plugins
                           If True -> return only admin plugins
                           If False -> return only non admin plugins
    :param admin: rally.common.objects.Credential that corresponds to OpenStack
                  admin.
    :param users: List of OpenStack users that was used during benchmarking.
                  Every user has next structure:
                  {
                    "id": <uuid1>,
                    "tenant_id": <uuid2>,
                    "credential": <rally.common.objects.Credential>

                  }
    """
    for manager in find_resource_managers(names, admin_required):
        LOG.debug("Cleaning up %(service)s %(resource)s objects" %
                  {"service": manager._service,
                   "resource": manager._resource})
        SeekAndDestroy(manager, admin, users, api_versions).exterminate()
