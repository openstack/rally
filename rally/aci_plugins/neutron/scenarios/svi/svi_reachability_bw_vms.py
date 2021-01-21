from rally import consts
from rally import exceptions
from rally.common import validation
from rally.aci_plugins import vcpe_utils
from rally.aci_plugins import create_ostack_resources
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils

@validation.add("required_services", services=[consts.Service.NOVA, consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="ScenarioPlugin.svi_reachability_bw_vms", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class SVIReachabilityBetweenVMs(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario, scenario.OpenStackScenario):

    def run(self, cidr1, cidr2, image, flavor, public_net, aci_nodes, username, password, dualstack, v6cidr1, v6cidr2):
         
        router = self._create_router({}, False)
        public_network = self.clients("neutron").show_network(public_net)        
        secgroup = self.context.get("user", {}).get("secgroup")
        key_name=self.context["user"]["keypair"]["name"]

        networks=[]
        interfaces=[]
        vms=[]
        try:
            if dualstack:
                net1, sub1 = self.create_network_and_subnets_dual({"provider:network_type": "vlan", "apic:svi": True, "apic:bgp_enable": True, \
                        "apic:bgp_asn": "10"},{"cidr": cidr1}, 1, None, dualstack, {"cidr": v6cidr1, "ipv6_ra_mode":"dhcpv6-stateful", \
                        "ipv6_address_mode": "dhcpv6-stateful"}, None)
                net2, sub2 = self.create_network_and_subnets_dual({"provider:network_type": "vlan", "apic:svi": True, "apic:bgp_enable": True, \
                        "apic:bgp_asn": "20"},{"cidr": cidr2}, 1, None, dualstack, {"cidr": v6cidr2, "ipv6_ra_mode":"dhcpv6-stateful", \
                        "ipv6_address_mode": "dhcpv6-stateful"}, None)
             
                networks.extend([net1, net2])
                self._create_svi_ports(net1, sub1[0][0], cidr1[0:10], aci_nodes, dualstack, sub1[0][1], v6cidr1[0:8])
                self._create_svi_ports(net2, sub2[0][0], cidr2[0:10], aci_nodes, dualstack, sub2[0][1], v6cidr2[0:8])
                self._add_interface_router(sub1[0][0].get("subnet"), router.get("router"))
                self._add_interface_router(sub2[0][0].get("subnet"), router.get("router"))
                self._add_interface_router(sub1[0][1].get("subnet"), router.get("router"))
                self._add_interface_router(sub2[0][1].get("subnet"), router.get("router"))
                interfaces.extend([sub1[0][0],sub1[0][1],sub2[0][0],sub2[0][1]])  
            else:
                net1, sub1 = self._create_network_and_subnets({"provider:network_type": "vlan", "apic:svi": True, "apic:bgp_enable": True, \
                "apic:bgp_asn": "10"},{"cidr": cidr1}, 1, None)

                net2, sub2 = self._create_network_and_subnets({"provider:network_type": "vlan", "apic:svi": True, "apic:bgp_enable": True, \
                    "apic:bgp_asn": "20"},{"cidr": cidr2}, 1, None)

                networks.extend([net1, net2])
                self._create_svi_ports(net1, sub1[0], cidr1[0:10], aci_nodes, dualstack)
                self._create_svi_ports(net2, sub2[0], cidr2[0:10], aci_nodes, dualstack)
                self._add_interface_router(sub1[0].get("subnet"), router.get("router"))
                self._add_interface_router(sub2[0].get("subnet"), router.get("router"))
                interfaces.extend([sub1[0],sub2[0]])
            self.sleep_between(50, 60)

            pfip1, pfip2, vm1, vm2 = self.create_vms_for_svi_tests(secgroup, public_network, image, flavor, key_name, dualstack, \
                    networks=[net1, net2], ips=["192.168.10.101", "192.168.20.101"], v6ips=["2001:a10::65", "2001:a20::65"])
            vms.extend([vm1, vm2])

            fip1 = pfip1.get('port', {}).get('fixed_ips')[0].get('ip_address')
            fip2 = pfip2.get('port', {}).get('fixed_ips')[0].get('ip_address')

            print("\nConfiguring the VMs...\n")
            if dualstack:
                self.configure_vm(username, password, fip1, vm1, "svi_orchest_vm1_dual.sh")
                self.configure_vm(username, password, fip2, vm2, "svi_orchest_vm2_dual.sh")
            else:
                self.configure_vm(username, password, fip1, vm1, "svi_orchest_vm1.sh")
                self.configure_vm(username, password, fip2, vm2, "svi_orchest_vm2.sh")

            print "\nVerifying the traffic between SVI VMs from VM1...\n"
            if dualstack:
                command1 = {
                            "interpreter": "/bin/sh",
                            "script_inline": "ping -c 5 192.168.20.101;ping6 -c 5 2001:a20::65" 
                        }

                command2 = {
                            "interpreter": "/bin/sh",
                            "script_inline": "ping -c 5 192.168.10.101;ping6 -c 5 2001:a10::65" 
                        }
            else:
                command1 = {
                            "interpreter": "/bin/sh",
                            "script_inline": "ping -c 5 192.168.20.101"
                        }

                command2 = {
                            "interpreter": "/bin/sh",
                            "script_inline": "ping -c 5 192.168.10.101"
                        }
            self._remote_command(username, password, fip1, command1, vm1)
            print "\nVerifying the traffic between SVI VMs from VM2...\n"
            self._remote_command(username, password, fip2, command2, vm2)
        except Exception as e:
            raise e
        finally:
            if vms:self.delete_servers(vms)
            if interfaces:self.delete_router_interface(interfaces, router)
            if networks:self.delete_network(networks)

