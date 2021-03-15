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
@scenario.configure(name="ScenarioPlugin.svi_scale", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")
class SVIScale(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario,
               nova_utils.NovaScenario, scenario.OpenStackScenario):

    def run(self, image, flavor, public_network, aci_nodes, username, password, scale, dualstack):
        
        router = self._create_router({}, False)
        public_net = self.clients("neutron").show_network(public_network)     
        secgroup = self.context.get("user", {}).get("secgroup")
        key_name=self.context["user"]["keypair"]["name"]

        fips = []
        vms = []
        networks=[]
        interfaces=[]
        try:
            for i in range(101, 101+int(scale)):
                port_create_args = {}
                port_create_args["security_groups"] = [secgroup.get('id')]
                pfip, pfip_id = self.create_port(public_net, port_create_args)
                fips.append(pfip.get('port', {}).get('fixed_ips')[0].get('ip_address'))
                
                if dualstack:
                    net, sub = self.create_network_and_subnets_dual({"provider:network_type": "vlan", "apic:svi": True, "apic:bgp_enable": True, \
                            "apic:bgp_asn": i},{"cidr": "192.168."+str(i)+".0/24"}, 1, None, dualstack, {"cidr": "2001:a"+hex(i)[2:]+"::/64", \
                            "gateway_ip": "2001:a"+hex(i)[2:]+"::1", "ipv6_ra_mode":"dhcpv6-stateful", "ipv6_address_mode": "dhcpv6-stateful"}, None)
                    networks.append(net)
                    self._create_svi_ports(net, sub[0][0], "192.168."+str(i), aci_nodes, dualstack, sub[0][1], "2001:a"+hex(i)[2:])
                    self._add_interface_router(sub[0][0].get("subnet"), router.get("router"))
                    self._add_interface_router(sub[0][1].get("subnet"), router.get("router"))
                    interfaces.extend([sub[0][0],sub[0][1]])
                else:
                    net, sub = self._create_network_and_subnets({"provider:network_type": "vlan", "apic:svi": True, "apic:bgp_enable": True, \
                            "apic:bgp_asn": i},{"cidr": "192.168."+str(i)+".0/24"}, 1, None)
                    networks.append(net)
                    self._create_svi_ports(net, sub[0], "192.168."+str(i), aci_nodes, dualstack)
                    self._add_interface_router(sub[0].get("subnet"), router.get("router"))
                    interfaces.append(sub[0])

                port_create_args = {}
                port_create_args.update({"port_security_enabled": "false"})
                if dualstack:
                    port_create_args.update({"fixed_ips": [{"ip_address": "192.168."+str(i)+".101"}, {"ip_address": "2001:a"+hex(i)[2:]+"::65"}]})
                else:
                    port_create_args.update({"fixed_ips": [{"ip_address": "192.168."+str(i)+".101"}]})
                p, p_id = self.create_port(net, port_create_args)
                vms.append(self.boot_vm([pfip_id, p_id], image, flavor, key_name=key_name))
            self.sleep_between(30, 40)
            
            prefix = []
            for i in range(101, 101+int(scale)):
                prefix.append(i)
                print("Configuring the VM-"+str(i%100)+"...")
                if dualstack:
                    command1 = {
                                "interpreter": "/bin/sh",
                                "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/orchest_svi_scale_dual.sh"
                            }
                    command2 = {
                                "interpreter": "/bin/sh",
                                "script_inline": "/usr/local/bin/orchest_svi_scale.sh " + str(i) +" "+ hex(i)[2:] + ";\
                                        /root/create_bird.sh " + str(i) +" "+ hex(i)[2:]
                            }
                else:
                    command1 = {
                                "interpreter": "/bin/sh",
                                "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/orchest_svi_scale.sh"
                            }   
                    command2 = {
                                "interpreter": "/bin/sh",
                                "script_inline": "/usr/local/bin/orchest_svi_scale.sh " + str(i) + ";/root/create_bird.sh " + str(i)
                            }
                self._remote_command(username, password, fips[i%101], command1, vms[i%101])
                self._remote_command(username, password, fips[i%101], command2, vms[i%101])
                
                print("Running bird in the VM-"+str(i%100)+"...")
                command3 = {
                            "interpreter": "/bin/sh",
                            "script_inline": "bird -c /etc/bird/bird_svi_scale.conf"
                        }
                self._remote_command(username, password, fips[i%101], command3, vms[i%101])
                self.sleep_between(10, 20)

            
            command4 = {
                        "interpreter": "/bin/sh",
                        "script_inline": "birdc show protocol;birdc show route"
                    }
            for i in range(101, 101+int(scale)):
                print("Validating BGP session from VM-"+str(i%100)+"...")
                self._remote_command(username, password, fips[i%101], command4, vms[i%101])
                print("Verify traffic from the VM-"+str(i%100)+"...")
                ping = []
                ping.extend(prefix)
                ping.pop(i%101)
                for j in ping:
                    if dualstack:
                        command5 = {
                                    "interpreter": "/bin/sh",
                                    "script_inline": "ping -c 5 11.10."+str(j)+".1;ping6 -c 5 -I 2001:a"+hex(i)[2:]+"::65 2001:b"+hex(j)[2:]+"::1;\
                                            ping -c 5 11.10."+str(j)+".2;ping6 -c 5 -I 2001:a"+hex(i)[2:]+"::65 2001:b"+hex(j)[2:]+"::2;\
                                            ping -c 5 11.10."+str(j)+".3;ping6 -c 5 -I 2001:a"+hex(i)[2:]+"::65 2001:b"+hex(j)[2:]+"::3;\
                                            ping -c 5 11.10."+str(j)+".4;ping6 -c 5 -I 2001:a"+hex(i)[2:]+"::65 2001:b"+hex(j)[2:]+"::4;\
                                            ping -c 5 11.10."+str(j)+".5;ping6 -c 5 -I 2001:a"+hex(i)[2:]+"::65 2001:b"+hex(j)[2:]+"::5"
                            }    
                    else:
                        command5 = {
                                    "interpreter": "/bin/sh",
                                    "script_inline": "ping -c 5 11.10."+str(j)+".1;ping -c 5 11.10."+str(j)+".2;\
                                            ping -c 5 11.10."+str(j)+".3;ping -c 5 11.10."+str(j)+".4;ping -c 5 11.10."+str(j)+".5"
                            }   
                    self._remote_command(username, password, fips[i%101], command5, vms[i%101])
        except Exception as e:
            raise e
        finally:
            if vms:self.delete_servers(vms)
            if interfaces:self.delete_router_interface(interfaces, router)
            if networks:self.delete_network(networks)
