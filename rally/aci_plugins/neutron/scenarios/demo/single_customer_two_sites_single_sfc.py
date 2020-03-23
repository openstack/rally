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
@scenario.configure(name="ScenarioPlugin.single_customer_two_sites_single_sfc", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class SingleCustomerTwoSitesSingleSFC(vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario, scenario.OpenStackScenario):

    def run(self, access_network, nat_network, bras_image, nat_image, service_image1, flavor, username, password, access_router_ip):
        
        acc_net = self.clients("neutron").show_network(access_network)
        nat_net = self.clients("neutron").show_network(nat_network)              
        
        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        pfip1 = self._admin_create_port(acc_net, port_create_args)
        pfip1_id = pfip1.get('port', {}).get('id')
        trunk_payload = {"port_id": pfip1_id}
        trunk_bras1 = self._admin_create_trunk(trunk_payload)
        nics = [{"port-id": pfip1_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        bras_vm1 = self._admin_boot_server(bras_image, flavor, False, **kwargs)
        
        pfip2 = self._admin_create_port(acc_net, port_create_args)
        pfip2_id = pfip2.get('port', {}).get('id')
        trunk_payload = {"port_id": pfip2_id}
        trunk_bras2 = self._admin_create_trunk(trunk_payload)
        nics = [{"port-id": pfip2_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        bras_vm2 = self._admin_boot_server(bras_image, flavor, False, **kwargs)
        
        pfip3 = self._admin_create_port(nat_net, port_create_args)
        pfip3_id = pfip3.get('port', {}).get('id')
        trunk_payload = {"port_id": pfip3_id}
        trunk_nat = self._admin_create_trunk(trunk_payload)
        nics = [{"port-id": pfip3_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        nat_vm = self._admin_boot_server(nat_image, flavor, False, **kwargs)

        router = self._create_router({}, False)
        net1, sub1 = self._create_network_and_subnets({"apic:svi": True, "apic:bgp_enable": True, "apic:bgp_asn": "2010"},{"cidr": '192.168.0.0/24'}, 1, None)
        
        net1_id = net1.get('network', {}).get('id')
        self._create_svi_ports(net1, sub1, "192.168.0")
        self._add_interface_router(sub1[0].get("subnet"), router.get("router"))
        
        port_create_args["mac_address"] = 'fa:16:3e:bc:d5:38'
        subp1 = self._create_port(net1, port_create_args)
        subp1_id = subp1.get('port', {}).get('id')
        subport_payload = [{"port_id": subp1["port"]["id"],
                                "segmentation_type": "vlan",
                                "segmentation_id": '10'}]
        self._admin_add_subports_to_trunk(trunk_bras1, subport_payload)
        
        port_create_args = {}
        port_create_args["mac_address"] = 'fa:16:3e:bc:d5:37'
        subp2 = self._create_port(net1, port_create_args)
        subp2_id = subp2.get('port', {}).get('id')
        subport_payload = [{"port_id": subp2["port"]["id"],
                                "segmentation_type": "vlan",
                                "segmentation_id": '10'}]
        self._admin_add_subports_to_trunk(trunk_bras2, subport_payload)

        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        port_create_args["mac_address"] = 'fa:16:3e:1b:a1:a1'
        subp3 = self._create_port(net1, port_create_args)
        subp3_id = subp3.get('port', {}).get('id')
        subport_payload = [{"port_id": subp3["port"]["id"],
                                "segmentation_type": "vlan",
                                "segmentation_id": '10'}]
        self._admin_add_subports_to_trunk(trunk_nat, subport_payload)
         
        fip1 = pfip1.get('port', {}).get('fixed_ips')[0].get('ip_address')
        fip2 = pfip2.get('port', {}).get('fixed_ips')[0].get('ip_address')
        fip3 = pfip3.get('port', {}).get('fixed_ips')[0].get('ip_address')

        command1 = {
                    "interpreter": "/bin/sh",
                    "script_file": "/root/.rally/plugins/orchest/orchest_single_customer_two_site_bras1.sh" 
                }
        command2 = {
                    "interpreter": "/bin/sh",
                    "script_file": "/root/.rally/plugins/orchest/orchest_single_customer_two_site_bras2.sh"
                }
        command3 = {
                    "interpreter": "/bin/sh",
                    "script_file": "/root/.rally/plugins/orchest/orchest_single_customer_two_site_nat.sh"
                }
        
     	print "\nConfiguring the BRAS-VMs and running Bird init...\n"
        self._remote_command(username, password, fip1, command1, bras_vm1)
        self._remote_command(username, password, fip2, command2, bras_vm2)
        print "\nConfiguring the NAT-VM and running Bird init...\n"
        self._remote_command(username, password, fip3, command3, nat_vm)
        self.sleep_between(30,40)

        print "\nValidating BGP session from BRAS1-VM...\n"
        command4 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "birdc show protocol;birdc show route;birdc -s /tmp/sock-cats show protocol;birdc -s /tmp/sock-cats show route" 
                }

        self._remote_command(username, password, fip1, command4, bras_vm1)
        print "\nValidating BGP session from BRAS2-VM...\n"
        self._remote_command(username, password, fip2, command4, bras_vm2)
        print "\nValidating BGP session from NAT-VM...\n"
        self._remote_command(username, password, fip3, command4, nat_vm)
        
        print "\nConfiguring ACCESS-ROUTER for traffic verification...\n"
        command5 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo /home/noiro/oc/orchest_single_customer_multi_site.sh mksites"
                }
        self._remote_command_wo_server('noiro', password, access_router_ip, command5)

        print "\nTraffic verification from site-1 before creating SFC\n"
        command6 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo ip netns exec cats-site1 ping -c 5 10.1.1.1;sudo ip netns exec cats-site1 ping -c 5 8.8.8.1;sudo ip netns exec cats-site1 ping -c 5 8.8.8.2;sudo ip netns exec cats-site1 ping -c 5 8.8.8.3"
                }
        self._remote_command_wo_server('noiro', password, access_router_ip, command6)
        print "\nTraffic verification from site-2 before creating SFC\n"
        command7 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo ip netns exec cats-site2 ping -c 5 10.1.1.1;sudo ip netns exec cats-site2 ping -c 5 8.8.8.1;sudo ip netns exec cats-site2 ping -c 5 8.8.8.2;sudo ip netns exec cats-site2 ping -c 5 8.8.8.3"
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
        fc1 = self._create_flow_classifier('10.0.1.0/24', '0.0.0.0/0', net1_id, net1_id)
        fc2 = self._create_flow_classifier('10.0.2.0/24', '0.0.0.0/0', net1_id, net1_id)
        pc = self._create_port_chain([ppg], [fc1, fc2])
        self.sleep_between(30, 40)
    
        print "\nTraffic verification from site-1 after creating SFC\n"
        self._remote_command_wo_server('noiro', password, access_router_ip, command6)
        print "\nTraffic verification from site-2 after creating SFC\n"
        self._remote_command_wo_server('noiro', password, access_router_ip, command7)
        
        print "\nCleaning up ACCESS-ROUTER after traffic verification...\n"
        command0 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo /home/noiro/oc/orchest_single_customer_multi_site.sh delsites"
                }
        self._remote_command_wo_server('noiro', password, access_router_ip, command0)


        self._delete_server(bras_vm1)
        self._delete_server(bras_vm2)
        self._delete_server(nat_vm)
        self._admin_delete_trunk(trunk_bras1)
        self._admin_delete_trunk(trunk_bras2)
        self._admin_delete_trunk(trunk_nat)
        self._admin_delete_port(pfip1)
        self._admin_delete_port(pfip2)
        self._admin_delete_port(pfip3)
        self._delete_port_chain(pc)
        self._delete_port_pair_group(ppg)
        self._delete_flow_classifier(fc1)
        self._delete_flow_classifier(fc2)
        self._delete_port_pair(pp)
