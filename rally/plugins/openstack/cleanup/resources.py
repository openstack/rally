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
from novaclient import exceptions as nova_exc
from oslo_config import cfg
from saharaclient.api import base as saharaclient_base

from rally.common import logging
from rally.common.plugin import discover
from rally.common import utils
from rally.plugins.openstack.cleanup import base
from rally.plugins.openstack.scenarios.cinder import utils as cinder_utils
from rally.plugins.openstack.scenarios.fuel import utils as futils
from rally.plugins.openstack.scenarios.keystone import utils as kutils
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.services.identity import identity
from rally.plugins.openstack.wrappers import glance as glance_wrapper
from rally.task import utils as task_utils

CONF = cfg.CONF
CONF.import_opt("glance_image_delete_timeout",
                "rally.plugins.openstack.scenarios.glance.utils",
                "benchmark")
CONF.import_opt("glance_image_delete_poll_interval",
                "rally.plugins.openstack.scenarios.glance.utils",
                "benchmark")

LOG = logging.getLogger(__name__)


def get_order(start):
    return iter(range(start, start + 99))


class SynchronizedDeletion(object):

    def is_deleted(self):
        return True


class QuotaMixin(SynchronizedDeletion):

    def id(self):
        return self.raw_resource

    def name(self):
        return None

    def delete(self):
        self._manager().delete(self.raw_resource)

    def list(self):
        return [self.tenant_uuid] if self.tenant_uuid else []


# MAGNUM

_magnum_order = get_order(80)


@base.resource(service=None, resource=None)
class MagnumMixin(base.ResourceManager):

    def id(self):
        """Returns id of resource."""
        return self.raw_resource.uuid

    def list(self):
        result = []
        marker = None
        while True:
            resources = self._manager().list(marker=marker)
            if not resources:
                break
            result.extend(resources)
            marker = resources[-1].uuid
        return result


@base.resource("magnum", "clusters", order=next(_magnum_order),
               tenant_resource=True)
class MagnumCluster(MagnumMixin):
    """Resource class for Magnum cluster."""


@base.resource("magnum", "cluster_templates", order=next(_magnum_order),
               tenant_resource=True)
class MagnumClusterTemplate(MagnumMixin):
    """Resource class for Magnum cluster_template."""


# HEAT

@base.resource("heat", "stacks", order=100, tenant_resource=True)
class HeatStack(base.ResourceManager):
    def name(self):
        return self.raw_resource.stack_name


# SENLIN

_senlin_order = get_order(150)


@base.resource(service=None, resource=None, admin_required=True)
class SenlinMixin(base.ResourceManager):

    def id(self):
        return self.raw_resource["id"]

    def _manager(self):
        client = self._admin_required and self.admin or self.user
        return getattr(client, self._service)()

    def list(self):
        return getattr(self._manager(), self._resource)()

    def delete(self):
        # make singular form of resource name from plural form
        res_name = self._resource[:-1]
        return getattr(self._manager(), "delete_%s" % res_name)(self.id())


@base.resource("senlin", "clusters", order=next(_senlin_order))
class SenlinCluster(SenlinMixin):
    """Resource class for Senlin Cluster."""


@base.resource("senlin", "profiles", order=next(_senlin_order),
               admin_required=False, tenant_resource=True)
class SenlinProfile(SenlinMixin):
    """Resource class for Senlin Profile."""


# NOVA

_nova_order = get_order(200)


@base.resource("nova", "servers", order=next(_nova_order),
               tenant_resource=True)
class NovaServer(base.ResourceManager):
    def list(self):
        """List all servers."""

        if hasattr(self._manager().api, "api_version"):
            # NOTE(andreykurilin): novaclient v2.27.0 includes ability to
            #   return all servers(see https://review.openstack.org/#/c/217101
            #   for more details). This release can be identified by presence
            #   of "api_version" property of ``novaclient.client.Client`` cls.
            return self._manager().list(limit=-1)
        else:
            # FIXME(andreykurilin): Remove code below, when minimum version of
            #   novaclient in requirements will allow it.
            # NOTE(andreykurilin): Nova API returns only limited number(
            #   'osapi_max_limit' option in nova.conf) of servers, so we need
            #   to use 'marker' option to list all pages of servers.
            result = []
            marker = None
            while True:
                servers = self._manager().list(marker=marker)
                if not servers:
                    break
                result.extend(servers)
                marker = servers[-1].id
            return result

    def delete(self):
        if getattr(self.raw_resource, "OS-EXT-STS:locked", False):
            self.raw_resource.unlock()
        super(NovaServer, self).delete()


