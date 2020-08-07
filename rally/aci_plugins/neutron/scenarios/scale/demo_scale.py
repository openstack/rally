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
@scenario.configure(name="ScenarioPlugin.demo_scale", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class DemoScale(vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario, scenario.OpenStackScenario):

    def run(self, access_network, access_network_bgp_asn, nat_network, nat_network_bgp_asn, aci_nodes, bras_image, nat_image, service_image1, flavor, username, password, access_router_ip, scale):
        
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
        
        fip1 = pfip1.get('port', {}).get('fixed_ips')[0].get('ip_address')
        fip2 = pfip2.get('port', {}).get('fixed_ips')[0].get('ip_address')
        print "\nConfiguring ACCESS-ROUTER...\n"
        command1 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo /usr/local/bin/scale-orchest-access-router.sh -c " + str(scale)
                }
        self._remote_command_wo_server('noiro', password, access_router_ip, command1)

        pp = []
        ppg = []
        fc = []
        pc = []
        net = []
        left = []
        right = []
        router = []
        sub = []
        left_sub = []
        right_sub = []
        service_vm = []
        pro = []
        user = []
        for i in range(1, int(scale)+1):
            pro.append(self._create_project('customer-' + str(i), 'admin_domain'))
            pro_id = pro[i-1].id
            user.append(self._create_user('customer-' + str(i), 'noir0123', pro_id, "admin_domain", True, "Admin"))
            dic = self.context
            new_user = dic.get("users")[0]
            new_user.get("credential").update({'username': 'customer-' + str(i), 'tenant_name': 'customer-' + str(i)})
            self.context.get("users").append(new_user)
            self._change_client(i, self.context, None, None)
                
            hex_i = hex(int(i))[2:]
            router.append(self._create_router({}, False))
            net.append(self._create_network({"provider:network_type": "vlan", "apic:svi": True, "apic:bgp_enable": True, "apic:bgp_asn": 1000+i }))
            sub.append(self._create_subnet(net[i-1],{"cidr": '192.168.0.0/24'},  None))
            
            net_id = net[i-1]["network"]["id"]
            self._create_svi_ports(net[i-1], sub[i-1], "192.168.0", aci_nodes)
            self._add_interface_router(sub[i-1].get("subnet"), router[i-1].get("router"))
        
            port_create_args["mac_address"] = 'fa:16:3e:bc:d5:' + hex_i
            subp1 = self._create_port(net[i-1], port_create_args)
            subp1_id = subp1.get('port', {}).get('id')
            subport_payload = [{"port_id": subp1["port"]["id"],
                                "segmentation_type": "vlan",
                                "segmentation_id": 1000+i}]
            self._admin_add_subports_to_trunk(trunk_bras, subport_payload)
       
            port_create_args = {}
            port_create_args.update({"port_security_enabled": "false"})
            port_create_args["mac_address"] = 'fa:16:3e:1b:a1:' + hex_i
            subp2 = self._create_port(net[i-1], port_create_args)
            subp2_id = subp2.get('port', {}).get('id')
            subport_payload = [{"port_id": subp2["port"]["id"],
                                "segmentation_type": "vlan",
                                "segmentation_id": 1000+i}]
            self._admin_add_subports_to_trunk(trunk_nat, subport_payload)

            print "\nCreating a single service function chain for customer-" + str(i)

            left.append(self._create_network({"provider:network_type": "vlan"})) 
            left_sub.append(self._create_subnet(left[i-1], {"cidr": "1.1.0.0/24", 'host_routes': [{'destination': '10.0.0.0/16', 'nexthop': '1.1.0.1'}]}, None))
            right.append(self._create_network({"provider:network_type": "vlan"})) 
            right_sub.append(self._create_subnet(right[i-1], {"cidr": "2.2.0.0/24", 'host_routes': [{'destination': '0.0.0.0/1', 'nexthop': '2.2.0.1'}, {'destination': '128.0.0.0/1', 'nexthop': '2.2.0.1'}]}, None))

            self._add_interface_router(left_sub[i-1].get("subnet"), router[i-1].get("router"))
            self._add_interface_router(right_sub[i-1].get("subnet"), router[i-1].get("router"))

            port_create_args = {}
            port_create_args.update({"port_security_enabled": "false"})
            pin = self._create_port(left[i-1], port_create_args)
            pout = self._create_port(right[i-1], port_create_args)
            kwargs = {}
            pin_id = pin.get('port', {}).get('id')
            pout_id = pout.get('port', {}).get('id')
            nics = [{"port-id": pin_id}, {"port-id": pout_id}]
            kwargs.update({'nics': nics})
            service_vm.append(self._user_boot_server(service_image1, flavor, False, **kwargs))
        
            pp.append(self._create_port_pair(pin, pout))
            ppg.append(self._create_port_pair_group([pp[i-1]]))
            fc.append(self._create_flow_classifier('10.0.1.0/24', '8.8.8.0/24', net_id, net_id))
            pc.append(self._create_port_chain([ppg[i-1]], [fc[i-1]]))            
        self.sleep_between(30, 40)

        command2 = {
                    "interpreter": "/bin/sh",
                    "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/orchest_demo_scale_bras.sh"
                }

        command3 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "/usr/local/bin/orchest_demo_scale.sh " + str(scale) + ";/usr/local/bin/scale_run_bird.sh " + str(scale)
                }

        command4 = {
                    "interpreter": "/bin/sh",
                    "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/orchest_demo_scale_nat.sh"
                }
        
     	print "\nConfiguring the BRAS-VM and running Bird init...\n"
        self._remote_command(username, password, fip1, command2, bras_vm)
        self._remote_command(username, password, fip1, command3, bras_vm)
        
        print "\nConfiguring the NAT-VM and running Bird init...\n"
        self._remote_command(username, password, fip2, command4, nat_vm)
        self._remote_command(username, password, fip2, command3, nat_vm)
        self.sleep_between(30,40)
        
        print "\nValidating BGP session from BRAS-VM...\n"
        command5 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "birdc show protocol;birdc show route" 
                }

        self._remote_command(username, password, fip1, command5, bras_vm)
        for i in range(1, int(scale)+1):
            command6 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "birdc -s /tmp/sock-Customer-" + str(i) +" show protocol;birdc -s /tmp/sock-Customer-" + str(i) +" show route"
                }
            self._remote_command(username, password, fip1, command6, bras_vm)
        
        print "\nValidating BGP session from NAT-VM...\n"
        self._remote_command(username, password, fip2, command5, nat_vm)
        for i in range(1, int(scale)+1):
            command6 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "birdc -s /tmp/sock-Customer-" + str(i) +" show protocol;birdc -s /tmp/sock-Customer-" + str(i) +" show route"
                }
            self._remote_command(username, password, fip2, command6, nat_vm)
            self.sleep_between(20, 30)

        clean = [bras_vm, nat_vm, trunk_bras, trunk_nat, pfip1, pfip2, pc, fc, ppg, pp, service_vm, router, sub, left_sub, right_sub, net, left, right, pro, user]

        try:
            
            for i in range(1, int(scale)+1):
                print "\nTraffic verification from Customer-"+str(i)+" after creating SFC\n"
                command7 = {
                        "interpreter": "/bin/sh",
                        "script_inline": "sudo ip netns exec Customer-"+str(i)+" ping -c 5 10.1.1.1"
                    }
                self._remote_command_wo_server('noiro', password, access_router_ip, command7)

                command8 = {
                        "interpreter": "/bin/sh",
                        "script_inline": "sudo ip netns exec Customer-"+str(i)+" ping -c 5 8.8.8.1"
                    }
                self._remote_command_wo_server('noiro', password, access_router_ip, command8)

                command9 = {
                        "interpreter": "/bin/sh",
                        "script_inline": "sudo ip netns exec Customer-"+str(i)+" ping -c 5 8.8.8.2"
                    }
                self._remote_command_validate('noiro', password, access_router_ip, command9)

                command10 = {
                        "interpreter": "/bin/sh",
                        "script_inline": "sudo ip netns exec Customer-"+str(i)+" ping -c 5 8.8.8.3"
                    }
                self._remote_command_validate('noiro', password, access_router_ip, command10)
                self.sleep_between(25, 30)

        finally:
            print "\nCleaning up ACCESS-ROUTER after traffic verification...\n"
            command11 = {
                        "interpreter": "/bin/sh",
                        "script_inline": "sudo /usr/local/bin/scale-orchest-access-router.sh -d " + str(scale)
                    }
            self._remote_command_wo_server('noiro', password, access_router_ip, command11)
            self.cleanup(clean, scale)

    def cleanup(self, clean, scale):

        self._delete_server(clean[0])
        self._delete_server(clean[1])
        self._admin_delete_trunk(clean[2])
        self._admin_delete_trunk(clean[3])
        self._admin_delete_port(clean[4])
        self._admin_delete_port(clean[5])
        for i in range(0, int(scale)):
            self._delete_port_chain(clean[6][i])
            self._delete_flow_classifier(clean[7][i])
            self._delete_port_pair_group(clean[8][i])
            self._delete_port_pair(clean[9][i])
            self._delete_server(clean[10][i])
            self._admin_remove_interface_router(clean[12][i], clean[11][i])
            self._admin_remove_interface_router(clean[13][i], clean[11][i])
            self._admin_remove_interface_router(clean[14][i], clean[11][i])
            self._admin_delete_router(clean[11][i])
            self._delete_all_ports(clean[15][i])
            self._admin_delete_network(clean[15][i])
            self._delete_all_ports(clean[16][i])
            self._admin_delete_network(clean[16][i])
            self._delete_all_ports(clean[17][i])
            self._admin_delete_network(clean[17][i])
            self._delete_project(clean[18][i])
            self._delete_user(clean[19][i])
