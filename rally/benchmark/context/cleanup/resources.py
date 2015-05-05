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

from boto import exception as boto_exception
from neutronclient.common import exceptions as neutron_exceptions
from saharaclient.api import base as saharaclient_base

from rally.benchmark.context.cleanup import base
from rally.benchmark.scenarios.keystone import utils as kutils
from rally.benchmark.wrappers import keystone as keystone_wrapper
from rally.common import log as logging


LOG = logging.getLogger(__name__)


def get_order(start):
    return iter(range(start, start + 99))


class SynchronizedDeletion(object):

    def is_deleted(self):
        return True


class QuotaMixin(SynchronizedDeletion):

    def id(self):
        return self.raw_resource

    def delete(self):
        self._manager().delete(self.raw_resource)

    def list(self):
        return [self.tenant_uuid] if self.tenant_uuid else []


# HEAT

@base.resource("heat", "stacks", order=100)
class HeatStack(base.ResourceManager):
    pass


# NOVA

_nova_order = get_order(200)


@base.resource("nova", "servers", order=next(_nova_order))
class NovaServer(base.ResourceManager):
    pass


@base.resource("nova", "keypairs", order=next(_nova_order))
class NovaKeypair(SynchronizedDeletion, base.ResourceManager):
    pass


@base.resource("nova", "security_groups", order=next(_nova_order))
class NovaSecurityGroup(SynchronizedDeletion, base.ResourceManager):

    def list(self):
        return filter(lambda x: x.name != "default",
                      super(NovaSecurityGroup, self).list())


@base.resource("nova", "quotas", order=next(_nova_order),
               admin_required=True, tenant_resource=True)
class NovaQuotas(QuotaMixin, base.ResourceManager):
    pass


@base.resource("nova", "floating_ips_bulk", order=next(_nova_order),
               admin_required=True)
class NovaFloatingIpsBulk(SynchronizedDeletion, base.ResourceManager):

    def id(self):
        return self.raw_resource.address

    def list(self):
        return [floating_ip for floating_ip in self._manager().list()
                if floating_ip.pool.startswith("rally_fip_pool_")]


# EC2

_ec2_order = get_order(250)


class EC2Mixin(object):

    def _manager(self):
        return getattr(self.user, self._service)()


@base.resource("ec2", "servers", order=next(_ec2_order))
class EC2Server(EC2Mixin, base.ResourceManager):

    def is_deleted(self):
        try:
            instances = self._manager().get_only_instances(
                instance_ids=[self.id()])
        except boto_exception.EC2ResponseError as e:
            # NOTE(wtakase): Nova EC2 API returns 'InvalidInstanceID.NotFound'
            #                if instance not found. In this case, we consider
            #                instance has already been deleted.
            return getattr(e, "error_code") == "InvalidInstanceID.NotFound"

        # NOTE(wtakase): After instance deletion, instance can be 'terminated'
        #                state. If all instance states are 'terminated', this
        #                returns True. And if get_only_instaces() returns empty
        #                list, this also returns True because we consider
        #                instance has already been deleted.
        return all(map(lambda i: i.state == "terminated", instances))

    def delete(self):
        self._manager().terminate_instances(instance_ids=[self.id()])

    def list(self):
        return self._manager().get_only_instances()


# NEUTRON

_neutron_order = get_order(300)


@base.resource(service=None, resource=None, admin_required=True)
class NeutronMixin(SynchronizedDeletion, base.ResourceManager):
    # Neutron has the best client ever, so we need to override everything

    def _manager(self):
        client = self._admin_required and self.admin or self.user
        return getattr(client, self._service)()

    def id(self):
        return self.raw_resource["id"]

    def delete(self):
        delete_method = getattr(self._manager(), "delete_%s" % self._resource)
        delete_method(self.id())

    def list(self):
        resources = self._resource + "s"
        list_method = getattr(self._manager(), "list_%s" % resources)

        return filter(lambda r: r["tenant_id"] == self.tenant_uuid,
                      list_method({"tenant_id": self.tenant_uuid})[resources])


@base.resource("neutron", "port", order=next(_neutron_order),
               tenant_resource=True)
