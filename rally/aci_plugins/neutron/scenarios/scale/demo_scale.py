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

    def run(self, access_network, nat_network, bras_image, nat_image, service_image1, flavor, username, password, access_router_ip, scale):
         
        acc_net = self.clients("neutron").show_network(access_network)
        nat_net = self.clients("neutron").show_network(nat_network)              
        
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
        dic = []
        for i in range(0, int(scale)):
            dic.append(i)
        dic.append(0)
        for i in range(1, int(scale)+1):
            hex_i = hex(int(i))[2:]
            router = self._create_router({}, False)
            net, sub = self._create_network_and_subnets({"apic:svi": True, "apic:bgp_enable": True, "apic:bgp_asn": 1000+i },{"cidr": '192.168.0.0/24'}, 1, None)
        
            net_id = net.get('network', {}).get('id')
            self._create_svi_ports(net, sub, "192.168.0")
            self._add_interface_router(sub[0].get("subnet"), router.get("router"))
        
            port_create_args["mac_address"] = 'fa:16:3e:bc:d5:' + hex_i
            subp1 = self._create_port(net, port_create_args)
            subp1_id = subp1.get('port', {}).get('id')
            subport_payload = [{"port_id": subp1["port"]["id"],
                                "segmentation_type": "vlan",
                                "segmentation_id": 1000+i}]
            self._admin_add_subports_to_trunk(trunk_bras, subport_payload)
       
            port_create_args = {}
            port_create_args.update({"port_security_enabled": "false"})
            port_create_args["mac_address"] = 'fa:16:3e:1b:a1:' + hex_i
            subp2 = self._create_port(net, port_create_args)
            subp2_id = subp2.get('port', {}).get('id')
            subport_payload = [{"port_id": subp2["port"]["id"],
                                "segmentation_type": "vlan",
                                "segmentation_id": 1000+i}]
            self._admin_add_subports_to_trunk(trunk_nat, subport_payload)

            print "\nCreating a single service function chain for customer-" + str(i)

            left, left_sub = self._create_network_and_subnets({},{"cidr": "1.1.0.0/24", 'host_routes': [{'destination': '10.0.0.0/16', 'nexthop': '1.1.0.1'}]}, 1, None)
            right, right_sub = self._create_network_and_subnets({},{"cidr": "2.2.0.0/24", 'host_routes': [{'destination': '0.0.0.0/1', 'nexthop': '2.2.0.1'}, {'destination': '128.0.0.0/1', 'nexthop': '2.2.0.1'}]}, 1, None)

            self._add_interface_router(left_sub[0].get("subnet"), router.get("router"))
            self._add_interface_router(right_sub[0].get("subnet"), router.get("router"))

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
        
            pp.append(self._create_port_pair(pin, pout))
            ppg.append(self._create_port_pair_group([pp[i-1]]))
            fc.append(self._create_flow_classifier('10.0.1.0/24', '0.0.0.0/0', net_id, net_id))
            pc.append(self._create_port_chain([ppg[i-1]], [fc[i-1]]))
            
            for j in dic:
                if self.context.get("users")[j].get("credential").username == self.context.get("user").get("credential").username :
                    dic.pop(dic.index(j))
                else:
                    self._change_client(j, self.context, None, None)
                    dic.pop(dic.index(j))
                    break
        self.sleep_between(30, 40)

        command2 = {
                    "interpreter": "/bin/sh",
                    "script_file": "/root/.rally/plugins/orchest/orchest_demo_scale_bras.sh"
                }

        command3 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "/usr/local/bin/orchest_demo_scale.sh " + str(scale) + ";/usr/local/bin/scale_run_bird.sh " + str(scale)
                }

        command4 = {
                    "interpreter": "/bin/sh",
                    "script_file": "/root/.rally/plugins/orchest/orchest_demo_scale_nat.sh"
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
        
        for i in range(1, int(scale)+1):
            command7 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo ip netns exec Customer-"+str(i)+" ping -c 5 10.1.1.1;sudo ip netns exec Customer-"+str(i)+" ping -c 5 8.8.8.1;sudo ip netns exec Customer-"+str(i)+" ping -c 5 8.8.8.2;sudo ip netns exec Customer-"+str(i)+" ping -c 5 8.8.8.3"
                }

            print "\nTraffic verification from Customer-"+str(i)+" after creating SFC\n"
            self._remote_command_wo_server('noiro', password, access_router_ip, command7)

        print "\nCleaning up ACCESS-ROUTER after traffic verification...\n"
        command8 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo /usr/local/bin/scale-orchest-access-router.sh -d " + str(scale)
                }

        self._remote_command_wo_server('noiro', password, access_router_ip, command8)
        for i in range(0, int(scale)):
            self._delete_port_chain(pc[i])
            self._delete_flow_classifier(fc[i])
            self._delete_port_pair_group(ppg[i])
            self._delete_port_pair(pp[i])

        self._delete_server(bras_vm)
        self._delete_server(nat_vm)
        self._admin_delete_trunk(trunk_bras)
        self._admin_delete_trunk(trunk_nat)
        self._admin_delete_port(pfip1)
        self._admin_delete_port(pfip2)

