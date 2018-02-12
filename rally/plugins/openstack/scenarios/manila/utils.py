# Copyright 2015 Mirantis Inc.
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

from rally.common import cfg
from rally import exceptions
from rally.plugins.openstack.context.manila import consts
from rally.plugins.openstack import scenario
from rally.task import atomic
from rally.task import utils


CONF = cfg.CONF


class ManilaScenario(scenario.OpenStackScenario):
    """Base class for Manila scenarios with basic atomic actions."""

    @atomic.action_timer("manila.create_share")
    def _create_share(self, share_proto, size=1, **kwargs):
        """Create a share.

        :param share_proto: share protocol for new share,
            available values are NFS, CIFS, GlusterFS, HDFS and CEPHFS.
        :param size: size of a share in GB
        :param snapshot_id: ID of the snapshot
        :param name: name of new share
        :param description: description of a share
        :param metadata: optional metadata to set on share creation
        :param share_network: either instance of ShareNetwork or str with ID
        :param share_type: either instance of ShareType or str with ID
        :param is_public: defines whether to set share as public or not.
        :returns: instance of :class:`Share`
        """
        if self.context:
            share_networks = self.context.get("tenant", {}).get(
                consts.SHARE_NETWORKS_CONTEXT_NAME, {}).get(
                    "share_networks", [])
            if share_networks and not kwargs.get("share_network"):
                kwargs["share_network"] = share_networks[
                    self.context["iteration"] % len(share_networks)]["id"]

        if not kwargs.get("name"):
            kwargs["name"] = self.generate_random_name()

        share = self.clients("manila").shares.create(
            share_proto, size, **kwargs)

        self.sleep_between(CONF.openstack.manila_share_create_prepoll_delay)
        share = utils.wait_for_status(
            share,
            ready_statuses=["available"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.openstack.manila_share_create_timeout,
            check_interval=CONF.openstack.manila_share_create_poll_interval,
        )
        return share

    @atomic.action_timer("manila.delete_share")
    def _delete_share(self, share):
        """Delete the given share.

        :param share: :class:`Share`
        """
        share.delete()
        error_statuses = ("error_deleting", )
        utils.wait_for_status(
            share,
            ready_statuses=["deleted"],
            check_deletion=True,
            update_resource=utils.get_from_manager(error_statuses),
            timeout=CONF.openstack.manila_share_delete_timeout,
            check_interval=CONF.openstack.manila_share_delete_poll_interval)

    def _get_access_from_share(self, share, access_id):
        """Get access from share

        :param share: :class: `Share`
        :param access_id: The id of the access we want to get
        :returns: The access object from the share
        :raises GetResourceNotFound: if the access is not in the share
        """
        try:
            return next(access for access in share.access_list()
                        if access.id == access_id)
        except StopIteration:
            raise exceptions.GetResourceNotFound(resource=access_id)

    def _update_resource_in_allow_access_share(self, share, access_id):
        """Helper to update resource state in allow_access_share method

        :param share: :class:`Share`
        :param access_id: id of the access
        :returns: A function to be used in wait_for_status for the update
            resource
        """
        def _is_created(_):
            return self._get_access_from_share(share, access_id)

        return _is_created

    @atomic.action_timer("manila.access_allow_share")
    def _allow_access_share(self, share, access_type, access, access_level):
        """Allow access to a share

        :param share: :class:`Share`
        :param access_type: represents the access type (e.g: 'ip', 'domain'...)
        :param access: represents the object (e.g: '127.0.0.1'...)
        :param access_level: access level to the share (e.g: 'rw', 'ro')
        """
        access_result = share.allow(access_type, access, access_level)
        # Get access from the list of accesses of the share
        access = next(access for access in share.access_list()
                      if access.id == access_result["id"])

        fn = self._update_resource_in_allow_access_share(share,
                                                         access_result["id"])

        # We check if the access in that access_list has the active state
        utils.wait_for_status(
            access,
            ready_statuses=["active"],
            update_resource=fn,
            check_interval=CONF.openstack.manila_access_create_poll_interval,
            timeout=CONF.openstack.manila_access_create_timeout)

        return access_result

    def _update_resource_in_deny_access_share(self, share, access_id):
        """Helper to update resource state in deny_access_share method

        :param share: :class:`Share`
        :param access_id: id of the access
        :returns: A function to be used in wait_for_status for the update
            resource
        """
        def _is_deleted(_):
            access = self._get_access_from_share(share, access_id)
            return access

        return _is_deleted

    @atomic.action_timer("manila.access_deny_share")
    def _deny_access_share(self, share, access_id):
        """Deny access to a share

        :param share: :class:`Share`
        :param access_id: id of the access to delete
        """
        # Get the access element that was created in the first place
        access = self._get_access_from_share(share, access_id)
        share.deny(access_id)

        fn = self._update_resource_in_deny_access_share(share,
                                                        access_id)

        utils.wait_for_status(
            access,
            ready_statuses=["deleted"],
            update_resource=fn,
            check_deletion=True,
            check_interval=CONF.openstack.manila_access_delete_poll_interval,
            timeout=CONF.openstack.manila_access_delete_timeout)

    @atomic.action_timer("manila.list_shares")
    def _list_shares(self, detailed=True, search_opts=None):
        """Returns user shares list.

        :param detailed: defines either to return detailed list of
            objects or not.
        :param search_opts: container of search opts such as
            "name", "host", "share_type", etc.
        """
        return self.clients("manila").shares.list(
            detailed=detailed, search_opts=search_opts)

    @atomic.action_timer("manila.extend_share")
    def _extend_share(self, share, new_size):
        """Extend the given share

        :param share: :class:`Share`
        :param new_size: new size of the share
        """
        share.extend(new_size)
        utils.wait_for_status(
            share,
            ready_statuses=["available"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.openstack.manila_share_create_timeout,
            check_interval=CONF.openstack.manila_share_create_poll_interval)

    @atomic.action_timer("manila.shrink_share")
    def _shrink_share(self, share, new_size):
        """Shrink the given share

        :param share: :class:`Share`
        :param new_size: new size of the share
        """
        share.shrink(new_size)
        utils.wait_for_status(
            share,
            ready_statuses=["available"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.openstack.manila_share_create_timeout,
            check_interval=CONF.openstack.manila_share_create_poll_interval)

    @atomic.action_timer("manila.create_share_network")
    def _create_share_network(self, neutron_net_id=None,
                              neutron_subnet_id=None,
                              nova_net_id=None, description=None):
        """Create share network.

        :param neutron_net_id: ID of Neutron network
        :param neutron_subnet_id: ID of Neutron subnet
        :param nova_net_id: ID of Nova network
        :param description: share network description
        :returns: instance of :class:`ShareNetwork`
        """
        share_network = self.clients("manila").share_networks.create(
            neutron_net_id=neutron_net_id,
            neutron_subnet_id=neutron_subnet_id,
            nova_net_id=nova_net_id,
            name=self.generate_random_name(),
            description=description)
        return share_network

    @atomic.action_timer("manila.delete_share_network")
    def _delete_share_network(self, share_network):
        """Delete share network.

        :param share_network: instance of :class:`ShareNetwork`.
        """
        share_network.delete()
        utils.wait_for_status(
            share_network,
            ready_statuses=["deleted"],
            check_deletion=True,
            update_resource=utils.get_from_manager(),
            timeout=CONF.openstack.manila_share_delete_timeout,
            check_interval=CONF.openstack.manila_share_delete_poll_interval)

    @atomic.action_timer("manila.list_share_networks")
    def _list_share_networks(self, detailed=True, search_opts=None):
        """List share networks.

        :param detailed: defines either to return detailed list of
            objects or not.
        :param search_opts: container of search opts such as
            "project_id" and "name".
        :returns: list of instances of :class:`ShareNetwork`
        """
        share_networks = self.clients("manila").share_networks.list(
            detailed=detailed, search_opts=search_opts)
        return share_networks

    @atomic.action_timer("manila.list_share_servers")
    def _list_share_servers(self, search_opts=None):
        """List share servers. Admin only.

        :param search_opts: set of key-value pairs to filter share servers by.
            Example: {"share_network": "share_network_name_or_id"}
        :returns: list of instances of :class:`ShareServer`
        """
        share_servers = self.admin_clients("manila").share_servers.list(
            search_opts=search_opts)
        return share_servers

    @atomic.action_timer("manila.create_security_service")
    def _create_security_service(self, security_service_type, dns_ip=None,
                                 server=None, domain=None, user=None,
                                 password=None, description=None):
        """Create security service.

        'Security service' is data container in Manila that stores info
        about auth services 'Active Directory', 'Kerberos' and catalog
        service 'LDAP' that should be used for shares.

        :param security_service_type: security service type, permitted values
            are 'ldap', 'kerberos' or 'active_directory'.
        :param dns_ip: dns ip address used inside tenant's network
        :param server: security service server ip address or hostname
        :param domain: security service domain
        :param user: security identifier used by tenant
        :param password: password used by user
        :param description: security service description
        :returns: instance of :class:`SecurityService`
        """
        security_service = self.clients("manila").security_services.create(
            type=security_service_type,
            dns_ip=dns_ip,
            server=server,
            domain=domain,
            user=user,
            password=password,
            name=self.generate_random_name(),
            description=description)
        return security_service

    @atomic.action_timer("manila.delete_security_service")
    def _delete_security_service(self, security_service):
        """Delete security service.

        :param security_service: instance of :class:`SecurityService`.
        """
        security_service.delete()
        utils.wait_for_status(
            security_service,
            ready_statuses=["deleted"],
            check_deletion=True,
            update_resource=utils.get_from_manager(),
            timeout=CONF.openstack.manila_share_delete_timeout,
            check_interval=CONF.openstack.manila_share_delete_poll_interval)

    @atomic.action_timer("manila.add_security_service_to_share_network")
    def _add_security_service_to_share_network(self, share_network,
                                               security_service):
        """Associate given security service with a share network.

        :param share_network: ID or instance of :class:`ShareNetwork`.
        :param security_service: ID or instance of :class:`SecurityService`.
        :returns: instance of :class:`ShareNetwork`.
        """
        share_network = self.clients(
            "manila").share_networks.add_security_service(
                share_network, security_service)
        return share_network

    @atomic.action_timer("manila.set_metadata")
    def _set_metadata(self, share, sets=1, set_size=1,
                      key_min_length=1, key_max_length=256,
                      value_min_length=1, value_max_length=1024):
        """Sets share metadata.

        :param share: the share to set metadata on
        :param sets: how many operations to perform
        :param set_size: number of metadata keys to set in each operation
        :param key_min_length: minimal size of metadata key to set
        :param key_max_length: maximum size of metadata key to set
        :param value_min_length: minimal size of metadata value to set
        :param value_max_length: maximum size of metadata value to set
        :returns: A list of keys that were set
        :raises exceptions.InvalidArgumentsException: if invalid arguments
            were provided.
        """
        if not (key_min_length <= key_max_length and
                value_min_length <= value_max_length):
            raise exceptions.InvalidArgumentsException(
                "Min length for keys and values of metadata can not be bigger "
                "than maximum length.")

        keys = []
        for i in range(sets):
            metadata = {}
            for j in range(set_size):
                if key_min_length == key_max_length:
                    key_length = key_min_length
                else:
                    key_length = random.choice(
                        range(key_min_length, key_max_length))
                if value_min_length == value_max_length:
                    value_length = value_min_length
                else:
                    value_length = random.choice(
                        range(value_min_length, value_max_length))
                key = self._generate_random_part(length=key_length)
                keys.append(key)
                metadata[key] = self._generate_random_part(length=value_length)
            self.clients("manila").shares.set_metadata(share["id"], metadata)

        return keys

    @atomic.action_timer("manila.delete_metadata")
    def _delete_metadata(self, share, keys, delete_size=3):
        """Deletes share metadata.

        :param share: The share to delete metadata from.
        :param delete_size: number of metadata keys to delete using one single
            call.
        :param keys: a list or tuple of keys to choose deletion candidates from
        :raises exceptions.InvalidArgumentsException: if invalid arguments
            were provided.
        """
        if not (isinstance(keys, list) and keys):
            raise exceptions.InvalidArgumentsException(
                "Param 'keys' should be non-empty 'list'. keys = '%s'" % keys)
        for i in range(0, len(keys), delete_size):
            self.clients("manila").shares.delete_metadata(
                share["id"], keys[i:i + delete_size])
