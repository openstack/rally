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

from neutronclient.common import exceptions as neutron_exceptions

from rally.benchmark.context.cleanup import base
from rally.benchmark.scenarios.keystone import utils as kutils
from rally.benchmark.wrappers import keystone as keystone_wrapper
from rally import log as logging


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


@base.resource("nova", "servers", order=_nova_order.next())
class NovaServer(base.ResourceManager):
    pass


@base.resource("nova", "keypairs", order=_nova_order.next())
class NovaKeypair(SynchronizedDeletion, base.ResourceManager):
    pass


@base.resource("nova", "security_groups", order=_nova_order.next())
class NovaSecurityGroup(SynchronizedDeletion, base.ResourceManager):

    def list(self):
        return filter(lambda x: x.name != "default",
                      super(NovaSecurityGroup, self).list())


@base.resource("nova", "quotas", order=_nova_order.next(),
               admin_required=True, tenant_resource=True)
class NovaQuotas(QuotaMixin, base.ResourceManager):
    pass


# NEUTRON

_neutron_order = get_order(300)


class NeutronMixin(SynchronizedDeletion):
    # Neutron has the best client ever, so we need to override everything

    def _manager(self):
        return getattr(self.user, self._service)()

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


@base.resource("neutron", "port", order=_neutron_order.next(),
               tenant_resource=True)
class NeutronPort(NeutronMixin, base.ResourceManager):

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


@base.resource("neutron", "router", order=_neutron_order.next(),
               tenant_resource=True)
class NeutronRouter(NeutronMixin, base.ResourceManager):
    pass


@base.resource("neutron", "subnet", order=_neutron_order.next(),
               tenant_resource=True)
class NeutronSubnet(NeutronMixin, base.ResourceManager):
    pass


@base.resource("neutron", "network", order=_neutron_order.next(),
               tenant_resource=True)
class NeutronNetwork(NeutronMixin, base.ResourceManager):
    pass


# CINDER

_cinder_order = get_order(400)


@base.resource("cinder", "backups", order=_cinder_order.next(),
               tenant_resource=True)
class CinderVolumeBackup(base.ResourceManager):
    pass


@base.resource("cinder", "volume_snapshots", order=_cinder_order.next(),
               tenant_resource=True)
class CinderVolumeSnapshot(base.ResourceManager):
    pass


@base.resource("cinder", "transfers", order=_cinder_order.next(),
               tenant_resource=True)
class CinderVolumeTransfer(base.ResourceManager):
    pass


@base.resource("cinder", "volumes", order=_cinder_order.next(),
               tenant_resource=True)
class CinderVolume(base.ResourceManager):
    pass


@base.resource("cinder", "quotas", order=_cinder_order.next(),
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


@base.resource("sahara", "job_executions", order=_sahara_order.next(),
               tenant_resource=True)
class SaharaJobExecution(base.ResourceManager):
    pass


@base.resource("sahara", "jobs", order=_sahara_order.next(),
               tenant_resource=True)
class SaharaJob(SynchronizedDeletion, base.ResourceManager):
    pass


@base.resource("sahara", "job_binary_internals", order=_sahara_order.next(),
               tenant_resource=True)
class SaharaJobBinaryInternals(SynchronizedDeletion, base.ResourceManager):
    pass


@base.resource("sahara", "job_binaries", order=_sahara_order.next(),
               tenant_resource=True)
class SaharaJobBinary(SynchronizedDeletion, base.ResourceManager):
    pass


@base.resource("sahara", "data_sources", order=_sahara_order.next(),
               tenant_resource=True)
class SaharaDataSource(SynchronizedDeletion, base.ResourceManager):
    pass


@base.resource("sahara", "clusters", order=_sahara_order.next(),
               tenant_resource=True)
class SaharaCluster(base.ResourceManager):
    pass


@base.resource("sahara", "cluster_templates", order=_sahara_order.next(),
               tenant_resource=True)
class SaharaClusterTemplate(SynchronizedDeletion, base.ResourceManager):
    pass


@base.resource("sahara", "node_group_templates", order=_sahara_order.next(),
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

@base.resource("designate", "domains", order=900)
class Designate(SynchronizedDeletion, base.ResourceManager):
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


@base.resource("keystone", "user", order=_keystone_order.next(),
               admin_required=True, perform_for_admin_only=True)
class KeystoneUser(KeystoneMixin, base.ResourceManager):
    pass


@base.resource("keystone", "project", order=_keystone_order.next(),
               admin_required=True, perform_for_admin_only=True)
class KeystoneProject(KeystoneMixin, base.ResourceManager):
    pass


@base.resource("keystone", "service", order=_keystone_order.next(),
               admin_required=True, perform_for_admin_only=True)
class KeystoneService(KeystoneMixin, base.ResourceManager):
    pass


@base.resource("keystone", "role", order=_keystone_order.next(),
               admin_required=True, perform_for_admin_only=True)
class KeystoneRole(KeystoneMixin, base.ResourceManager):
    pass
