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
@scenario.configure(name="ScenarioPlugin.svi_reachability_of_bgp_route", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class SVIReachabilityofBGProute(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario,
        scenario.OpenStackScenario):

    def run(self, cidr1, cidr2, image, flavor, public_net, aci_nodes, username, password):
        
        router = self._create_router({}, False)
        public_network = self.clients("neutron").show_network(public_net)        
        secgroup = self.context.get("user", {}).get("secgroup")
        key_name=self.context["user"]["keypair"]["name"]
        
        net1, sub1 = self._create_network_and_subnets({"provider:network_type": "vlan", "apic:svi": True, "apic:bgp_enable": True, "apic:bgp_asn": "10"},{"cidr": cidr1}, 1, None)
        net2, sub2 = self._create_network_and_subnets({"provider:network_type": "vlan", "apic:svi": True, "apic:bgp_enable": True, "apic:bgp_asn": "20"},{"cidr": cidr2}, 1, None)
        self._create_svi_ports(net1, sub1[0], "192.168.10", aci_nodes)
        self._create_svi_ports(net2, sub2[0], "192.168.20", aci_nodes)
        self.sleep_between(50, 60)
        
        self._add_interface_router(sub1[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub2[0].get("subnet"), router.get("router"))

        pfip1, pfip2, vm1, vm2 = self.create_vms_for_svi_tests(secgroup, public_network, image, flavor, key_name,
                                                               networks=[net1, net2], ips=["192.168.10.101", "192.168.20.101"])
        
        fip1 = pfip1.get('port', {}).get('fixed_ips')[0].get('ip_address')
        fip2 = pfip2.get('port', {}).get('fixed_ips')[0].get('ip_address')

        print("\nConfiguring the VMs...\n")
        self.configure_vm(username, password, fip1, vm1, "svi_orchest_vm1.sh")
        self.configure_vm(username, password, fip2, vm2, "svi_orchest_vm2.sh")
        self.run_bird_conf(username, password, fip1, vm1, "bird_svi.conf")
        self.run_bird_conf(username, password, fip2, vm2, "bird_svi.conf")
        self.sleep_between(100, 120)

        print("Validating BGP session from VM1...")
        self.validate_bgp_session(username, password, [fip1, fip2], [vm1, vm2], no_demo=True)
        
        command0 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ping -c 5 192.168.10.199;\
                    ping -c 5 192.168.10.200;ping -c 5 10.10.10.1;\
                    ping -c 5 192.168.20.199;ping -c 5 10.10.10.2;ping -c 5 192.168.20.200"
                }
        self._remote_command(username, password, fip2, command0, vm2)
        print "\nVerifying the traffic from VM1...\n"
        command1 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ping -c 10 10.10.20.1;ping -c 10 10.10.20.2;\
                    ping -c 10 10.10.20.3;ping -c 10 10.10.20.4;ping -c 10 10.10.20.5"
                }

        command2 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ping -c 10 10.10.10.1;ping -c 10 10.10.10.2;\
                    ping -c 10 10.10.10.3;ping -c 10 10.10.10.4;ping -c 10 10.10.10.5"
                } 
        
        self._remote_command(username, password, fip1, command1, vm1)
        print "\nVerifying the traffic from VM2...\n"
        self._remote_command(username, password, fip2, command2, vm2)