@base.resource("nova", "floating_ips", order=next(_nova_order))
class NovaFloatingIPs(SynchronizedDeletion, base.ResourceManager):

    def name(self):
        return None


@base.resource("nova", "keypairs", order=next(_nova_order))
class NovaKeypair(SynchronizedDeletion, base.ResourceManager):
    pass


@base.resource("nova", "security_groups", order=next(_nova_order),
               tenant_resource=True)
class NovaSecurityGroup(SynchronizedDeletion, base.ResourceManager):

    def list(self):
        return filter(lambda x: x.name != "default",
                      super(NovaSecurityGroup, self).list())


@base.resource("nova", "quotas", order=next(_nova_order),
               admin_required=True, tenant_resource=True)
class NovaQuotas(QuotaMixin, base.ResourceManager):
    pass


@base.resource("nova", "flavors", order=next(_nova_order),
               admin_required=True, perform_for_admin_only=True)
class NovaFlavors(base.ResourceManager):
    def list(self):
        return [r for r in self._manager().list()
                if utils.name_matches_object(r.name, nova_utils.NovaScenario)]

    def is_deleted(self):
        try:
            self._manager().get(self.name())
        except nova_exc.NotFound:
            return True

        return False


@base.resource("nova", "floating_ips_bulk", order=next(_nova_order),
               admin_required=True)
class NovaFloatingIpsBulk(SynchronizedDeletion, base.ResourceManager):

    def id(self):
        return self.raw_resource.address

    def name(self):
        return None

    def list(self):
        return [floating_ip for floating_ip in self._manager().list()
                if utils.name_matches_object(floating_ip.pool,
                                             nova_utils.NovaScenario)]


@base.resource("nova", "networks", order=next(_nova_order),
               admin_required=True, tenant_resource=True)
class NovaNetworks(SynchronizedDeletion, base.ResourceManager):

    def name(self):
        return self.raw_resource.label

    def list(self):
        # NOTE(stpierre): any plugin can create a nova network via the
        # network wrapper, and that network's name will be created
        # according to its owner's random name generation
        # parameters. so we need to check if there are nova networks
        # whose name pattern matches those of any loaded plugin that
        # implements RandomNameGeneratorMixin
        classes = list(discover.itersubclasses(utils.RandomNameGeneratorMixin))
        return [net for net in self._manager().list()
                if utils.name_matches_object(net.label, *classes)]


@base.resource("nova", "aggregates", order=next(_nova_order),
               admin_required=True, perform_for_admin_only=True)
class NovaAggregate(SynchronizedDeletion, base.ResourceManager):

    def list(self):
        return [r for r in self._manager().list()
                if utils.name_matches_object(r.name, nova_utils.NovaScenario)]

    def delete(self):
        for host in self.raw_resource.hosts:
            self.raw_resource.remove_host(host)
        super(NovaAggregate, self).delete()


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
        #                returns True. And if get_only_instances() returns an
        #                empty list, this also returns True because we consider
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

    def supports_extension(self, extension):
        exts = self._manager().list_extensions().get("extensions", [])
        if any(ext.get("alias") == extension for ext in exts):
            return True
        return False

    def _manager(self):
        client = self._admin_required and self.admin or self.user
        return getattr(client, self._service)()

    def id(self):
        return self.raw_resource["id"]

    def name(self):
        return self.raw_resource.get("name", "")

    def delete(self):
        delete_method = getattr(self._manager(), "delete_%s" % self._resource)
        delete_method(self.id())

    def list(self):
        resources = self._resource + "s"
        list_method = getattr(self._manager(), "list_%s" % resources)

        return filter(lambda r: r["tenant_id"] == self.tenant_uuid,
                      list_method(tenant_id=self.tenant_uuid)[resources])


class NeutronLbaasV1Mixin(NeutronMixin):

    def list(self):
        if self.supports_extension("lbaas"):
            return super(NeutronLbaasV1Mixin, self).list()
        return []


@base.resource("neutron", "vip", order=next(_neutron_order),
               tenant_resource=True)
class NeutronV1Vip(NeutronLbaasV1Mixin):
    pass


@base.resource("neutron", "health_monitor", order=next(_neutron_order),
               tenant_resource=True)
class NeutronV1Healthmonitor(NeutronLbaasV1Mixin):
    pass


