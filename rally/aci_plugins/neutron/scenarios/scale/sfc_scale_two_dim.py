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
@scenario.configure(name="ScenarioPlugin.sfc_scale_two_dimension", context={"cleanup@openstack": ["nova", "neutron"],
                                                                            "keypair@openstack": {},
                                                                            "allow_ssh@openstack": None},
                    platform="openstack")
class SFCScaleTwoDimension(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario,
                           scenario.OpenStackScenario):

    def run(self, src_cidr, dest_cidr, vm_image, service_image1, service_image2, service_image3, flavor, public_network,
            username, password, x, y, ipv6_cidr, ipv6_dest_cidr, dualstack):

        public_net = self.clients("neutron").show_network(public_network)
        secgroup = self.context.get("user", {}).get("secgroup")
        service_image = [service_image1, service_image2, service_image3]
        for i in range(0, int(x) - 3): service_image.append(service_image[2])
        
        router = self._create_router({}, False)
        if dualstack:
            net1, sub_net1 = self.create_network_and_subnets_dual({"provider:network_type": "vlan"}, {"cidr": src_cidr}, 1,
                                                                  None, dualstack, {"cidr": ipv6_cidr, "gateway_ip": ipv6_cidr[:9]+'1', 
                                                                  "ipv6_ra_mode": "dhcpv6-stateful",
                                                                  "ipv6_address_mode": "dhcpv6-stateful"}, None)
            net2, sub_net2 = self.create_network_and_subnets_dual({"provider:network_type": "vlan"}, {"cidr": dest_cidr}, 1,
                                                                  None, dualstack, {"cidr": ipv6_dest_cidr, 
                                                                  "gateway_ip": ipv6_dest_cidr[:9]+'1', "ipv6_ra_mode": "dhcpv6-stateful",
                                                                   "ipv6_address_mode": "dhcpv6-stateful"}, None)

            self._add_interface_router(sub_net1[0][0].get("subnet"), router.get("router"))
            self._add_interface_router(sub_net1[0][1].get("subnet"), router.get("router"))
            self._add_interface_router(sub_net2[0][0].get("subnet"), router.get("router"))
            self._add_interface_router(sub_net2[0][1].get("subnet"), router.get("router"))
        else:
            net1, sub_net1 = self._create_network_and_subnets({"provider:network_type": "vlan"}, {"cidr": src_cidr}, 1,
                                                              None)
            net2, sub_net2 = self._create_network_and_subnets({"provider:network_type": "vlan"}, {"cidr": dest_cidr}, 1,
                                                              None)
            self._add_interface_router(sub_net1[0].get("subnet"), router.get("router"))
            self._add_interface_router(sub_net2[0].get("subnet"), router.get("router"))

        net1_id = net1.get('network', {}).get('id')
        net2_id = net2.get('network', {}).get('id')

        p1, p2, src_vm, dest_vm = self.create_vms_for_sfc_test(secgroup, public_net, net1, net2,
                                                               vm_image, flavor)

        fip1 = p1.get('port', {}).get('fixed_ips')[0].get('ip_address')
        fip2 = p2.get('port', {}).get('fixed_ips')[0].get('ip_address')

        print("Configuring destination-vm for traffic verification..")
        if dualstack:
            command1 = {
                "interpreter": "/bin/sh",
                "script_inline": "ip address add 192.168.200.101/24 dev eth1;ip address add 192.168.200.102/24 dev eth1;\
                            ip address add 192.168.200.103/24 dev eth1; ip address add 192.168.200.104/24 dev eth1;\
                            ip address add 192.168.200.105/24 dev eth1; route add default gw 192.168.200.1 eth1; \
                            ip -6 addr add  2001:d8::101/32 dev eth1; ip -6 addr add 2001:d8::102/32 dev eth1; \
                            ip -6 addr add 2001:d8::103/32 dev eth1; ip -6 addr add 2001:d8::104/32 dev eth1;\
                            ip -6 addr add 2001:d8::105/32 dev eth1; ip -6 route add 2001:d8::1 dev eth1"
            }
            command2 = {
                "interpreter": "/bin/sh",
                "script_inline": "ping -c 5 192.168.200.101;ping -c 5 192.168.200.102;ping -c 5 192.168.200.103;\
                                    ping -c 5 192.168.200.104; ping -c 5 192.168.200.105; ping6 -c 5 2001:d8::101;\
                                    ping6 -c 5 2001:d8::102; ping6 -c 5 2001:d8::103;  ping6 -c 5 2001:d8::104; ping6 -c 5 2001:d8::105"
            }
        else:
            command1 = {
                "interpreter": "/bin/sh",
                "script_inline": "ip address add 192.168.200.101/24 dev eth1;ip address add 192.168.200.102/24 dev eth1;\
                            ip address add 192.168.200.103/24 dev eth1; ip address add 192.168.200.104/24 dev eth1;\
                             ip address add 192.168.200.105/24 dev eth1; route add default gw 192.168.200.1 eth1"
            }
            command2 = {
                "interpreter": "/bin/sh",
                "script_inline": "ping -c 5 192.168.200.101;ping -c 5 192.168.200.102;ping -c 5 192.168.200.103;\
                            ping -c 5 192.168.200.104;ping -c 5 192.168.200.105"

            }
        self._remote_command(username, password, fip2, command1, dest_vm)
        
        print("Traffic verification before SFC")
        self._remote_command(username, password, fip1, command2, src_vm)
        
        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        try:
            print("Creating two-dimensional service function chain...")
            ppg = []
            pp = [[0 for i in range(int(y))] for j in range(int(x))]
            for i in range(0, int(x)):
                if dualstack:
                    left, sub_left = self.create_network_and_subnets_dual({"provider:network_type": "vlan"},
                        {"cidr": "1.1." + str(i) + ".0/24", 'host_routes': [{'destination': src_cidr, 'nexthop': '1.1.' + str(i) + '.1'}]}, 1, None,
                        dualstack, {"cidr": chr(ord('a') + i*2) + ':' + chr(ord('a') + i*2)+"::/64", 
                            "gateway_ip": chr(ord('a') + i*2) + ':' + chr(ord('a') + i*2)+"::1",
                            'host_routes': [{ 'destination': ipv6_cidr, 'nexthop': chr(ord('a') + i*2) + ':' + chr(ord('a') + i*2)+ '::1' }], 
                            "ipv6_ra_mode": "dhcpv6-stateful", "ipv6_address_mode": "dhcpv6-stateful"}, None)

                    right, sub_right = self.create_network_and_subnets_dual({"provider:network_type": "vlan"}, {"cidr": "2.2." + str(i) + ".0/24",  
                        'host_routes': [{'destination': '0.0.0.0/1', 'nexthop': '2.2.' + str(i) + '.1'}, 
                            {'destination': '128.0.0.0/1', 'nexthop': '2.2.' + str(i) + '.1'}]}, 1, None, dualstack, 
                        {"cidr": chr(ord('b') + i*2) + ':' + chr(ord('b') + i*2)+"::/64", "gateway_ip": chr(ord('b') + i*2) + ':' + chr(ord('b') + i*2)+"::1",
                        'host_routes': [{'destination': '0:0::/1', 'nexthop': chr(ord('b') + i*2) + ':' + chr(ord('b') + i*2)+ '::1'}, 
                            {'destination': '::/1', 'nexthop': chr(ord('b') + i*2) + ':' + chr(ord('b') + i*2)+ '::1'}],
                        "ipv6_ra_mode": "dhcpv6-stateful", "ipv6_address_mode": "dhcpv6-stateful"}, None)

                    self._add_interface_router(sub_left[0][0].get("subnet"), router.get("router"))
                    self._add_interface_router(sub_left[0][1].get("subnet"), router.get("router"))
                    self._add_interface_router(sub_right[0][0].get("subnet"), router.get("router"))
                    self._add_interface_router(sub_right[0][1].get("subnet"), router.get("router"))
                else:
                    left, sub_left = self._create_network_and_subnets({"provider:network_type": "vlan"}, {"cidr": "1.1." + str(i) + ".0/24", 'host_routes': [
                                                                    {'destination': src_cidr, 'nexthop': '1.1.' + str(i) + '.1'}]}, 1, None)
                    right, sub_right = self._create_network_and_subnets({"provider:network_type": "vlan"}, {"cidr": "2.2." + str(i) + ".0/24", 
                                                                       'host_routes': [{'destination': '0.0.0.0/1',  'nexthop': '2.2.' + str(i) + '.1'},
                                                                       {'destination': '128.0.0.0/1', 'nexthop': '2.2.' + str(i) + '.1'}]}, 1, None)

                    self._add_interface_router(sub_left[0].get("subnet"), router.get("router"))
                    self._add_interface_router(sub_right[0].get("subnet"), router.get("router"))

                ppl = []
                for j in range(0, int(y)):
                    service_vm, pin, pout = self.boot_server(left, port_create_args, service_image[i], flavor,
                                                             net2=right, service_vm=True)
                    pp[i][j] = self._create_port_pair(pin, pout)
                    ppl.append(pp[i][j])
                ppg.append(self._create_port_pair_group(ppl))

            fc = self._create_flow_classifier(src_cidr, dest_cidr, net1_id, net2_id)
            if dualstack:
                fc2 = self._create_flow_classifier(ipv6_cidr, ipv6_dest_cidr, net1_id, net2_id, ethertype="IPv6")
                pc = self._create_port_chain(ppg, [fc, fc2])
            else:
                pc = self._create_port_chain(ppg, [fc])
            self.sleep_between(30, 40)

            print("Traffic verification after creating SFC")
            self._remote_command(username, password, fip1, command2, src_vm)
        except Exception as e:
            raise e
        finally:
            self.cleanup_sfc()
