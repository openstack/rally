# Copyright 2014: Intel Inc.
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

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.neutron import utils
from rally.task import validation


"""Scenarios for Neutron."""


@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="NeutronNetworks.create_and_list_networks",
                    platform="openstack")
class CreateAndListNetworks(utils.NeutronScenario):

    def run(self, network_create_args=None):
        """Create a network and then list all networks.

        Measure the "neutron net-list" command performance.

        If you have only 1 user in your context, you will
        add 1 network on every iteration. So you will have more
        and more networks and will be able to measure the
        performance of the "neutron net-list" command depending on
        the number of networks owned by users.

        :param network_create_args: dict, POST /v2.0/networks request options
        """
        self._create_network(network_create_args or {})
        self._list_networks()


@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="NeutronNetworks.create_and_show_network",
                    platform="openstack")
class CreateAndShowNetwork(utils.NeutronScenario):

    def run(self, network_create_args=None):
        """Create a network and show network details.

        Measure the "neutron net-show" command performance.

        :param network_create_args: dict, POST /v2.0/networks request options
        """
        network = self._create_network(network_create_args or {})
        self._show_network(network)


@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="NeutronNetworks.create_and_update_networks",
                    platform="openstack")
class CreateAndUpdateNetworks(utils.NeutronScenario):

    def run(self, network_update_args, network_create_args=None):
        """Create and update a network.

        Measure the "neutron net-create and net-update" command performance.

        :param network_update_args: dict, PUT /v2.0/networks update request
        :param network_create_args: dict, POST /v2.0/networks request options
        """
        network = self._create_network(network_create_args or {})
        self._update_network(network, network_update_args)


@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="NeutronNetworks.create_and_delete_networks",
                    platform="openstack")
class CreateAndDeleteNetworks(utils.NeutronScenario):

    def run(self, network_create_args=None):
        """Create and delete a network.

        Measure the "neutron net-create" and "net-delete" command performance.

        :param network_create_args: dict, POST /v2.0/networks request options
        """
        network = self._create_network(network_create_args or {})
        self._delete_network(network["network"])


@validation.add("number", param_name="subnets_per_network", minval=1,
                integer_only=True)
@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="NeutronNetworks.create_and_list_subnets",
                    platform="openstack")
class CreateAndListSubnets(utils.NeutronScenario):

    def run(self, network_create_args=None, subnet_create_args=None,
            subnet_cidr_start=None, subnets_per_network=1):
        """Create and a given number of subnets and list all subnets.

        The scenario creates a network, a given number of subnets and then
        lists subnets.

        :param network_create_args: dict, POST /v2.0/networks request
                                    options. Deprecated
        :param subnet_create_args: dict, POST /v2.0/subnets request options
        :param subnet_cidr_start: str, start value for subnets CIDR
        :param subnets_per_network: int, number of subnets for one network
        """
        network = self._create_network(network_create_args or {})
        self._create_subnets(network, subnet_create_args, subnet_cidr_start,
                             subnets_per_network)
        self._list_subnets()


@validation.add("number", param_name="subnets_per_network", minval=1,
                integer_only=True)
@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="NeutronNetworks.create_and_update_subnets",
                    platform="openstack")
class CreateAndUpdateSubnets(utils.NeutronScenario):

    def run(self, subnet_update_args, network_create_args=None,
            subnet_create_args=None, subnet_cidr_start=None,
            subnets_per_network=1):
        """Create and update a subnet.

        The scenario creates a network, a given number of subnets
        and then updates the subnet. This scenario measures the
        "neutron subnet-update" command performance.

        :param subnet_update_args: dict, PUT /v2.0/subnets update options
        :param network_create_args: dict, POST /v2.0/networks request
                                    options. Deprecated.
        :param subnet_create_args: dict, POST /v2.0/subnets request options
        :param subnet_cidr_start: str, start value for subnets CIDR
        :param subnets_per_network: int, number of subnets for one network
        """
        network = self._create_network(network_create_args or {})
        subnets = self._create_subnets(network, subnet_create_args,
                                       subnet_cidr_start, subnets_per_network)

        for subnet in subnets:
            self._update_subnet(subnet, subnet_update_args)


@validation.add("number", param_name="subnets_per_network", minval=1,
                integer_only=True)
@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="NeutronNetworks.create_and_show_subnets",
                    platform="openstack")
