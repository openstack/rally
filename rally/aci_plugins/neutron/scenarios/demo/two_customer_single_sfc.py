from rally import consts
from rally import exceptions
from rally.task import utils
from rally.task import atomic
from rally.task import service
from rally.task import validation
from rally.common import validation
from rally.aci_plugins import vcpe_utils
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils

@validation.add("required_services", services=[consts.Service.NOVA, consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="ScenarioPlugin.two_customer_single_sfc", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class TwoCustomerSingleSFC(vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario, scenario.OpenStackScenario):

    def run(self, access_network, access_network_bgp_asn, nat_network, nat_network_bgp_asn, aci_nodes, bras_image, nat_image, service_image1, flavor, username, password, access_router_ip):

        try:
            acc_net = self.clients("neutron").show_network(access_network)
            nat_net = self.clients("neutron").show_network(nat_network)       
        except:
            acc_net = self._admin_create_network('ACCESS', {"provider:network_type": "vlan", "shared": True, "apic:svi": True, "apic:bgp_enable": True, "apic:bgp_asn": access_network_bgp_asn, "apic:distinguished_names": {"ExternalNetwork": "uni/tn-common/out-Access-Out/instP-data_ext_pol"}})
            acc_sub = self._admin_create_subnet(acc_net, {"cidr": '172.168.0.0/24'}, None)
            self._create_svi_ports(acc_net, acc_sub, '172.168.0', aci_nodes)

            nat_net = self._admin_create_network('INTERNET', {"provider:network_type": "vlan", "shared": True, "apic:svi": True, "apic:bgp_enable": True, "apic:bgp_asn": nat_network_bgp_asn, "apic:distinguished_names": {"ExternalNetwork": "uni/tn-common/out-Internet-Out/instP-data_ext_pol"}})
            nat_sub = self._admin_create_subnet(nat_net, {"cidr": '173.168.0.0/24'}, None)
            self._create_svi_ports(nat_net, nat_sub, '173.168.0', aci_nodes)

        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        pfip1 = self._admin_create_port(acc_net, port_create_args)
        pfip1_id = pfip1.get('port', {}).get('id')
        trunk_payload = {"port_id": pfip1_id}
        trunk_bras = self._admin_create_trunk(trunk_payload)
        nics = [{"port-id": pfip1_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        bras_vm = self._admin_boot_server(bras_image, flavor, False, **kwargs)

        pfip2 = self._admin_create_port(nat_net, port_create_args)
        pfip2_id = pfip2.get('port', {}).get('id')
        trunk_payload = {"port_id": pfip2_id}
        trunk_nat = self._admin_create_trunk(trunk_payload)
        nics = [{"port-id": pfip2_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        nat_vm = self._admin_boot_server(nat_image, flavor, False, **kwargs)

        pro1 = self._create_project('customer-1', 'admin_domain')
        pro1_id = pro1.id
        user1 = self._create_user('customer-1', 'noir0123', pro1_id, "admin_domain", True, "Admin")
        dic = self.context
        new_user = dic.get("users")[0]
        new_user.get("credential").update({'username': 'customer-1', 'tenant_name': 'customer-1'})
        self.context.get("users").append(new_user)
        self._change_client(1, self.context, None, None)

        router1 = self._create_router({}, False)
        net1, sub1 = self._create_network_and_subnets({"provider:network_type": "vlan", "apic:svi": True, "apic:bgp_enable": True, "apic:bgp_asn": "2010"},{"cidr": '192.168.0.0/24'}, 1, None)

        net1_id = net1.get('network', {}).get('id')
        self._create_svi_ports(net1, sub1[0], "192.168.0", aci_nodes)
        self._add_interface_router(sub1[0].get("subnet"), router1.get("router"))

        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        subp1 = self._create_port(net1, port_create_args)
        subp1_id = subp1.get('port', {}).get('id')
        subport_payload = [{"port_id": subp1["port"]["id"],
                                "segmentation_type": "vlan",
                                "segmentation_id": '10'}]
        self._admin_add_subports_to_trunk(trunk_bras, subport_payload)
        subp1_mac = subp1.get('port', {}).get('mac_address')

        subp2 = self._create_port(net1, port_create_args)
        subp2_id = subp2.get('port', {}).get('id')
        subport_payload = [{"port_id": subp2["port"]["id"],
                                "segmentation_type": "vlan",
                                "segmentation_id": '10'}]
        self._admin_add_subports_to_trunk(trunk_nat, subport_payload)
        subp2_mac = subp2.get('port', {}).get('mac_address')

        fip1 = pfip1.get('port', {}).get('fixed_ips')[0].get('ip_address')
        fip2 = pfip2.get('port', {}).get('fixed_ips')[0].get('ip_address')

        print "\nConfiguring ACCESS-ROUTER...\n"
        command1 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo /home/noiro/oc/orchest_two_customer.sh mksites"
                }
        self._remote_command_wo_server('noiro', password, access_router_ip, command1)

        print "\nCreating a single service function chain for customer-1...\n"

        left1, left1_sub = self._create_network_and_subnets({"provider:network_type": "vlan"},{"cidr": "1.1.0.0/24", 'host_routes': [{'destination': '10.0.0.0/16', 'nexthop': '1.1.0.1'}]}, 1, None)
        right1, right1_sub = self._create_network_and_subnets({"provider:network_type": "vlan"},{"cidr": "2.2.0.0/24", 'host_routes': [{'destination': '0.0.0.0/1', 'nexthop': '2.2.0.1'}, {'destination': '128.0.0.0/1', 'nexthop': '2.2.0.1'}]}, 1, None)

        self._add_interface_router(left1_sub[0].get("subnet"), router1.get("router"))
        self._add_interface_router(right1_sub[0].get("subnet"), router1.get("router"))

        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        pin1 = self._create_port(left1, port_create_args)
        pout1 = self._create_port(right1, port_create_args)
        kwargs = {}
        pin1_id = pin1.get('port', {}).get('id')
        pout1_id = pout1.get('port', {}).get('id')
        nics = [{"port-id": pin1_id}, {"port-id": pout1_id}]
        kwargs.update({'nics': nics})
        service_vm1 = self._user_boot_server(service_image1, flavor, False, **kwargs)

        pp1 = self._create_port_pair(pin1, pout1)
        ppg1 = self._create_port_pair_group([pp1])
        fc1 = self._create_flow_classifier('10.0.1.0/24', '8.8.8.0/24', net1_id, net1_id)
        pc1 = self._create_port_chain([ppg1], [fc1])

        print "\nCreating a single service function chain for customer-2...\n"
        pro2 = self._create_project('customer-2', 'admin_domain')
        pro2_id = pro2.id
        user2 = self._create_user('customer-2', 'noir0123', pro2_id, "admin_domain", True, "Admin")
        dic = self.context
        new_user = dic.get("users")[0]
        new_user.get("credential").update({'username': 'customer-2', 'tenant_name': 'customer-2'})
        self.context.get("users").append(new_user)
        self._change_client(2, self.context, None, None)

        router2 = self._create_router({}, False)
        net2, sub2 = self._create_network_and_subnets({"provider:network_type": "vlan", "apic:svi": True, "apic:bgp_enable": True, "apic:bgp_asn": "3010"},{"cidr": '192.168.0.0/24'}, 1, None)

        net2_id = net2.get('network', {}).get('id')
        self._create_svi_ports(net2, sub2[0], "192.168.0", aci_nodes)
        self._add_interface_router(sub2[0].get("subnet"), router2.get("router"))

        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        subp3 = self._create_port(net2, port_create_args)
        subp3_id = subp3.get('port', {}).get('id')
        subport_payload = [{"port_id": subp3["port"]["id"],
                                "segmentation_type": "vlan",
                                "segmentation_id": '20'}]
        self._admin_add_subports_to_trunk(trunk_bras, subport_payload)
        subp3_mac = subp3.get('port', {}).get('mac_address')

        subp4 = self._create_port(net2, port_create_args)
        subp4_id = subp4.get('port', {}).get('id')
        subport_payload = [{"port_id": subp4["port"]["id"],
                                "segmentation_type": "vlan",
                                "segmentation_id": '20'}]
        self._admin_add_subports_to_trunk(trunk_nat, subport_payload)
        subp4_mac = subp4.get('port', {}).get('mac_address')

        left2, left2_sub = self._create_network_and_subnets({"provider:network_type": "vlan"},{"cidr": "1.1.0.0/24", 'host_routes': [{'destination': '10.0.0.0/16', 'nexthop': '1.1.0.1'}]}, 1, None)
        right2, right2_sub = self._create_network_and_subnets({"provider:network_type": "vlan"},{"cidr": "2.2.0.0/24", 'host_routes': [{'destination': '0.0.0.0/1', 'nexthop': '2.2.0.1'}, {'destination': '128.0.0.0/1', 'nexthop': '2.2.0.1'}]}, 1, None)

        self._add_interface_router(left2_sub[0].get("subnet"), router2.get("router"))
        self._add_interface_router(right2_sub[0].get("subnet"), router2.get("router"))

        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        pin2 = self._create_port(left2, port_create_args)
        pout2 = self._create_port(right2, port_create_args)
        kwargs = {}
        pin2_id = pin2.get('port', {}).get('id')
        pout2_id = pout2.get('port', {}).get('id')
        nics = [{"port-id": pin2_id}, {"port-id": pout2_id}]
        kwargs.update({'nics': nics})
        service_vm2 = self._user_boot_server(service_image1, flavor, False, **kwargs)

        pp2 = self._create_port_pair(pin2, pout2)
        ppg2 = self._create_port_pair_group([pp2])
        fc2 = self._create_flow_classifier('10.0.1.0/24', '8.8.8.0/24', net2_id, net2_id)
        pc2 = self._create_port_chain([ppg2], [fc2])
        self.sleep_between(30, 40)

        command2 = {
                    "interpreter": "/bin/sh",
                    "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/orchest_two_customer_bras.sh"
                }
        command3 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "/usr/local/bin/orchest_bras.sh " + subp1_mac + " " + subp3_mac + ";/usr/local/bin/run_bird"
                }

        command4 = {
                    "interpreter": "/bin/sh",
                    "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/orchest_two_customer_nat.sh"
                }
        command5 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "/usr/local/bin/orchest_nat.sh " + subp2_mac + " " + subp4_mac + ";/usr/local/bin/run_bird"
                }

     	print "\nConfiguring the BRAS-VM and running Bird init...\n"
        self._remote_command(username, password, fip1, command2, bras_vm)
        self._remote_command(username, password, fip1, command3, bras_vm)
        print "\nConfiguring the NAT-VM and running Bird init...\n"
        self._remote_command(username, password, fip2, command4, nat_vm)
        self._remote_command(username, password, fip2, command5, nat_vm)
        self.sleep_between(30,40)

        print "\nValidating BGP session from BRAS-VM...\n"
        command6 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "birdc show protocol;birdc show route;birdc -s /tmp/sock-cats show protocol;birdc -s /tmp/sock-cats show route;birdc -s /tmp/sock-dogs show protocol;birdc -s /tmp/sock-dogs show route"
                }

        self._remote_command(username, password, fip1, command6, bras_vm)
        print "\nValidating BGP session from NAT-VM...\n"
        self._remote_command(username, password, fip2, command6, nat_vm)

        clean = [bras_vm, nat_vm, trunk_bras, trunk_nat, pfip1, pfip2, pc1, pc2, fc1, fc2, ppg1, ppg2, pp1, pp2, service_vm1, service_vm2, router1, sub1[0], left1_sub[0], right1_sub[0], net1, left1, right1, router2, sub2[0], left2_sub[0], right2_sub[0], net2, left2, right2, pro1, pro2, user1, user2]
        try:
            print "\nTraffic verification from Customer-1 after creating SFC\n"
            command7 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo ip netns exec cats ping -c 5 10.1.1.1"
                }
            self._remote_command_wo_server('noiro', password, access_router_ip, command7)

            command8 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo ip netns exec cats ping -c 5 8.8.8.1"
                }
            self._remote_command_wo_server('noiro', password, access_router_ip, command8)

            command9 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo ip netns exec cats ping -c 5 8.8.8.2"
                }
            self._remote_command_validate('noiro', password, access_router_ip, command9)

            command10 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo ip netns exec cats ping -c 5 8.8.8.3"
                }
            self._remote_command_validate('noiro', password, access_router_ip, command10)

            print "\nTraffic verification from Customer-2 after creating SFC\n"
            command11 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo ip netns exec dogs ping -c 5 10.1.1.1"
                }
            self._remote_command_wo_server('noiro', password, access_router_ip, command11)

            command12 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo ip netns exec dogs ping -c 5 8.8.8.1"
                }
            self._remote_command_wo_server('noiro', password, access_router_ip, command12)

            command13 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo ip netns exec dogs ping -c 5 8.8.8.2"
                }
            self._remote_command_validate('noiro', password, access_router_ip, command13)

            command14 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo ip netns exec dogs ping -c 5 8.8.8.3"
                }
            self._remote_command_validate('noiro', password, access_router_ip, command14)

        finally:
            print "\nCleaning up ACCESS-ROUTER after traffic verification...\n"
            command15 = {
                        "interpreter": "/bin/sh",
                        "script_inline": "sudo /home/noiro/oc/orchest_two_customer.sh delsites"
                    }
            self._remote_command_wo_server('noiro', password, access_router_ip, command15)
            self.cleanup(clean)


    def cleanup(self, clean):
        self._delete_server(clean[0])
        self._delete_server(clean[1])
        self._admin_delete_trunk(clean[2])
        self._admin_delete_trunk(clean[3])
        self._admin_delete_port(clean[4])
        self._admin_delete_port(clean[5])
        self._delete_port_chain(clean[6])
        self._delete_port_chain(clean[7])
        self._delete_flow_classifier(clean[8])
        self._delete_flow_classifier(clean[9])
        self._delete_port_pair_group(clean[10])
        self._delete_port_pair_group(clean[11])
        self._delete_port_pair(clean[12])
        self._delete_port_pair(clean[13])
        self._delete_server(clean[14])
        self._delete_server(clean[15])
        self._admin_remove_interface_router(clean[17], clean[16])
        self._admin_remove_interface_router(clean[18], clean[16])
        self._admin_remove_interface_router(clean[19], clean[16])
        self._admin_delete_router(clean[16])
        self._delete_all_ports(clean[20])
        self._admin_delete_network(clean[20])
        self._delete_all_ports(clean[21])
        self._admin_delete_network(clean[21])
        self._delete_all_ports(clean[22])
        self._admin_delete_network(clean[22])
        self._admin_remove_interface_router(clean[24], clean[23])
        self._admin_remove_interface_router(clean[25], clean[23])
        self._admin_remove_interface_router(clean[26], clean[23])
        self._admin_delete_router(clean[23])
        self._delete_all_ports(clean[27])
        self._admin_delete_network(clean[27])
        self._delete_all_ports(clean[28])
        self._admin_delete_network(clean[28])
        self._delete_all_ports(clean[29])
        self._admin_delete_network(clean[29])
        self._delete_project(clean[30])
        self._delete_project(clean[31])
        self._delete_user(clean[32])
        self._delete_user(clean[33])
