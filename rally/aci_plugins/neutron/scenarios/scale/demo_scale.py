from rally import consts
from rally import exceptions
from rally.common import validation
from rally.aci_plugins import create_ostack_resources
from rally.aci_plugins import vcpe_utils
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils

@validation.add("required_services", services=[consts.Service.NOVA, consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="ScenarioPlugin.demo_scale", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class DemoScale(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario, scenario.OpenStackScenario):

    resources_created = {"projects": [], "users": [], "vms": [], "trunks": [], "ports": [], "networks": [], "routers": [], "interfaces": []}

    def run(self, access_network, access_network_bgp_asn, nat_network, nat_network_bgp_asn, aci_nodes, bras_image, nat_image, service_image1, flavor, username, password, access_router_ip, scale):

        try:
            acc_net = self.create_network(access_network, 'ACCESS', access_network_bgp_asn,
                                          "uni/tn-common/out-Access-Out/instP-data_ext_pol", '172.168.0.0/24', aci_nodes)
            nat_net = self.create_network(nat_network, 'INTERNET', nat_network_bgp_asn,
                                          "uni/tn-common/out-Internet-Out/instP-data_ext_pol", '173.168.0.0/24', aci_nodes)

            print("Creating Bras vm and nat vm...")
            port_create_args = {}
            port_create_args.update({"port_security_enabled": "false"})
            bras_vm, trunk1, pfip1 = self.boot_server(acc_net, port_create_args, bras_image, flavor, admin=True)
            self.resources_created["vms"].append(bras_vm)
            self.resources_created["trunks"].append(trunk1)
            self.resources_created["ports"].append(pfip1)
            
            nat_vm, trunk2, pfip2 = self.boot_server(nat_net, port_create_args, nat_image, flavor, admin=True)
            self.resources_created["vms"].append(nat_vm)
            self.resources_created["trunks"].append(trunk2)
            self.resources_created["ports"].append(pfip2)

            fip1 = pfip1.get('port', {}).get('fixed_ips')[0].get('ip_address')
            fip2 = pfip2.get('port', {}).get('fixed_ips')[0].get('ip_address')

            print "\nConfiguring ACCESS-ROUTER...\n"
            command1 = {
                        "interpreter": "/bin/sh",
                        "script_inline": "sudo /usr/local/bin/scale-orchest-access-router.sh -c " + str(scale)
                    }
            self._remote_command_wo_server('noiro', password, access_router_ip, command1)

            for i in range(1, int(scale)+1):
                pro, user, new_user = self.create_rally_client('customer-' + str(i), 'customer-' + str(i), self.context)
                self.context.get("users").append(new_user)
                self._change_client(i, self.context, None, None)
                self.resources_created["projects"].append(pro)
                self.resources_created["users"].append(user)
                    
                hex_i = hex(int(i))[2:]
                router = self._create_router({}, False)
                self.resources_created["routers"].append(router)

                net = self._create_network({"provider:network_type": "vlan", "apic:svi": True, "apic:bgp_enable": True, "apic:bgp_asn": 1000+i })
                sub = self._create_subnet(net, {"cidr": '192.168.0.0/24'},  None)
                self.resources_created["networks"].append(net)
                net_id = net["network"]["id"]
                self._create_svi_ports(net, sub, "192.168.0", aci_nodes)
                self._add_interface_router(sub.get("subnet"), router.get("router"))
                self.resources_created["interfaces"].append((sub, router))

                port_create_args["mac_address"] = 'fa:16:3e:bc:d5:' + hex_i
                sub_mac1, sp1 = self.crete_port_and_add_trunk(net, port_create_args, trunk1, seg_id=1000 + i)
                port_create_args = {}
                port_create_args.update({"port_security_enabled": "false"})
                port_create_args["mac_address"] = 'fa:16:3e:1b:a1:' + hex_i
                sub_mac2, sp2 = self.crete_port_and_add_trunk(net, port_create_args, trunk2, seg_id=1000 + i)

                print "Creating a single service function chain for customer-" + str(i)
                left = self._create_network({"provider:network_type": "vlan"})
                left_sub = self._create_subnet(left, {"cidr": "1.1.0.0/24", 'host_routes': [{'destination': '10.0.0.0/16', 'nexthop': '1.1.0.1'}]}, None)
                self.resources_created["networks"].append(left)

                right = self._create_network({"provider:network_type": "vlan"})
                right_sub = self._create_subnet(right, {"cidr": "2.2.0.0/24", 'host_routes': [{'destination': '0.0.0.0/1', 'nexthop': '2.2.0.1'}, {'destination': '128.0.0.0/1', 'nexthop': '2.2.0.1'}]}, None)    
                self.resources_created["networks"].append(right)

                self._add_interface_router(left_sub.get("subnet"), router.get("router"))
                self.resources_created["interfaces"].append((left_sub, router))
                self._add_interface_router(right_sub.get("subnet"), router.get("router"))
                self.resources_created["interfaces"].append((right_sub, router))

                port_create_args = {}
                port_create_args.update({"port_security_enabled": "false"})
                pin, pin_id = self.create_port(left, port_create_args)
                pout, pout_id = self.create_port(right, port_create_args)
                self.resources_created["vms"].append(self.boot_vm([pin_id, pout_id], service_image1, flavor, user=True))

                pp = self._create_port_pair(pin, pout)
                ppg = self._create_port_pair_group([pp])
                fc = self._create_flow_classifier('10.0.1.0/24', '8.8.8.0/24', net_id, net_id)
                pc = self._create_port_chain([ppg], [fc])
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

            for i in range(1, int(scale)+1):
                print("Traffic verification from Customer-" + str(i) + " after creating SFC\n")
                self.ping_for_diff_cust('noiro', password, access_router_ip, i, '10.1.1.1')
                self.ping_for_diff_cust('noiro', password, access_router_ip, i, '8.8.8.1')
                self.ping_for_diff_cust('noiro', password, access_router_ip, i, '8.8.8.2')
                self.ping_for_diff_cust('noiro', password, access_router_ip, i, '8.8.8.3')
                self.sleep_between(25, 30)
        except Exception as e:
            raise e
        finally:
            print("Cleaning up ACCESS-ROUTER after traffic verification...")
            command11 = {
                        "interpreter": "/bin/sh",
                        "script_inline": "sudo /usr/local/bin/scale-orchest-access-router.sh -d " + str(scale)
                    }
            self._remote_command_wo_server('noiro', password, access_router_ip, command11)
            self.cleanup(scale)

    def cleanup(self, scale):
        
        self.delete_servers(self.resources_created["vms"])
        self.delete_trunks(self.resources_created["trunks"])
        self.delete_ports(self.resources_created["ports"])
        self.cleanup_sfc()
        for sub, router in self.resources_created["interfaces"]:
            self._admin_remove_interface_router(sub, router)
        for router in self.resources_created["routers"]:
            self._admin_delete_router(router)
        self.delete_network(self.resources_created["networks"])
        for pro in self.resources_created["projects"]:
            self._delete_project(pro)
        for user in self.resources_created["users"]:
            self._delete_user(user)
    
    def ping_for_diff_cust(self, username, password, access_router_ip, n, ping_ip):
        command = {
            "interpreter": "/bin/sh",
            "script_inline": "sudo ip netns exec Customer-" + str(n) + " ping -c 5 %s" %ping_ip
        }
        self._remote_command_wo_server(username, password, access_router_ip, command)
        