@base.resource("neutron", "pool", order=next(_neutron_order),
               tenant_resource=True)
class NeutronV1Pool(NeutronLbaasV1Mixin):
    pass


@base.resource("neutron", "port", order=next(_neutron_order),
               tenant_resource=True)
class NeutronPort(NeutronMixin):

    def delete(self):
        if (self.raw_resource["device_owner"] in
            ("network:router_interface",
             "network:router_interface_distributed",
             "network:ha_router_replicated_interface")):
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


@base.resource("neutron", "floatingip", order=next(_neutron_order),
               tenant_resource=True)
class NeutronFloatingIP(NeutronMixin):
    pass


@base.resource("neutron", "security_group", order=next(_neutron_order),
               tenant_resource=True)
class NeutronSecurityGroup(NeutronMixin):
    def list(self):
        tenant_sgs = super(NeutronSecurityGroup, self).list()
        # NOTE(pirsriva): Filter out "default" security group deletion
        # by non-admin role user
        return filter(lambda r: r["name"] != "default",
                      tenant_sgs)


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


@base.resource("cinder", "volume_types", order=next(_cinder_order),
               admin_required=True, perform_for_admin_only=True)
class CinderVolumeType(base.ResourceManager):
    def list(self):
        return [r for r in self._manager().list()
                if utils.name_matches_object(r.name,
                                             cinder_utils.CinderScenario)]


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


# MANILA

_manila_order = get_order(450)


@base.resource("manila", "shares", order=next(_manila_order),
               tenant_resource=True)
class ManilaShare(base.ResourceManager):
    pass


@base.resource("manila", "share_networks", order=next(_manila_order),
               tenant_resource=True)
class ManilaShareNetwork(base.ResourceManager):
    pass


@base.resource("manila", "security_services", order=next(_manila_order),
               tenant_resource=True)
class ManilaSecurityService(base.ResourceManager):
    pass


# GLANCE

@base.resource("glance", "images", order=500, tenant_resource=True)
class GlanceImage(base.ResourceManager):

    def _client(self):
        return getattr(self.admin or self.user, self._service)

    def _wrapper(self):
        return glance_wrapper.wrap(self._client(), self)

    def list(self):
        return self._wrapper().list_images(owner=self.tenant_uuid)

    def delete(self):
        client = self._client()
        client().images.delete(self.raw_resource.id)
        task_utils.wait_for_status(
            self.raw_resource, ["deleted"],
            check_deletion=True,
            update_resource=self._wrapper().get_image,
            timeout=CONF.benchmark.glance_image_delete_timeout,
            check_interval=CONF.benchmark.glance_image_delete_poll_interval)


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


class DesignateResource(SynchronizedDeletion, base.ResourceManager):
    def _manager(self):
        # Map resource names to api / client version
        resource_versions = {
            "domains": "1",
            "servers": "1",
            "recordsets": 2,
            "zones": "2"
        }
        version = resource_versions[self._resource]
        return getattr(getattr(self.user, self._service)(version),
                       self._resource)

    def _walk_pages(self, func, *args, **kwargs):
        """Generator that keeps fetching pages until there's none left."""
        marker = None

        while True:
            items = func(marker=marker, limit=100, *args, **kwargs)
            if not items:
                break
            for item in items:
                yield item
            marker = items[-1]["id"]


@base.resource("designate", "domains", order=next(_designate_order))
class DesignateDomain(DesignateResource):
    pass


@base.resource("designate", "servers", order=next(_designate_order),
               admin_required=True, perform_for_admin_only=True)
class DesignateServer(DesignateResource):
    pass


@base.resource("designate", "recordsets", order=next(_designate_order),
               tenant_resource=True)
class DesignateRecordSets(DesignateResource):
    def _client(self):
        # Map resource names to api / client version
        resource_versions = {
            "domains": "1",
            "servers": "1",
            "recordsets": 2,
            "zones": "2"
        }
        version = resource_versions[self._resource]
        return getattr(self.user, self._service)(version)

    def list(self):
        criterion = {"name": "s_rally_*"}
        for zone in self._walk_pages(self._client().zones.list,
                                     criterion=criterion):
            for recordset in self._walk_pages(self._client().recordsets.list,
                                              zone["id"]):
                yield recordset


@base.resource("designate", "zones", order=next(_designate_order),
               tenant_resource=True)
class DesignateZones(DesignateResource):
    def list(self):
        criterion = {"name": "s_rally_*"}
        return self._walk_pages(self._manager().list, criterion=criterion)