class CreateAndShowSubnets(utils.NeutronScenario):

    def run(self, network_create_args=None,
            subnet_create_args=None, subnet_cidr_start=None,
            subnets_per_network=1):
        """Create and show a subnet details.

        The scenario creates a network, a given number of subnets
        and show the subnet details. This scenario measures the
        "neutron subnet-show" command performance.

        :param network_create_args: dict, POST /v2.0/networks request
                                    options.
        :param subnet_create_args: dict, POST /v2.0/subnets request options
        :param subnet_cidr_start: str, start value for subnets CIDR
        :param subnets_per_network: int, number of subnets for one network
        """
        network = self._get_or_create_network(network_create_args)
        subnets = self._create_subnets(network, subnet_create_args,
                                       subnet_cidr_start, subnets_per_network)

        for subnet in subnets:
            self._show_subnet(subnet)


@validation.add("number", param_name="subnets_per_network", minval=1,
                integer_only=True)
@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="NeutronNetworks.create_and_delete_subnets",
                    platform="openstack")
class CreateAndDeleteSubnets(utils.NeutronScenario):

    def run(self, network_create_args=None, subnet_create_args=None,
            subnet_cidr_start=None, subnets_per_network=1):
        """Create and delete a given number of subnets.

        The scenario creates a network, a given number of subnets and then
        deletes subnets.

        :param network_create_args: dict, POST /v2.0/networks request
                                    options. Deprecated.
        :param subnet_create_args: dict, POST /v2.0/subnets request options
        :param subnet_cidr_start: str, start value for subnets CIDR
        :param subnets_per_network: int, number of subnets for one network
        """
        network = self._get_or_create_network(network_create_args)
        subnets = self._create_subnets(network, subnet_create_args,
                                       subnet_cidr_start, subnets_per_network)

        for subnet in subnets:
            self._delete_subnet(subnet)


@validation.add("number", param_name="subnets_per_network", minval=1,
                integer_only=True)
@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="NeutronNetworks.create_and_list_routers",
                    platform="openstack")
class CreateAndListRouters(utils.NeutronScenario):

    def run(self, network_create_args=None, subnet_create_args=None,
            subnet_cidr_start=None, subnets_per_network=1,
            router_create_args=None):
        """Create and a given number of routers and list all routers.

        Create a network, a given number of subnets and routers
        and then list all routers.

        :param network_create_args: dict, POST /v2.0/networks request
                                    options. Deprecated.
        :param subnet_create_args: dict, POST /v2.0/subnets request options
        :param subnet_cidr_start: str, start value for subnets CIDR
        :param subnets_per_network: int, number of subnets for one network
        :param router_create_args: dict, POST /v2.0/routers request options
        """
        self._create_network_structure(network_create_args, subnet_create_args,
                                       subnet_cidr_start, subnets_per_network,
                                       router_create_args)
        self._list_routers()


@validation.add("number", param_name="subnets_per_network", minval=1,
                integer_only=True)
@validation.add("required_services", services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="NeutronNetworks.create_and_show_routers",
                    platform="openstack")
class CreateAndShowRouters(utils.NeutronScenario):

    def run(self, network_create_args=None, subnet_create_args=None,
            subnet_cidr_start=None, subnets_per_network=1,
            router_create_args=None):
        """Create and show a given number of routers.

        Create a network, a given number of subnets and routers
        and then show all routers.

        :param network_create_args: dict, POST /v2.0/networks request
                                    options
        :param subnet_create_args: dict, POST /v2.0/subnets request options
        :param subnet_cidr_start: str, start value for subnets CIDR
        :param subnets_per_network: int, number of subnets for each network
        :param router_create_args: dict, POST /v2.0/routers request options
        """
        network, subnets, routers = self._create_network_structure(
            network_create_args, subnet_create_args, subnet_cidr_start,
            subnets_per_network, router_create_args)

        for router in routers:
            self._show_router(router)


@validation.add("number", param_name="subnets_per_network", minval=1,
                integer_only=True)
@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="NeutronNetworks.create_and_update_routers",
                    platform="openstack")
