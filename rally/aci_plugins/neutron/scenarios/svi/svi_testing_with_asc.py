from rally import consts
from rally import exceptions
from rally.common import validation
from rally.aci_plugins import vcpe_utils
from rally.plugins.openstack import scenario
from rally.aci_plugins import create_ostack_resources
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils

@validation.add("required_services", services=[consts.Service.NOVA, consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="ScenarioPlugin.svi_testing_with_asc", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class SVIReachabilityofBGProute(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario,
        scenario.OpenStackScenario):

    def run(self, cidr1, cidr2, image, flavor, public_net, aci_nodes, username, password, dualstack, v6cidr1, v6cidr2):
        
        router = self._create_router({}, False)
        public_network = self.clients("neutron").show_network(public_net)        
        secgroup = self.context.get("user", {}).get("secgroup")
        key_name=self.context["user"]["keypair"]["name"]

        networks=[]
        interfaces=[]
        vms=[]
        try:
            asc1 = self.create_address_scope("asc10", "4", False, False)
            if dualstack:
                asc1v6 = self.create_address_scope("asc1v6", "6", False, False, **{"apic:distinguished_names": {"VRF": "uni/tn-common/ctx-"}})

            subpool1 = self.create_subnet_pool("subpool10", asc1.get("address_scope")["id"], "192.168.10.0/24", "24", False, False)
            if dualstack:
                subpool1v6 = self.create_subnet_pool("subpool1v6", asc1v6.get("address_scope")["id"], "2001:a10::/64", "64", False, False)
            asc2 = self.create_address_scope("asc20", "4", False, False)
            if dualstack:
                asc2v6 = self.create_address_scope("asc2v6", "6", False, False, **{"apic:distinguished_names": {"VRF": "uni/tn-common/ctx-"}})

            subpool2 = self.create_subnet_pool("subpool20", asc2.get("address_scope")["id"], "192.168.20.0/24", "24", False, False)
            if dualstack:
                subpool2v6 = self.create_subnet_pool("subpool2v6", asc2v6.get("address_scope")["id"], "2001:a20::/64", "64", False, False)
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
                #net1, sub1 = self._create_network_and_subnets({"provider:network_type": "vlan", "apic:svi": True, "apic:bgp_enable": True, \
                #        "apic:bgp_asn": "10"},{"cidr": cidr1}, 1, None)

                #net2, sub2 = self._create_network_and_subnets({"provider:network_type": "vlan", "apic:svi": True, "apic:bgp_enable": True, \
                #        "apic:bgp_asn": "20"},{"cidr": cidr2}, 1, None)
                net1 = self._create_network({"provider:network_type": "vlan", "apic:svi": True, "apic:bgp_enable": True, "apic:bgp_asn": "10"})
                sub1 = self.create_subnet_with_pool(net1, {"subnetpool_id": subpool1.get("subnetpool")["id"], "ip_version": "4"}, None)
                net2 = self._create_network({"provider:network_type": "vlan", "apic:svi": True, "apic:bgp_enable": True, "apic:bgp_asn": "20"})
                sub2 = self.create_subnet_with_pool(net2, {"subnetpool_id": subpool2.get("subnetpool")["id"], "ip_version": "4"}, None)
                networks.extend([net1, net2])
                self._create_svi_ports(net1, sub1, cidr1[0:10], aci_nodes, dualstack)
                self._create_svi_ports(net2, sub2, cidr2[0:10], aci_nodes, dualstack)
                self._add_interface_router(sub1.get("subnet"), router.get("router"))
                self._add_interface_router(sub2.get("subnet"), router.get("router"))
                interfaces.extend([sub1,sub2])
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
                #self.configure_vm(username, password, fip1, vm1, "svitesting1.sh")
                #self.configure_vm(username, password, fip2, vm2, "svitesting2.sh")
            else:
                self.configure_vm(username, password, fip1, vm1, "svi_orchest_vm1.sh")
                self.configure_vm(username, password, fip2, vm2, "svi_orchest_vm2.sh")
            self.run_bird_conf(username, password, fip1, vm1, "bird_svi.conf")
            self.run_bird_conf(username, password, fip2, vm2, "bird_svi.conf")
            self.sleep_between(100, 120)

            print("Validating BGP session from VM1...")
            self.validate_bgp_session(username, password, [fip1, fip2], [vm1, vm2], no_demo=True)
            
            if dualstack:
                command0 = {
                           "interpreter": "/bin/sh",
                           "script_inline": "ping -c 5 192.168.10.199;ping6 -c 5 -I 2001:a20::65 2001:a10::c7\
                            ping -c 5 192.168.10.200;ping6 -c 5 -I 2001:a20::65 2001:a10::c8;\
                            ping -c 5 10.10.10.1;ping6 -c 5 -I 2001:a20::65 2001:b10::1\
                            ping -c 5 192.168.20.199;ping6 -c 5 -I 2001:a20::65 2001:b10::c7;\
                            ping -c 5 10.10.10.2;ping6 -c 5 -I 2001:a20::65 2001:b10::2;\
                            ping -c 5 192.168.20.200;ping6 -c 5 -I 2001:a20::65 2001:a20::c8"
                        }
            else:
                command0 = {
                            "interpreter": "/bin/sh",
                            "script_inline": "ping -c 5 192.168.10.199;\
                            ping -c 5 192.168.10.200;ping -c 5 10.10.10.1;\
                            ping -c 5 192.168.20.199;ping -c 5 10.10.10.2;ping -c 5 192.168.20.200"
                        }
            self._remote_command(username, password, fip2, command0, vm2)
            print "\nVerifying the traffic from VM1...\n"
            if dualstack:
                command1 = {
                            "interpreter": "/bin/sh",
                            "script_inline": "ping -c 5 10.10.20.1;ping6 -c 5 -I 2001:a10::65 2001:b20::1;\
                            ping -c 5 10.10.20.2;ping6 -c 5 -I 2001:a10::65 2001:b20::2;\
                            ping -c 5 10.10.20.3;ping6 -c 5 -I 2001:a10::65 2001:b20::3;\
                            ping -c 5 10.10.20.4;ping6 -c 5 -I 2001:a10::65 2001:b20::4;\
                            ping -c 5 10.10.20.5;ping6 -c 5 -I 2001:a10::65 2001:b20::5"
                        }

                command2 = {
                            "interpreter": "/bin/sh",
                            "script_inline": "ping -c 5 10.10.10.1;ping6 -c 5 -I 2001:a20::65 2001:b10::1;\
                            ping -c 5 10.10.10.2;ping6 -c 5 -I 2001:a20::65 2001:b10::2;\
                            ping -c 5 10.10.10.3;ping6 -c 5 -I 2001:a20::65 2001:b10::3;\
                            ping -c 5 10.10.10.4;ping6 -c 5 -I 2001:a20::65 2001:b10::4;\
                            ping -c 5 10.10.10.5;ping6 -c 5 -I 2001:a20::65 2001:b10::5"
                        }
            else:
                command1 = {
                            "interpreter": "/bin/sh",
                            "script_inline": "ping -c 5 10.10.20.1;ping -c 5 10.10.20.2;\
                            ping -c 5 10.10.20.3;ping -c 5 10.10.20.4;ping -c 5 10.10.20.5"
                        }

                command2 = {
                            "interpreter": "/bin/sh",
                            "script_inline": "ping -c 5 10.10.10.1;ping -c 5 10.10.10.2;\
                            ping -c 5 10.10.10.3;ping -c 5 10.10.10.4;ping -c 5 10.10.10.5"
                        } 
            
            self._remote_command(username, password, fip1, command1, vm1)
            print "\nVerifying the traffic from VM2...\n"
            self._remote_command(username, password, fip2, command2, vm2)
        except Exception as e:
            raise e
        finally:
            if vms:self.delete_servers(vms)
            if interfaces:self.delete_router_interface(interfaces, router)
            if networks:self.delete_network(networks)
