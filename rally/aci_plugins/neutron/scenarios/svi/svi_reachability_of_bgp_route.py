from rally import consts
from rally import exceptions
from rally.task import utils
from rally.task import atomic
from rally.task import validation
from rally.common import validation
from rally.aci_plugins import vcpe_utils
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils

@validation.add("required_services", services=[consts.Service.NOVA, consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="ScenarioPlugin.svi_reachability_of_bgp_route", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class SVIReachabilityofBGProute(vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario, scenario.OpenStackScenario):

    def run(self, cidr1, cidr2, image, flavor, public_net, aci_nodes, username, password):
        
        router = self._create_router({}, False)
        public_network = self.clients("neutron").show_network(public_net)        
        secgroup = self.context.get("user", {}).get("secgroup")
        key_name=self.context["user"]["keypair"]["name"]

        net1, sub1 = self._create_network_and_subnets({"apic:svi": True, "apic:bgp_enable": True, "apic:bgp_asn": "10"},{"cidr": cidr1}, 1, None)
        net2, sub2 = self._create_network_and_subnets({"apic:svi": True, "apic:bgp_enable": True, "apic:bgp_asn": "20"},{"cidr": cidr2}, 1, None)

        self._create_svi_ports(net1, sub1[0], "192.168.10", aci_nodes)
        self._create_svi_ports(net2, sub2[0], "192.168.20", aci_nodes)
        self.sleep_between(50, 60)

        self._add_interface_router(sub1[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub2[0].get("subnet"), router.get("router"))
        
        port_create_args = {}
        port_create_args["security_groups"] = [secgroup.get('id')]
        pfip1 = self._create_port(public_network, port_create_args)
        pfip1_id = pfip1.get('port', {}).get('id')
        pfip2 = self._create_port(public_network, port_create_args)
        pfip2_id = pfip2.get('port', {}).get('id')
        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        port_create_args.update({"fixed_ips": [{"ip_address": "192.168.10.101"}]})      
        p1 = self._create_port(net1, port_create_args)
        p1_id = p1.get('port', {}).get('id')
        nics = [{"port-id": pfip1_id},{"port-id": p1_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        vm1 = self._boot_server(image, flavor, False, **kwargs)

	port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        port_create_args.update({"fixed_ips": [{"ip_address": "192.168.20.101"}]})
        p2 = self._create_port(net2, port_create_args)
        p2_id = p2.get('port', {}).get('id')
        nics = [{"port-id": pfip2_id},{"port-id": p2_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        vm2 = self._boot_server(image, flavor, False, **kwargs)
        self.sleep_between(30, 40)
 
        fip1 = pfip1.get('port', {}).get('fixed_ips')[0].get('ip_address')
        fip2 = pfip2.get('port', {}).get('fixed_ips')[0].get('ip_address')

        command1 = {
                    "interpreter": "/bin/sh",
                    "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/svi_orchest_vm1.sh" 
                }

        command2 = {
                    "interpreter": "/bin/sh",
                    "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/svi_orchest_vm2.sh" 
                }
        
        print "\nConfiguring the VMs...\n"
        self._remote_command(username, password, fip1, command1, vm1)
        self._remote_command(username, password, fip2, command2, vm2)

        print "\nRunning bird in the VMs...\n"
        command = {
                    "interpreter": "/bin/sh",
                    "script_inline": "bird -c /etc/bird/bird_svi.conf" 
                }

        self._remote_command(username, password, fip1, command, vm1)
        self._remote_command(username, password, fip2, command, vm2)
        self.sleep_between(50, 60)

        print "\nValidating BGP session from VM1...\n"
        command = {
                    "interpreter": "/bin/sh",
                    "script_inline": "birdc show protocol;birdc show route" 
                }

        self._remote_command(username, password, fip1, command, vm1)
        print "\nValidating BGP session from VM2...\n"
        self._remote_command(username, password, fip2, command, vm2)
        
        command0 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ping -c 5 192.168.10.199;ping -c 5 192.168.10.200;ping -c 5 10.10.10.1;ping -c 5 192.168.20.199;ping -c 5 10.10.10.2;ping -c 5 192.168.20.200"
                }
        self._remote_command(username, password, fip2, command0, vm2)
        print "\nVerifying the traffic from VM1...\n"
        command1 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ping -c 10 10.10.20.1;ping -c 10 10.10.20.2;ping -c 10 10.10.20.3;ping -c 10 10.10.20.4;ping -c 10 10.10.20.5" 
                }

        command2 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ping -c 10 10.10.10.1;ping -c 10 10.10.10.2;ping -c 10 10.10.10.3;ping -c 10 10.10.10.4;ping -c 10 10.10.10.5" 
                } 
        
        self._remote_command(username, password, fip1, command1, vm1)
        print "\nVerifying the traffic from VM2...\n"
        self._remote_command(username, password, fip2, command2, vm2)
