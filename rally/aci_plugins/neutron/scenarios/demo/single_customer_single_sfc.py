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
@scenario.configure(name="ScenarioPlugin.single_customer_single_sfc", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class SingleCustomerSingleSFC(vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario, scenario.OpenStackScenario):

    def run(self, access_network, access_network_bgp_asn, nat_network, nat_network_bgp_asn, aci_nodes, bras_image, nat_image, service_image1, flavor, username, password, access_router_ip):
        
        try:
            acc_net = self.clients("neutron").show_network(access_network)
            nat_net = self.clients("neutron").show_network(nat_network)       
        except:
            acc_net = self._admin_create_network('ACCESS', {"shared": True, "apic:svi": True, "apic:bgp_enable": True, "apic:bgp_asn": access_network_bgp_asn, "apic:distinguished_names": {"ExternalNetwork": "uni/tn-common/out-Access-Out/instP-data_ext_pol"}})
            acc_sub = self._admin_create_subnet(acc_net, {"cidr": '172.168.0.0/24'}, None)
            self._create_svi_ports(acc_net, acc_sub, '172.168.0', aci_nodes)

            nat_net = self._admin_create_network('INTERNET', {"shared": True, "apic:svi": True, "apic:bgp_enable": True, "apic:bgp_asn": nat_network_bgp_asn, "apic:distinguished_names": {"ExternalNetwork": "uni/tn-common/out-Internet-Out/instP-data_ext_pol"}})
            nat_sub = self._admin_create_subnet(nat_net, {"cidr": '173.168.0.0/24'}, None)
            self._create_svi_ports(nat_net, nat_sub, '173.168.0', aci_nodes)

        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        pfip1 = self._admin_create_port(acc_net, port_create_args)
        pfip1_id = pfip1.get('port', {}).get('id')
        trunk_payload = {"port_id": pfip1_id}
        trunk1 = self._admin_create_trunk(trunk_payload)
        nics = [{"port-id": pfip1_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        bras_vm = self._admin_boot_server(bras_image, flavor, False, **kwargs)
        
        pfip2 = self._admin_create_port(nat_net, port_create_args)
        pfip2_id = pfip2.get('port', {}).get('id')
        trunk_payload = {"port_id": pfip2_id}
        trunk2 = self._admin_create_trunk(trunk_payload)
        nics = [{"port-id": pfip2_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        nat_vm = self._admin_boot_server(nat_image, flavor, False, **kwargs)

        router = self._create_router({}, False)
        net1, sub1 = self._create_network_and_subnets({"apic:svi": True, "apic:bgp_enable": True, "apic:bgp_asn": "2010"},{"cidr": '192.168.0.0/24'}, 1, None)
        
        net1_id = net1.get('network', {}).get('id')
        self._create_svi_ports(net1, sub1[0], "192.168.0", aci_nodes)
        self._add_interface_router(sub1[0].get("subnet"), router.get("router"))
        
        subp1 = self._create_port(net1, port_create_args)
        subp1_id = subp1.get('port', {}).get('id')
        subport_payload = [{"port_id": subp1["port"]["id"],
                                "segmentation_type": "vlan",
                                "segmentation_id": '10'}]
        self._admin_add_subports_to_trunk(trunk1, subport_payload)
        subp1_mac = subp1.get('port', {}).get('mac_address')

        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        subp2 = self._create_port(net1, port_create_args)
        subp2_id = subp2.get('port', {}).get('id')
        subport_payload = [{"port_id": subp2["port"]["id"],
                                "segmentation_type": "vlan",
                                "segmentation_id": '10'}]
        self._admin_add_subports_to_trunk(trunk2, subport_payload)
        subp2_mac = subp2.get('port', {}).get('mac_address')

        fip1 = pfip1.get('port', {}).get('fixed_ips')[0].get('ip_address')
        fip2 = pfip2.get('port', {}).get('fixed_ips')[0].get('ip_address')
        
        command1 = {
                    "interpreter": "/bin/sh",
                    "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/orchest_single_customer_bras.sh" 
                }
        command2 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "/usr/local/bin/orchest_bras.sh " + subp1_mac + ";/usr/local/bin/run_bird"
                }
        command3 = {
                    "interpreter": "/bin/sh",
                    "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/orchest_single_customer_nat.sh"
                }
        command4 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "/usr/local/bin/orchest_nat.sh " + subp2_mac + ";/usr/local/bin/run_bird"
                }
    
     	print "\nConfiguring the BRAS-VM and running Bird init...\n"
        self._remote_command(username, password, fip1, command1, bras_vm)
        self._remote_command(username, password, fip1, command2, bras_vm)
        print "\nConfiguring the NAT-VM and running Bird init...\n"
        self._remote_command(username, password, fip2, command3, nat_vm)
        self._remote_command(username, password, fip2, command4, nat_vm)
        self.sleep_between(30,40)

        print "\nValidating BGP session from BRAS-VM...\n"
        command5 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "birdc show protocol;birdc show route;birdc -s /tmp/sock-cats show protocol;birdc -s /tmp/sock-cats show route" 
                }

        self._remote_command(username, password, fip1, command5, bras_vm)
        print "\nValidating BGP session from NAT-VM...\n"
        self._remote_command(username, password, fip2, command5, nat_vm)
        
        print "\nConfiguring ACCESS-router for traffic verification...\n"
        command6 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo /usr/local/bin/orchest_single_customer.sh mksites"
                }
        self._remote_command_wo_server('noiro', password, access_router_ip, command6)

        print "\nTraffic verification before creating SFC\n"
        command7 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo ip netns exec cats ping -c 5 10.1.1.1;sudo ip netns exec cats ping -c 5 8.8.8.1;sudo ip netns exec cats ping -c 5 8.8.8.2;sudo ip netns exec cats ping -c 5 8.8.8.3"
                }
        self._remote_command_wo_server('noiro', password, access_router_ip, command7)

        print "\nCreating a single service function chain...\n"

        left, sub2 = self._create_network_and_subnets({},{"cidr": "1.1.0.0/24", 'host_routes': [{'destination': '10.0.0.0/16', 'nexthop': '1.1.0.1'}]}, 1, None)
        right, sub3 = self._create_network_and_subnets({},{"cidr": "2.2.0.0/24", 'host_routes': [{'destination': '0.0.0.0/1', 'nexthop': '2.2.0.1'}, {'destination': '128.0.0.0/1', 'nexthop': '2.2.0.1'}]}, 1, None)

        self._add_interface_router(sub2[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub3[0].get("subnet"), router.get("router"))

        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        pin = self._create_port(left, port_create_args)
        pout = self._create_port(right, port_create_args)
        kwargs = {}
        pin_id = pin.get('port', {}).get('id')
        pout_id = pout.get('port', {}).get('id')
        nics = [{"port-id": pin_id}, {"port-id": pout_id}]
        kwargs.update({'nics': nics})
        service_vm = self._boot_server(service_image1, flavor, False, **kwargs)
        
        pp = self._create_port_pair(pin, pout)
        ppg = self._create_port_pair_group([pp])
        fc = self._create_flow_classifier('10.0.1.0/24', '0.0.0.0/0', net1_id, net1_id)
        pc = self._create_port_chain([ppg], [fc])
        self.sleep_between(30, 40)
         
        clean = [bras_vm, nat_vm, trunk1, trunk2, pfip1, pfip2, pc, ppg, fc, pp, service_vm, router, sub1[0], sub2[0], sub3[0], net1, left, right]
        try:
            print "\nTraffic verification after creating SFC\n"
            command8 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo ip netns exec cats ping -c 5 10.1.1.1"
                }
            self._remote_command_wo_server('noiro', password, access_router_ip, command8)
            
            command9 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo ip netns exec cats ping -c 5 8.8.8.1"
                }
            self._remote_command_wo_server('noiro', password, access_router_ip, command9)
            
            command10 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo ip netns exec cats ping -c 5 8.8.8.2"
                }
            self._remote_command_validate('noiro', password, access_router_ip, command10)
            
            command11 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo ip netns exec cats ping -c 5 8.8.8.3"
                }
            self._remote_command_validate('noiro', password, access_router_ip, command11)
        
        except:
            print "\nTraffic verification failed\n"
            print "\nCleaning up ACCESS-router after traffic verification...\n"
            command12 = {
                        "interpreter": "/bin/sh",
                        "script_inline": "sudo /usr/local/bin/orchest_single_customer.sh delsites"
                    }
            self._remote_command_wo_server('noiro', password, access_router_ip, command12)
            self.cleanup(clean)

        print "\nCleaning up ACCESS-router...\n"
        command8 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo /usr/local/bin/orchest_single_customer.sh delsites"
                }
        self._remote_command_wo_server('noiro', password, access_router_ip, command8)
        self.cleanup(clean)

    def cleanup(self, clean):
        self._delete_server(clean[0])
        self._delete_server(clean[1])
        self._admin_delete_trunk(clean[2])
        self._admin_delete_trunk(clean[3])
        self._admin_delete_port(clean[4])
        self._admin_delete_port(clean[5])
        self._delete_port_chain(clean[6])
        self._delete_port_pair_group(clean[7])
        self._delete_flow_classifier(clean[8])
        self._delete_port_pair(clean[9])
        self._delete_server(clean[10])
        self._admin_remove_interface_router(clean[12], clean[11])
        self._admin_remove_interface_router(clean[13], clean[11])
        self._admin_remove_interface_router(clean[14], clean[11])
        self._admin_delete_router(clean[11])
        self._delete_all_ports(clean[15])
        self._admin_delete_network(clean[15])
        self._delete_all_ports(clean[16])
        self._admin_delete_network(clean[16])
        self._delete_all_ports(clean[17])
        self._admin_delete_network(clean[17])