class NeutronPort(NeutronMixin):

    def delete(self):
        if self.raw_resource["device_owner"] == "network:router_interface":
            self._manager().remove_interface_router(
                self.raw_resource["device_id"],
                {"port_id": self.raw_resource["id"]})
        else:
            try:
                self._manager().delete_port(self.id())
            except neutron_exceptions.PortNotFoundClient:
                # Port can be already auto-deleted, skip silently
                LOG.debug("Port %s was not deleted. Skip silently because "
                          "port can be already auto-deleted."
                          % self.id())


@base.resource("neutron", "router", order=next(_neutron_order),
               tenant_resource=True)
class NeutronRouter(NeutronMixin):
    pass


@base.resource("neutron", "subnet", order=next(_neutron_order),
               tenant_resource=True)
class NeutronSubnet(NeutronMixin):
    pass


@base.resource("neutron", "network", order=next(_neutron_order),
               tenant_resource=True)
class NeutronNetwork(NeutronMixin):
    pass


@base.resource("neutron", "quota", order=next(_neutron_order),
               admin_required=True, tenant_resource=True)
class NeutronQuota(QuotaMixin, NeutronMixin):

    def delete(self):
        self._manager().delete_quota(self.tenant_uuid)


# CINDER

_cinder_order = get_order(400)


@base.resource("cinder", "backups", order=next(_cinder_order),
               tenant_resource=True)
class CinderVolumeBackup(base.ResourceManager):
    pass


@base.resource("cinder", "volume_snapshots", order=next(_cinder_order),
               tenant_resource=True)
class CinderVolumeSnapshot(base.ResourceManager):
    pass


@base.resource("cinder", "transfers", order=next(_cinder_order),
               tenant_resource=True)
class CinderVolumeTransfer(base.ResourceManager):
    pass


@base.resource("cinder", "volumes", order=next(_cinder_order),
               tenant_resource=True)
class CinderVolume(base.ResourceManager):
    pass


@base.resource("cinder", "quotas", order=next(_cinder_order),
               admin_required=True, tenant_resource=True)
class CinderQuotas(QuotaMixin, base.ResourceManager):
    pass


# GLANCE

@base.resource("glance", "images", order=500, tenant_resource=True)
class GlanceImage(base.ResourceManager):

    def list(self):
        return self._manager().list(owner=self.tenant_uuid)


# SAHARA

_sahara_order = get_order(600)


@base.resource("sahara", "job_executions", order=next(_sahara_order),
               tenant_resource=True)
class SaharaJobExecution(SynchronizedDeletion, base.ResourceManager):
    pass


@base.resource("sahara", "jobs", order=next(_sahara_order),
               tenant_resource=True)
class SaharaJob(SynchronizedDeletion, base.ResourceManager):
    pass


@base.resource("sahara", "job_binary_internals", order=next(_sahara_order),
               tenant_resource=True)
class SaharaJobBinaryInternals(SynchronizedDeletion, base.ResourceManager):
    pass


@base.resource("sahara", "job_binaries", order=next(_sahara_order),
               tenant_resource=True)
class SaharaJobBinary(SynchronizedDeletion, base.ResourceManager):
    pass


@base.resource("sahara", "data_sources", order=next(_sahara_order),
               tenant_resource=True)
class SaharaDataSource(SynchronizedDeletion, base.ResourceManager):
    pass


@base.resource("sahara", "clusters", order=next(_sahara_order),
               tenant_resource=True)
class SaharaCluster(base.ResourceManager):

    # Need special treatment for Sahara Cluster because of the way the
    # exceptions are described in:
    # https://github.com/openstack/python-saharaclient/blob/master/
    # saharaclient/api/base.py#L145

    def is_deleted(self):
        try:
            self._manager().get(self.id())
            return False
        except saharaclient_base.APIException as e:
            return e.error_code == 404


@base.resource("sahara", "cluster_templates", order=next(_sahara_order),
               tenant_resource=True)
class SaharaClusterTemplate(SynchronizedDeletion, base.ResourceManager):
    pass


@base.resource("sahara", "node_group_templates", order=next(_sahara_order),
               tenant_resource=True)