class CreateAndUpdateRouters(utils.NeutronScenario):

    def run(self, router_update_args, network_create_args=None,
            subnet_create_args=None, subnet_cidr_start=None,
            subnets_per_network=1, router_create_args=None):
        """Create and update a given number of routers.

        Create a network, a given number of subnets and routers
        and then updating all routers.

        :param router_update_args: dict, PUT /v2.0/routers update options
        :param network_create_args: dict, POST /v2.0/networks request
                                    options. Deprecated.
        :param subnet_create_args: dict, POST /v2.0/subnets request options
        :param subnet_cidr_start: str, start value for subnets CIDR
        :param subnets_per_network: int, number of subnets for one network
        :param router_create_args: dict, POST /v2.0/routers request options
        """
        network, subnets, routers = self._create_network_structure(
            network_create_args, subnet_create_args, subnet_cidr_start,
            subnets_per_network, router_create_args)

        for router in routers:
            self._update_router(router, router_update_args)


@validation.add("number", param_name="subnets_per_network", minval=1,
                integer_only=True)
@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="NeutronNetworks.create_and_delete_routers",
                    platform="openstack")
class CreateAndDeleteRouters(utils.NeutronScenario):

    def run(self, network_create_args=None, subnet_create_args=None,
            subnet_cidr_start=None, subnets_per_network=1,
            router_create_args=None):
        """Create and delete a given number of routers.

        Create a network, a given number of subnets and routers
        and then delete all routers.

        :param network_create_args: dict, POST /v2.0/networks request
                                    options. Deprecated.
        :param subnet_create_args: dict, POST /v2.0/subnets request options
        :param subnet_cidr_start: str, start value for subnets CIDR
        :param subnets_per_network: int, number of subnets for one network
        :param router_create_args: dict, POST /v2.0/routers request options
        """
        network, subnets, routers = self._create_network_structure(
            network_create_args, subnet_create_args, subnet_cidr_start,
            subnets_per_network, router_create_args)

        for e in range(subnets_per_network):
            router = routers[e]
            subnet = subnets[e]
            self._remove_interface_router(subnet["subnet"], router["router"])
            self._delete_router(router)


@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="NeutronNetworks.set_and_clear_router_gateway",
                    platform="openstack")
class SetAndClearRouterGateway(utils.NeutronScenario):

    def run(self, enable_snat=True, network_create_args=None,
            router_create_args=None):
        """Set and Remove the external network gateway from a router.

        create an external network and a router, set external network
        gateway for the router, remove the external network gateway from
        the router.

        :param enable_snat: True if enable snat
        :param network_create_args: dict, POST /v2.0/networks request
                                    options
        :param router_create_args: dict, POST /v2.0/routers request options
        """
        network_create_args = network_create_args or {}
        router_create_args = router_create_args or {}
        ext_net = self._create_network(network_create_args)
        router = self._create_router(router_create_args)
        self._add_gateway_router(router, ext_net, enable_snat)
        self._remove_gateway_router(router)


@validation.add("number", param_name="ports_per_network", minval=1,
                integer_only=True)
@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="NeutronNetworks.create_and_list_ports",
                    platform="openstack")
class CreateAndListPorts(utils.NeutronScenario):

    def run(self, network_create_args=None,
            port_create_args=None, ports_per_network=1):
        """Create and a given number of ports and list all ports.

        :param network_create_args: dict, POST /v2.0/networks request
                                    options. Deprecated.
        :param port_create_args: dict, POST /v2.0/ports request options
        :param ports_per_network: int, number of ports for one network
        """
        network = self._get_or_create_network(network_create_args)
        for i in range(ports_per_network):
            self._create_port(network, port_create_args or {})

        self._list_ports()


@validation.add("number", param_name="ports_per_network", minval=1,
                integer_only=True)
@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="NeutronNetworks.create_and_update_ports",
                    platform="openstack")
class CreateAndUpdatePorts(utils.NeutronScenario):

    def run(self, port_update_args, network_create_args=None,
            port_create_args=None, ports_per_network=1):
        """Create and update a given number of ports.

        Measure the "neutron port-create" and "neutron port-update" commands
        performance.

        :param port_update_args: dict, PUT /v2.0/ports update request options
        :param network_create_args: dict, POST /v2.0/networks request
                                    options. Deprecated.
        :param port_create_args: dict, POST /v2.0/ports request options
        :param ports_per_network: int, number of ports for one network
        """
        network = self._get_or_create_network(network_create_args)
        for i in range(ports_per_network):
            port = self._create_port(network, port_create_args)
            self._update_port(port, port_update_args)


@validation.add("number", param_name="ports_per_network", minval=1,
                integer_only=True)
@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="NeutronNetworks.create_and_show_ports",
                    platform="openstack")
