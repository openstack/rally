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

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.neutron import utils
from rally.task import atomic
from rally.task import validation


class NeutronLoadbalancerV1(utils.NeutronScenario):
    """Benchmark scenarios for Neutron Loadbalancer v1."""

    @validation.restricted_parameters("subnet_id",
                                      subdict="pool_create_args")
    @validation.required_neutron_extensions("lbaas")
    @validation.required_services(consts.Service.NEUTRON)
    @validation.required_openstack(users=True)
    @validation.required_contexts("network")
    @scenario.configure(context={"cleanup": ["neutron"]})
    def create_and_list_pools(self, pool_create_args=None):
        """Create a pool(v1) and then list pools(v1).

        Measure the "neutron lb-pool-list" command performance.
        The scenario creates a pool for every subnet and then lists pools.

        :param pool_create_args: dict, POST /lb/pools request options
        """
        pool_create_args = pool_create_args or {}
        networks = self.context.get("tenant", {}).get("networks", [])
        self._create_v1_pools(networks, **pool_create_args)
        self._list_v1_pools()

    @validation.restricted_parameters("subnet_id",
                                      subdict="pool_create_args")
    @validation.required_neutron_extensions("lbaas")
    @validation.required_services(consts.Service.NEUTRON)
    @validation.required_openstack(users=True)
    @validation.required_contexts("network")
    @scenario.configure(context={"cleanup": ["neutron"]})
    def create_and_delete_pools(self, pool_create_args=None):
        """Create pools(v1) and delete pools(v1).

        Measure the "neutron lb-pool-create" and "neutron lb-pool-delete"
        command performance. The scenario creates a pool for every subnet
        and then deletes those pools.

        :param pool_create_args: dict, POST /lb/pools request options
        """
        pool_create_args = pool_create_args or {}
        networks = self.context.get("tenant", {}).get("networks", [])
        pools = self._create_v1_pools(networks, **pool_create_args)
        for pool in pools:
            self._delete_v1_pool(pool["pool"])

    @validation.restricted_parameters("subnet_id",
                                      subdict="pool_create_args")
    @validation.required_neutron_extensions("lbaas")
    @validation.required_services(consts.Service.NEUTRON)
    @validation.required_openstack(users=True)
    @validation.required_contexts("network")
    @scenario.configure(context={"cleanup": ["neutron"]})
    def create_and_update_pools(self, pool_update_args=None,
                                pool_create_args=None):
        """Create pools(v1) and update pools(v1).

        Measure the "neutron lb-pool-create" and "neutron lb-pool-update"
        command performance. The scenario creates a pool for every subnet
        and then update those pools.

        :param pool_create_args: dict, POST /lb/pools request options
        :param pool_update_args: dict, POST /lb/pools update options
        """
        pool_create_args = pool_create_args or {}
        pool_update_args = pool_update_args or {}
        networks = self.context.get("tenant", {}).get("networks", [])
        pools = self._create_v1_pools(networks, **pool_create_args)
        for pool in pools:
            self._update_v1_pool(pool, **pool_update_args)

    @validation.restricted_parameters(["pool_id", "subnet_id"],
                                      subdict="vip_create_args")
    @validation.required_neutron_extensions("lbaas")
    @validation.required_services(consts.Service.NEUTRON)
    @validation.required_openstack(users=True)
    @validation.required_contexts("network")
    @scenario.configure(context={"cleanup": ["neutron"]})
    def create_and_list_vips(self, pool_create_args=None,
                             vip_create_args=None):
        """Create a vip(v1) and then list vips(v1).

        Measure the "neutron lb-vip-create" and "neutron lb-vip-list" command
        performance. The scenario creates a vip for every pool created and
        then lists vips.

        :param vip_create_args: dict, POST /lb/vips request options
        :param pool_create_args: dict, POST /lb/pools request options
        """
        vip_create_args = vip_create_args or {}
        pool_create_args = pool_create_args or {}
        networks = self.context.get("tenant", {}).get("networks", [])
        pools = self._create_v1_pools(networks, **pool_create_args)
        with atomic.ActionTimer(self, "neutron.create_%s_vips" % len(pools)):
            for pool in pools:
                self._create_v1_vip(pool, **vip_create_args)
        self._list_v1_vips()

    @validation.restricted_parameters(["pool_id", "subnet_id"],
                                      subdict="vip_create_args")
    @validation.required_neutron_extensions("lbaas")
    @validation.required_services(consts.Service.NEUTRON)
    @validation.required_openstack(users=True)
    @validation.required_contexts("network")
    @scenario.configure(context={"cleanup": ["neutron"]})
    def create_and_delete_vips(self, pool_create_args=None,
                               vip_create_args=None):
        """Create a vip(v1) and then delete vips(v1).

        Measure the "neutron lb-vip-create" and "neutron lb-vip-delete"
        command performance. The scenario creates a vip for pool and
        then deletes those vips.

        :param pool_create_args: dict, POST /lb/pools request options
        :param vip_create_args: dict, POST /lb/vips request options
        """
        vips = []
        pool_create_args = pool_create_args or {}
        vip_create_args = vip_create_args or {}
        networks = self.context.get("tenant", {}).get("networks", [])
        pools = self._create_v1_pools(networks, **pool_create_args)
        with atomic.ActionTimer(self, "neutron.create_%s_vips" % len(pools)):
            for pool in pools:
                vips.append(self._create_v1_vip(pool, **vip_create_args))
        for vip in vips:
            self._delete_v1_vip(vip["vip"])

    @validation.restricted_parameters(["pool_id", "subnet_id"],
                                      subdict="vip_create_args")
    @validation.required_neutron_extensions("lbaas")
    @validation.required_services(consts.Service.NEUTRON)
    @validation.required_openstack(users=True)
    @validation.required_contexts("network")
    @scenario.configure(context={"cleanup": ["neutron"]})
    def create_and_update_vips(self, pool_create_args=None,
                               vip_update_args=None,
                               vip_create_args=None):
        """Create vips(v1) and update vips(v1).

        Measure the "neutron lb-vip-create" and "neutron lb-vip-update"
        command performance. The scenario creates a pool for every subnet
        and then update those pools.

        :param pool_create_args: dict, POST /lb/pools request options
        :param vip_create_args: dict, POST /lb/vips request options
        :param vip_update_args: dict, POST /lb/vips update options
        """
        vips = []
        pool_create_args = pool_create_args or {}
        vip_create_args = vip_create_args or {}
        vip_update_args = vip_update_args or {}
        networks = self.context.get("tenant", {}).get("networks", [])
        pools = self._create_v1_pools(networks, **pool_create_args)
        with atomic.ActionTimer(self, "neutron.create_%s_vips" % len(pools)):
            for pool in pools:
                vips.append(self._create_v1_vip(pool, **vip_create_args))
        for vip in vips:
            self._update_v1_vip(vip, **vip_update_args)

    @validation.required_neutron_extensions("lbaas")
    @validation.required_services(consts.Service.NEUTRON)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["neutron"]})
    def create_and_list_healthmonitors(self, healthmonitor_create_args=None):
        """Create healthmonitors(v1) and list healthmonitors(v1).

        Measure the "neutron lb-healthmonitor-list" command performance. This
        scenario creates healthmonitors and lists them.

        :param healthmonitor_create_args: dict, POST /lb/healthmonitors request
        options
        """
        healthmonitor_create_args = healthmonitor_create_args or {}
        self._create_v1_healthmonitor(**healthmonitor_create_args)
        self._list_v1_healthmonitors()

    @validation.required_neutron_extensions("lbaas")
    @validation.required_services(consts.Service.NEUTRON)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["neutron"]})
    def create_and_delete_healthmonitors(self, healthmonitor_create_args=None):
        """Create a healthmonitor(v1) and delete healthmonitors(v1).

        Measure the "neutron lb-healthmonitor-create" and "neutron
        lb-healthmonitor-delete" command performance. The scenario creates
        healthmonitors and deletes those healthmonitors.

        :param healthmonitor_create_args: dict, POST /lb/healthmonitors request
        options
        """
        healthmonitor_create_args = healthmonitor_create_args or {}
        healthmonitor = self._create_v1_healthmonitor(
            **healthmonitor_create_args)
        self._delete_v1_healthmonitor(healthmonitor["health_monitor"])

    @validation.required_neutron_extensions("lbaas")
    @validation.required_services(consts.Service.NEUTRON)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["neutron"]})
    def create_and_update_healthmonitors(self,
                                         healthmonitor_create_args=None,
                                         healthmonitor_update_args=None):
        """Create a healthmonitor(v1) and update healthmonitors(v1).

        Measure the "neutron lb-healthmonitor-create" and "neutron
        lb-healthmonitor-update" command performance. The scenario creates
        healthmonitors and then updates them.

        :param healthmonitor_create_args: dict, POST /lb/healthmonitors request
        options
        :param healthmonitor_update_args: dict, POST /lb/healthmonitors update
        options
        """
        healthmonitor_create_args = healthmonitor_create_args or {}
        healthmonitor_update_args = healthmonitor_update_args or {
            "max_retries": random.choice(range(1, 10))}
        healthmonitor = self._create_v1_healthmonitor(
            **healthmonitor_create_args)
        self._update_v1_healthmonitor(healthmonitor,
                                      **healthmonitor_update_args)