class SaharaNodeGroup(SynchronizedDeletion, base.ResourceManager):
    pass


# CEILOMETER

@base.resource("ceilometer", "alarms", order=700, tenant_resource=True)
class CeilometerAlarms(SynchronizedDeletion, base.ResourceManager):

    def id(self):
        return self.raw_resource.alarm_id

    def list(self):
        query = [{
            "field": "project_id",
            "op": "eq",
            "value": self.tenant_uuid
        }]
        return self._manager().list(q=query)


# ZAQAR

@base.resource("zaqar", "queues", order=800)
class ZaqarQueues(SynchronizedDeletion, base.ResourceManager):

    def list(self):
        return self.user.zaqar().queues()


# DESIGNATE

_designate_order = get_order(900)


@base.resource("designate", "domains", order=next(_designate_order))
class Designate(SynchronizedDeletion, base.ResourceManager):
    pass


@base.resource("designate", "servers", order=next(_designate_order),
               admin_required=True, perform_for_admin_only=True)
class DesignateServer(SynchronizedDeletion, base.ResourceManager):
    pass


# SWIFT

_swift_order = get_order(1000)


class SwiftMixin(SynchronizedDeletion, base.ResourceManager):

    def _manager(self):
        client = self._admin_required and self.admin or self.user
        return getattr(client, self._service)()

    def id(self):
        return self.raw_resource

    def delete(self):
        delete_method = getattr(self._manager(), "delete_%s" % self._resource)
        # NOTE(weiwu): *self.raw_resource is required because for deleting
        # container we are passing only container name, to delete object we
        # should pass as first argument container and second is object name.
        delete_method(*self.raw_resource)


@base.resource("swift", "object", order=next(_swift_order),
               tenant_resource=True)
class SwiftObject(SwiftMixin):

    def list(self):
        object_list = []
        containers = self._manager().get_account(full_listing=True)[1]
        for con in containers:
            objects = self._manager().get_container(con["name"],
                                                    full_listing=True)[1]
            for obj in objects:
                raw_resource = [con["name"], obj["name"]]
                object_list.append(raw_resource)
        return object_list


@base.resource("swift", "container", order=next(_swift_order),
               tenant_resource=True)
class SwiftContainer(SwiftMixin):

    def list(self):
        containers = self._manager().get_account(full_listing=True)[1]
        return [[con["name"]] for con in containers]


# MISTRAL

@base.resource("mistral", "workbooks", order=1100, tenant_resource=True)
class MistralWorkbooks(SynchronizedDeletion, base.ResourceManager):
    def delete(self):
        self._manager().delete(self.raw_resource.name)


# MURANO

_murano_order = get_order(1200)


@base.resource("murano", "environments", tenant_resource=True,
               order=next(_murano_order))
class MuranoEnvironments(base.ResourceManager):
    pass


# KEYSTONE

_keystone_order = get_order(9000)


class KeystoneMixin(SynchronizedDeletion):

    def _manager(self):
        return keystone_wrapper.wrap(getattr(self.admin, self._service)())

    def delete(self):
        delete_method = getattr(self._manager(), "delete_%s" % self._resource)
        delete_method(self.id())

    def list(self):
        # TODO(boris-42): We should use such stuff in all list commands.
        resources = self._resource + "s"
        list_method = getattr(self._manager(), "list_%s" % resources)

        return filter(kutils.is_temporary, list_method())


@base.resource("keystone", "user", order=next(_keystone_order),
               admin_required=True, perform_for_admin_only=True)
class KeystoneUser(KeystoneMixin, base.ResourceManager):
    pass


@base.resource("keystone", "project", order=next(_keystone_order),
               admin_required=True, perform_for_admin_only=True)
class KeystoneProject(KeystoneMixin, base.ResourceManager):
    pass


@base.resource("keystone", "service", order=next(_keystone_order),
               admin_required=True, perform_for_admin_only=True)
class KeystoneService(KeystoneMixin, base.ResourceManager):
    pass


@base.resource("keystone", "role", order=next(_keystone_order),
               admin_required=True, perform_for_admin_only=True)
class KeystoneRole(KeystoneMixin, base.ResourceManager):
    pass
