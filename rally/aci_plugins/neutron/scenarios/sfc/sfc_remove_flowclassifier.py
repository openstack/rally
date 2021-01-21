from rally import consts
from rally.common import validation
from rally.aci_plugins import vcpe_utils
from rally.aci_plugins import create_ostack_resources
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils

@validation.add("required_services", services=[consts.Service.NOVA, consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="ScenarioPlugin.sfc_remove_flowclassifier", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class SFCRemoveFlowclassifier(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario,
                              nova_utils.NovaScenario, scenario.OpenStackScenario):

    def run(self, src_cidr, dest_cidr, vm_image, service_image1, flavor, public_network, username, password,
            ipv6_cidr, ipv6_dest_cidr, dualstack):
        
        public_net = self.clients("neutron").show_network(public_network)
        secgroup = self.context.get("user", {}).get("secgroup")
        key_name=self.context["user"]["keypair"]["name"]
        
        #net_list, sub_list = self.create_net_sub_for_sfc(src_cidr, dest_cidr)
        net_list, sub_list = self.create_net_sub_for_sfc(src_cidr, dest_cidr, dualstack=dualstack,
                                                         ipv6_src_cidr=ipv6_cidr, ipv6_dest_cidr=ipv6_dest_cidr)
        test_net, sub5 = self._create_network_and_subnets({"provider:network_type": "vlan"},{"cidr": '192.168.0.0/24'}, 1, None)

        router = self._create_router({}, False)
        #self.add_interface_to_router(router, sub_list)
        self.add_interface_to_router(router, sub_list, dualstack)
        self._add_interface_router(sub5[0].get("subnet"), router.get("router"))

        net1_id = net_list[0].get('network', {}).get('id')
        net2_id = net_list[1].get('network', {}).get('id')
        testnet_id = test_net.get('network', {}).get('id')

        p1, p2, src_vm, dest_vm  = self.create_vms_for_sfc_test(secgroup, public_net, net_list[0], net_list[1],
                                                           vm_image, flavor, key_name)
        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        pin, pin_id = self.create_port(net_list[2], port_create_args)
        pout, pout_id = self.create_port(net_list[3], port_create_args)
        service_vm1 = self.boot_vm([pin_id, pout_id], service_image1, flavor, key_name=key_name)

        fip1 = p1.get('port', {}).get('fixed_ips')[0].get('ip_address')
        fip2 = p2.get('port', {}).get('fixed_ips')[0].get('ip_address')

        print "\nConfiguring destination-vm for traffic verification..\n"
        if dualstack:
            command1 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ip address add 192.168.200.101/24 dev eth1;ip address add 192.168.200.102/24 dev eth1;\
                    ip address add 192.168.200.103/24 dev eth1;route add default gw 192.168.200.1 eth1; \
                    ip -6 addr add  2001:d8::101/32 dev eth1; ip -6 addr add 2001:d8::102/32 dev eth1; \
                    ip -6 addr add 2001:d8::103/32 dev eth1; ip -6 route add 2001:d8::1 dev eth1"
                    }
            command2 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ping -c 5 192.168.200.101;ping -c 5 192.168.200.102;ping -c 5 192.168.200.103; \
                    ping6 -c 5 2001:d8::101;ping6 -c 5 2001:d8::102;ping6 -c 5 2001:d8::103"
                }

        else:
            command1 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ip address add 192.168.200.101/24 dev eth1;ip address add 192.168.200.102/24 dev eth1;\
                    ip address add 192.168.200.103/24 dev eth1;route add default gw 192.168.200.1 eth1"
                }
            command2 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ping -c 5 192.168.200.101;ping -c 5 192.168.200.102;ping -c 5 192.168.200.103"
                }

        self._remote_command(username, password, fip2, command1, dest_vm)
        try:
            pp = self._create_port_pair(pin, pout)
            ppg = self._create_port_pair_group([pp])
            fc1 = self._create_flow_classifier(src_cidr, '192.168.0.0/24', net1_id, testnet_id)
            fc2 = self._create_flow_classifier(src_cidr, dest_cidr, net1_id, net2_id)
            pc = self._create_port_chain([ppg], [fc1, fc2])
            self.sleep_between(30, 40)

            print"Traffic verification with multiple flow classifiers"
            self._remote_command(username, password, fip1, command2, src_vm)

            print"Removing a flow classifier from the chain..."
            self._update_port_chain(pc, [ppg], [fc1])
            self.sleep_between(30, 40)

            print"Traffic verification after removing a flow classifier\n"
            self._remote_command(username, password, fip1, command2, src_vm)
        except Exception as e:
            raise e
        finally:
            self.cleanup_sfc()