# SWIFT

_swift_order = get_order(1000)


class SwiftMixin(SynchronizedDeletion, base.ResourceManager):

    def _manager(self):
        client = self._admin_required and self.admin or self.user
        return getattr(client, self._service)()

    def id(self):
        return self.raw_resource

    def name(self):
        # NOTE(stpierre): raw_resource is a list of either [container
        # name, object name] (as in SwiftObject) or just [container
        # name] (as in SwiftContainer).
        return self.raw_resource[-1]

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

_mistral_order = get_order(1100)


class MistralMixin(SynchronizedDeletion, base.ResourceManager):

    def delete(self):
        self._manager().delete(self.raw_resource["id"])


@base.resource("mistral", "workbooks", order=next(_mistral_order),
               tenant_resource=True)
class MistralWorkbooks(MistralMixin):
    def delete(self):
        self._manager().delete(self.raw_resource["name"])


@base.resource("mistral", "workflows", order=next(_mistral_order),
               tenant_resource=True)
class MistralWorkflows(MistralMixin):
    pass


@base.resource("mistral", "executions", order=next(_mistral_order),
               tenant_resource=True)
class MistralExecutions(MistralMixin):
    pass


# MURANO

_murano_order = get_order(1200)


@base.resource("murano", "environments", tenant_resource=True,
               order=next(_murano_order))
class MuranoEnvironments(SynchronizedDeletion, base.ResourceManager):
    pass


@base.resource("murano", "packages", tenant_resource=True,
               order=next(_murano_order))
class MuranoPackages(base.ResourceManager):
    def list(self):
        return filter(lambda x: x.name != "Core library",
                      super(MuranoPackages, self).list())


# IRONIC

_ironic_order = get_order(1300)


@base.resource("ironic", "node", admin_required=True,
               order=next(_ironic_order), perform_for_admin_only=True)
class IronicNodes(base.ResourceManager):

    def id(self):
        return self.raw_resource.uuid


# FUEL

@base.resource("fuel", "environment", order=1400,
               admin_required=True, perform_for_admin_only=True)
class FuelEnvironment(base.ResourceManager):
    """Fuel environment.

    That is the only resource that can be deleted by fuelclient explicitly.
    """

    def id(self):
        return self.raw_resource["id"]

    def name(self):
        return self.raw_resource["name"]

    def is_deleted(self):
        return not self._manager().get(self.id())

    def list(self):
        return [env for env in self._manager().list()
                if utils.name_matches_object(env["name"],
                                             futils.FuelScenario)]


# WATCHER

_watcher_order = get_order(1500)


class WatcherMixin(SynchronizedDeletion, base.ResourceManager):

    def id(self):
        return self.raw_resource.uuid

    def list(self):
        return self._manager().list(limit=0)

    def is_deleted(self):
        from watcherclient.common.apiclient import exceptions
        try:
            self._manager().get(self.id())
            return False
        except exceptions.NotFound:
            return True


@base.resource("watcher", "audit_template", order=next(_watcher_order),
               admin_required=True, perform_for_admin_only=True)
class WatcherTemplate(WatcherMixin):
    pass


@base.resource("watcher", "action_plan", order=next(_watcher_order),
               admin_required=True, perform_for_admin_only=True)
class WatcherActionPlan(WatcherMixin):

    def name(self):
        return self.raw_resource.uuid


@base.resource("watcher", "audit", order=next(_watcher_order),
               admin_required=True, perform_for_admin_only=True)
class WatcherAudit(WatcherMixin):

    def name(self):
        return self.raw_resource.uuid


# KEYSTONE

_keystone_order = get_order(9000)


class KeystoneMixin(SynchronizedDeletion):

    def _manager(self):
        return identity.Identity(self.admin)

    def delete(self):
        delete_method = getattr(self._manager(), "delete_%s" % self._resource)
        delete_method(self.id())

    def list(self):
        # TODO(boris-42): We should use such stuff in all list commands.
        resources = self._resource + "s"
        list_method = getattr(self._manager(), "list_%s" % resources)
        return [r for r in list_method()
                if utils.name_matches_object(r.name, kutils.KeystoneScenario)]


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


@base.resource("keystone", "ec2", tenant_resource=True,
               order=next(_keystone_order))
class KeystoneEc2(SynchronizedDeletion, base.ResourceManager):
    def list(self):
        return self._manager().list(self.raw_resource)
