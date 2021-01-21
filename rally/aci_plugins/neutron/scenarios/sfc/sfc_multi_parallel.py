from rally import consts
from rally import exceptions
from rally.task import utils
from rally.task import atomic
from rally.task import validation
from rally.common import validation
from rally.aci_plugins import vcpe_utils
from rally.plugins.openstack import scenario
from rally.aci_plugins import create_ostack_resources
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils

@validation.add("required_services", services=[consts.Service.NOVA, consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="ScenarioPlugin.sfc_multi_parallel", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class SFCMultiParallel(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario, 
        scenario.OpenStackScenario):

    def run(self, src_cidr, dest_cidr, vm_image, service_image1, service_image2, service_image3, flavor, public_network, username, password,
            ipv6_cidr, ipv6_dest_cidr, dualstack):

        public_net = self.clients("neutron").show_network(public_network)        
        secgroup = self.context.get("user", {}).get("secgroup")
        key_name=self.context["user"]["keypair"]["name"]

        #net_list, sub_list = self.create_net_sub_for_sfc(src_cidr, dest_cidr)
        net_list, sub_list = self.create_net_sub_for_sfc(src_cidr, dest_cidr, dualstack=dualstack,
                                                         ipv6_src_cidr=ipv6_cidr, ipv6_dest_cidr=ipv6_dest_cidr)
        left2, sub5 = self.create_network_and_subnets_dual({"provider:network_type": "vlan"}, {"cidr": "3.3.0.0/24", 'host_routes': [{'destination': src_cidr, 'nexthop': '3.3.0.1'}]}, 1, None, dualstack, {"cidr": 'c:c::/64', 'host_routes': [{'destination': ipv6_cidr, 'nexthop': 'c:c::1'}], "ipv6_ra_mode": "slaac", "ipv6_address_mode": "slaac"},None)

        right2, sub6 = self.create_network_and_subnets_dual({"provider:network_type": "vlan"}, {"cidr": "4.4.0.0/24",'host_routes': [{'destination': '0.0.0.0/1', 'nexthop': '4.4.0.1'}, {'destination': '128.0.0.0/1','nexthop': '4.4.0.1'}]}, 1, None, dualstack, {"cidr": "d:d::/64", 'host_routes': [{'destination': '0:0::/1', 'nexthop': 'd:d::1'}, {'destination': '::/1', 'nexthop': 'd:d::1'}], "ipv6_ra_mode": "slaac", "ipv6_address_mode": "slaac"}, None)

        left3, sub7 = self.create_network_and_subnets_dual({"provider:network_type": "vlan"}, {"cidr": "5.5.0.0/24", 'host_routes':[{'destination': src_cidr,'nexthop': '5.5.0.1'}]},1, None, dualstack, {"cidr": 'e:e::/64','host_routes': [{'destination': ipv6_cidr, 'nexthop': 'e:e::1'}], "ipv6_ra_mode": "slaac", "ipv6_address_mode": "slaac"}, None)
        right3, sub8 = self.create_network_and_subnets_dual({"provider:network_type": "vlan"}, {"cidr": "6.6.0.0/24", 'host_routes': [{'destination': '0.0.0.0/1', 'nexthop': '6.6.0.1'}, {'destination': '128.0.0.0/1', 'nexthop': '6.6.0.1'}]}, 1, None, dualstack, {"cidr": "f:f::/64", 'host_routes': [{'destination': '0:0::/1', 'nexthop': 'f:f::1'}, {'destination': '::/1', 'nexthop': 'f:f::1'}],  "ipv6_ra_mode": "slaac", "ipv6_address_mode": "slaac"}, None)


        router = self._create_router({}, False)
        self.add_interface_to_router(router, sub_list, dualstack)
        self._add_interface_router(sub5[0][0].get("subnet"), router.get("router"))
        self._add_interface_router(sub5[0][1].get("subnet"), router.get("router"))
        self._add_interface_router(sub6[0][0].get("subnet"), router.get("router"))
        self._add_interface_router(sub6[0][1].get("subnet"), router.get("router"))
        self._add_interface_router(sub7[0][0].get("subnet"), router.get("router"))
        self._add_interface_router(sub7[0][1].get("subnet"), router.get("router"))
        self._add_interface_router(sub8[0][0].get("subnet"), router.get("router"))
        self._add_interface_router(sub8[0][1].get("subnet"), router.get("router"))

        net1_id = net_list[0].get('network', {}).get('id')
        net2_id = net_list[1].get('network', {}).get('id')

        p1, p2, src_vm, dest_vm = self.create_vms_for_sfc_test(secgroup, public_net, net_list[0], net_list[1],
                                                           vm_image, flavor, key_name)
        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        service_vm1, pin1, pout1 = self.boot_server(net_list[2], port_create_args, service_image1, flavor,
                                                    net2=net_list[3], service_vm=True, key_name=key_name)
        service_vm21, pin21, pout21 = self.boot_server(left2, port_create_args, service_image2, flavor,
                                                    net2=right2, service_vm=True, key_name=key_name)
        service_vm22, pin22, pout22 = self.boot_server(left2, port_create_args, service_image2, flavor,
                                                       net2=right2, service_vm=True, key_name=key_name)
        service_vm23, pin23, pout23 = self.boot_server(left2, port_create_args, service_image2, flavor,
                                                       net2=right2, service_vm=True, key_name=key_name)
        service_vm3, pin3, pout3 = self.boot_server(left3, port_create_args, service_image3, flavor,
                                                       net2=right3, service_vm=True, key_name=key_name)

        fip1 = p1.get('port', {}).get('fixed_ips')[0].get('ip_address')
        fip2 = p2.get('port', {}).get('fixed_ips')[0].get('ip_address')

        print "\nConfiguring destination-vm for traffic verification..\n"
        if dualstack:
            command1 = {
                "interpreter": "/bin/sh",
                "script_inline": "ip address add 192.168.200.101/24 dev eth1;\
                                             ip address add 192.168.200.102/24 dev eth1;\
                                             ip address add 192.168.200.103/24 dev eth1;\
                                             ip address add 192.168.200.104/24 dev eth1;\
                                             ip address add 192.168.200.105/24 dev eth1;\
                                             route add default gw 192.168.200.1 eth1;\
                                             ip -6 addr add  2001:d8::101/32 dev eth1; ip -6 addr add 2001:d8::102/32 dev eth1;\
                                             ip -6 addr add 2001:d8::103/32 dev eth1; ip -6 addr add 2001:d8::104/32 dev eth1;\
                                             ip -6 addr add 2001:d8::105/32 dev eth1; ip -6 route add 2001:d8::1 dev eth1"
            }
            command2 = {
                "interpreter": "/bin/sh",
                "script_inline": "ping -c 5 192.168.200.101;ping -c 5 192.168.200.102;\
                                ping -c 5 192.168.200.103;ping -c 5 192.168.200.104;ping -c 5 192.168.200.105;\
                                 ping6 -c 5 2001:d8::101;ping6 -c 5 2001:d8::102;\
                                 ping6 -c 5 2001:d8::103; ping6 -c 5 2001:d8::104;ping6 -c 5 2001:d8::105"
            }
        else:
            command1 = {
                "interpreter": "/bin/sh",
                "script_inline": "ip address add 192.168.200.101/24 dev eth1;\
                                     ip address add 192.168.200.102/24 dev eth1;\
                                     ip address add 192.168.200.103/24 dev eth1;\
                                     ip address add 192.168.200.104/24 dev eth1;\
                                     ip address add 192.168.200.105/24 dev eth1;\
                                     route add default gw 192.168.200.1 eth1"
            }
            command2 = {
                "interpreter": "/bin/sh",
                "script_inline": "ping -c 5 192.168.200.101;ping -c 5 192.168.200.102;\
                                        ping -c 5 192.168.200.103;ping -c 5 192.168.200.104;ping -c 5 192.168.200.105"
            }

        self._remote_command(username, password, fip2, command1, dest_vm)

        print "\nTraffic verification before SFC\n"
        self._remote_command(username, password, fip1, command2, src_vm)
        try:
            print"Creating a parallel multi service function chain..."
            pp1 = self._create_port_pair(pin1, pout1)
            ppg1 = self._create_port_pair_group([pp1])
            pp21 = self._create_port_pair(pin21, pout21)
            pp22 = self._create_port_pair(pin22, pout22)
            pp23 = self._create_port_pair(pin23, pout23)
            ppg2 = self._create_port_pair_group([pp21, pp22, pp23])
            pp3 = self._create_port_pair(pin3, pout3)
            ppg3 = self._create_port_pair_group([pp3])
            fc = self._create_flow_classifier(src_cidr, dest_cidr, net1_id, net2_id)
            if dualstack:
                fc2 = self._create_flow_classifier(ipv6_cidr, ipv6_dest_cidr, net1_id, net2_id, ethertype="IPv6")
                pc = self._create_port_chain([ppg1, ppg2, ppg3], [fc, fc2])
            else:
                pc = self._create_port_chain([ppg1, ppg2, ppg3], [fc])
            self.sleep_between(50, 60)
            print"Traffic verification after creating SFC\n"
            self._remote_command(username, password, fip1, command2, src_vm)
        except Exception as e:
            raise e
        finally:
            self.cleanup_sfc()