class CreateAndShowPorts(utils.NeutronScenario):

    def run(self, network_create_args=None,
            port_create_args=None, ports_per_network=1):
        """Create a given number of ports and show created ports in trun.

        Measure the "neutron port-create" and "neutron port-show" commands
        performance.

        :param network_create_args: dict, POST /v2.0/networks request
                                    options.
        :param port_create_args: dict, POST /v2.0/ports request options
        :param ports_per_network: int, number of ports for one network
        """
        network_create_args = network_create_args or {}
        port_create_args = port_create_args or {}

        network = self._get_or_create_network(network_create_args)
        for i in range(ports_per_network):
            port = self._create_port(network, port_create_args)
            msg = "Port isn't created"
            self.assertTrue(port, err_msg=msg)

            port_info = self._show_port(port)
            msg = "Created port and Showed port isn't equal"
            self.assertEqual(port["port"]["id"], port_info["port"]["id"],
                             err_msg=msg)


@validation.add("number", param_name="ports_per_network", minval=1,
                integer_only=True)
@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="NeutronNetworks.create_and_delete_ports",
                    platform="openstack")
class CreateAndDeletePorts(utils.NeutronScenario):

    def run(self, network_create_args=None,
            port_create_args=None, ports_per_network=1):
            """Create and delete a port.

            Measure the "neutron port-create" and "neutron port-delete"
            commands performance.

            :param network_create_args: dict, POST /v2.0/networks request
                                        options. Deprecated.
            :param port_create_args: dict, POST /v2.0/ports request options
            :param ports_per_network: int, number of ports for one network
            """
            network = self._get_or_create_network(network_create_args)
            for i in range(ports_per_network):
                port = self._create_port(network, port_create_args)
                self._delete_port(port)


@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@validation.add("external_network_exists", param_name="floating_network")
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="NeutronNetworks.create_and_list_floating_ips",
                    platform="openstack")
class CreateAndListFloatingIps(utils.NeutronScenario):

    def run(self, floating_network=None, floating_ip_args=None):
        """Create and list floating IPs.

        Measure the "neutron floating-ip-create" and "neutron floating-ip-list"
        commands performance.

        :param floating_network: str, external network for floating IP creation
        :param floating_ip_args: dict, POST /floatingips request options
        """
        floating_ip_args = floating_ip_args or {}
        self._create_floatingip(floating_network, **floating_ip_args)
        self._list_floating_ips()


@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@validation.add("external_network_exists", param_name="floating_network")
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="NeutronNetworks.create_and_delete_floating_ips",
                    platform="openstack")
class CreateAndDeleteFloatingIps(utils.NeutronScenario):

    def run(self, floating_network=None, floating_ip_args=None):
        """Create and delete floating IPs.

        Measure the "neutron floating-ip-create" and "neutron
        floating-ip-delete" commands performance.

        :param floating_network: str, external network for floating IP creation
        :param floating_ip_args: dict, POST /floatingips request options
        """
        floating_ip_args = floating_ip_args or {}
        floating_ip = self._create_floatingip(floating_network,
                                              **floating_ip_args)
        self._delete_floating_ip(floating_ip["floatingip"])


@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="NeutronNetworks.list_agents", platform="openstack")
class ListAgents(utils.NeutronScenario):

    def run(self, agent_args=None):
        """List all neutron agents.

        This simple scenario tests the "neutron agent-list" command by
        listing all the neutron agents.

        :param agent_args: dict, POST /v2.0/agents request options
        """
        agent_args = agent_args or {}
        self._list_agents(**agent_args)


@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_contexts", contexts=["network"])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="NeutronSubnets.delete_subnets",
                    platform="openstack")
class DeleteSubnets(utils.NeutronScenario):

    def run(self):
        """Delete a subnet that belongs to each precreated network.

        Each runner instance picks a specific subnet from the list based on its
        positional location in the list of users. By doing so, we can start
        multiple threads with sufficient number of users created and spread
        delete requests across all of them, so that they hit different subnets
        concurrently.

        Concurrent execution of this scenario should help reveal any race
        conditions and other concurrency issues in Neutron IP allocation layer,
        among other things.
        """
        tenant_id = self.context["tenant"]["id"]
        users = self.context["tenants"][tenant_id]["users"]
        number = users.index(self.context["user"])
        for network in self.context["tenants"][tenant_id]["networks"]:
            # delete one of subnets based on the user sequential number
            subnet_id = network["subnets"][number]
            self._delete_subnet({"subnet": {"id": subnet_id}})
