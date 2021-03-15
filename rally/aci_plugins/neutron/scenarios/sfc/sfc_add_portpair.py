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
@scenario.configure(name="ScenarioPlugin.sfc_add_portpair", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class SFCAddPortpair(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario,
                     nova_utils.NovaScenario,scenario.OpenStackScenario):

    def run(self, src_cidr, dest_cidr, vm_image, service_image1, flavor, public_network, username, password,
            dualstack, ipv6_cidr, ipv6_dest_cidr):
        
        public_net = self.clients("neutron").show_network(public_network)        
        secgroup = self.context.get("user", {}).get("secgroup")
        key_name=self.context["user"]["keypair"]["name"]
        
        net_list, sub_list = self.create_net_sub_for_sfc(src_cidr, dest_cidr, dualstack=dualstack, 
                ipv6_src_cidr=ipv6_cidr, ipv6_dest_cidr=ipv6_dest_cidr)
        router = self._create_router({}, False)
        self.add_interface_to_router(router, sub_list, dualstack)

        net1_id = net_list[0].get('network', {}).get('id')
        net2_id = net_list[1].get('network', {}).get('id')
        
        p1, p2, src_vm, dest_vm  = self.create_vms_for_sfc_test(secgroup, public_net, net_list[0], net_list[1],
                                                           vm_image, flavor, key_name)

        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        service_vm11, pin1, pout1 = self.boot_server(net_list[2], port_create_args, service_image1, flavor,
                                                 net2=net_list[3], service_vm=True, key_name=key_name)
        service_vm12, pin2, pout2 = self.boot_server(net_list[2], port_create_args, service_image1, flavor,
                                                 net2=net_list[3], service_vm=True, key_name=key_name)
        service_vm13, pin3, pout3 = self.boot_server(net_list[2], port_create_args, service_image1, flavor,
                                                     net2=net_list[3], service_vm=True, key_name=key_name)
       
        fip1 = p1.get('port', {}).get('fixed_ips')[0].get('ip_address')
        fip2 = p2.get('port', {}).get('fixed_ips')[0].get('ip_address')

        print "\nConfiguring destination-vm for traffic verification..\n"
        if dualstack:
            command1 = {
                "interpreter": "/bin/sh",
                "script_inline": "ip address add 192.168.200.101/24 dev eth1;\
                                ip address add 192.168.200.102/24 dev eth1;\
                                ip address add 192.168.200.103/24 dev eth1;route add default gw 192.168.200.1 eth1;\
                                ip -6 addr add  2001:d8::101/32 dev eth1; ip -6 addr add 2001:d8::102/32 dev eth1;\
                                ip -6 addr add 2001:d8::103/32 dev eth1; ip -6 route add 2001:d8::1 dev eth1"
            }
            command2 = {
                "interpreter": "/bin/sh",
                "script_inline": "ping -c 5 192.168.200.101;ping -c 5 192.168.200.102;\
                                ping -c 5 192.168.200.103; ping6 -c 5 2001:d8::101;ping6 -c 5 2001:d8::102;\
                                ping6 -c 5 2001:d8::103"
            }
        else:
            command1 = {
                "interpreter": "/bin/sh",
                "script_inline": "ip address add 192.168.200.101/24 dev eth1;\
                                ip address add 192.168.200.102/24 dev eth1;\
                                ip address add 192.168.200.103/24 dev eth1;route add default gw 192.168.200.1 eth1"
            }
            command2 = {
                "interpreter": "/bin/sh",
                "script_inline": "ping -c 5 192.168.200.101;ping -c 5 192.168.200.102;\
                                            ping -c 5 192.168.200.103"
            }

        self._remote_command(username, password, fip2, command1, dest_vm)
        
        try:
            pp1 = self._create_port_pair(pin1, pout1)
            pp2 = self._create_port_pair(pin2, pout2)
            pp3 = self._create_port_pair(pin3, pout3)
            ppg = self._create_port_pair_group([pp1, pp2, pp3])
            fc = self._create_flow_classifier(src_cidr, dest_cidr, net1_id, net2_id)
            if dualstack:
                fc2 = self._create_flow_classifier(ipv6_cidr, ipv6_dest_cidr, net1_id, net2_id, ethertype="IPv6")
                pc = self._create_port_chain([ppg], [fc, fc2])
            else:
                pc = self._create_port_chain([ppg], [fc])
            self.sleep_between(30, 40)

            print"Traffic verification with existing SFC..."
            self._remote_command(username, password, fip1, command2, src_vm)

            print"Adding a new port pair to the existing chain..."
            service_vm14, pin4, pout4 = self.boot_server(net_list[2], port_create_args, service_image1, flavor,
                                                         net2=net_list[3], service_vm=True, key_name=key_name)
            pp4 = self._create_port_pair(pin4, pout4)
            self._update_port_pair_group(ppg, [pp1, pp2, pp3, pp4])
            self.sleep_between(30, 40)

            print"Traffic verification after adding a new port pair"
            self._remote_command(username, password, fip1, command2, src_vm)
        except Exception as e:
            raise e
        finally:
            self.cleanup_sfc()
