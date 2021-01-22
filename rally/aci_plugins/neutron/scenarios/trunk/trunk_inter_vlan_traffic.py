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
@scenario.configure(name="ScenarioPlugin.trunk_inter_vlan_traffic", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class TrunkIntervlanTraffic(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario,
                            scenario.OpenStackScenario):

    resources_created = {"vms": [], "trunks": []}

    def run(self, cidr1, cidr2, cidr3, image, flavor, public_net, username, password, dualstack, v6cidr1, v6cidr2, v6cidr3):

        try:
            public_network = self.clients("neutron").show_network(public_net)
            secgroup = self.context.get("user", {}).get("secgroup")
            key_name=self.context["user"]["keypair"]["name"]

            net_list, router = self.create_sub_add_to_interfaces_for_trunk(cidr1, cidr2, cidr3, dualstack, v6cidr1, v6cidr2, v6cidr3)

            pf1, pf2, vm_tr1, vm_tr2, trunk1, trunk2, port_create_args = self.create_src_dest_vm(secgroup,
                                                                                                 public_network, net_list[0], net_list[0], image,
                                                                                                 flavor, key_name=key_name, trunk=True)

            self.resources_created["vms"].extend([vm_tr1, vm_tr2])
            self.resources_created["trunks"].extend([trunk1, trunk2])
            
            p1, p1_id = self.create_port(net_list[0], port_create_args)
            vm1 = self.boot_vm(p1_id, image, flavor, key_name=key_name)

            subp1_mac, subp1 = self.crete_port_and_add_trunk(net_list[1], port_create_args, trunk1)
            subp2_mac, subp2 = self.crete_port_and_add_trunk(net_list[1], port_create_args, trunk2)

            p2, p2_id = self.create_port(net_list[1], port_create_args)
            vm2 = self.boot_vm(p2_id, image, flavor, key_name=key_name)

            subp3_mac, subp3 = self.crete_port_and_add_trunk(net_list[2], port_create_args, trunk1, seg_id=20)
            subp4_mac, subp4 = self.crete_port_and_add_trunk(net_list[2], port_create_args, trunk2, seg_id=20)
            
            p3, p3_id = self.create_port(net_list[2], port_create_args)
            vm3 = self.boot_vm(p3_id, image, flavor, key_name=key_name)

            fip1 = pf1.get('port', {}).get('fixed_ips')[0].get('ip_address')
            fip2 = pf2.get('port', {}).get('fixed_ips')[0].get('ip_address')

            command1 = {
                        "interpreter": "/bin/sh",
                        "script_inline": "ip netns add cats;ip link add link eth1 name subp1 type vlan id 10;\
                        ip link set subp1 netns cats;ip netns exec cats ifconfig subp1 hw ether " + subp1_mac + ";\
                        ip netns exec cats udhcpc -i subp1;ip netns add dogs;ip link add link eth1 name subp2 type vlan id 20;\
                        ip link set subp2 netns dogs;ip netns exec dogs ifconfig subp2 hw ether " + subp3_mac + ";\
                        ip netns exec dogs udhcpc -i subp2"
                    }

            command2 = {
                        "interpreter": "/bin/sh",
                        "script_inline": "ip netns add cats;ip link add link eth1 name subp1 type vlan id 10;\
                                ip link set subp1 netns cats;ip netns exec cats ifconfig subp1 hw ether " + subp2_mac + ";\
                                ip netns exec cats udhcpc -i subp1;ip netns add dogs;ip link add link eth1 name subp2 type vlan id 20\
                                ;ip link set subp2 netns dogs;ip netns exec dogs ifconfig subp2 hw ether " + subp4_mac + ";\
                                ip netns exec dogs udhcpc -i subp2"
                    }

            print "\nAdding sub-interfaces into the VMs...\n"
            self._remote_command(username, password, fip1, command1, vm_tr1)
            self._remote_command(username, password, fip2, command2, vm_tr2)
            self.sleep_between(30, 40)
            import pdb;pdb.set_trace() 
            p1_add = p1.get('port', {}).get('fixed_ips')[0].get('ip_address')
            p2_add = p2.get('port', {}).get('fixed_ips')[0].get('ip_address')
            p3_add = p3.get('port', {}).get('fixed_ips')[0].get('ip_address')
            subp1_add = subp1.get('port', {}).get('fixed_ips')[0].get('ip_address')
            subp2_add = subp2.get('port', {}).get('fixed_ips')[0].get('ip_address')
            subp3_add = subp3.get('port', {}).get('fixed_ips')[0].get('ip_address')
            subp4_add = subp4.get('port', {}).get('fixed_ips')[0].get('ip_address')
            if dualstack:
                p1v6_add = p1.get('port', {}).get('fixed_ips')[1].get('ip_address')
                p2v6_add = p2.get('port', {}).get('fixed_ips')[1].get('ip_address')
                p3v6_add = p3.get('port', {}).get('fixed_ips')[1].get('ip_address')
                subp1v6_add = subp1.get('port', {}).get('fixed_ips')[1].get('ip_address')
                subp2v6_add = subp2.get('port', {}).get('fixed_ips')[1].get('ip_address')
                subp3v6_add = subp3.get('port', {}).get('fixed_ips')[1].get('ip_address')
                subp4v6_add = subp4.get('port', {}).get('fixed_ips')[1].get('ip_address')
                command = {
                        "interpreter": "/bin/sh",
                        "script_inline": "ping -c 5 " + p2_add + ";ping6 -c 5 " + p2v6_add + ";ping -c 5 " + p3_add + ";ping6 -c 5 " + p3v6_add + ";\
                                ip netns exec cats ping -c 5 " + p1_add + ";ip netns exec cats ping6 -c 5 " + p1v6_add + ";\
                                ip netns exec dogs ping -c 5 " + p1_add + ";ip netns exec dogs ping6 -c 5 " + p1v6_add + ";\
                                ip netns exec cats ping -c 5 " + subp4_add + ";ip netns exec cats ping6 -c 5 " + subp4v6_add + ";\
                                ip netns exec dogs ping -c 5 " + subp2_add + ";ip netns exec dogs ping6 -c 5 " + subp2v6_add                    }
            else:
                command = {
                            "interpreter": "/bin/sh",
                            "script_inline": "ping -c 5 " + p2_add + ";ping -c 5 " + p3_add + ";ip netns exec cats ping -c 5 " + p1_add + ";\
                                ip netns exec dogs ping -c 5 " + p1_add + ";ip netns exec cats ping -c 5 " + subp4_add + ";\
                                ip netns exec dogs ping -c 5 " + subp2_add
                        }
            
            
            print "\nInter-vlan traffic verification from VM1\n"
            self._remote_command(username, password, fip1, command, vm_tr1)

            if dualstack:
                command = {
                            "interpreter": "/bin/sh",
                            "script_inline": "ping -c 5 " + p2_add + ";ping6 -c 5 " + p2v6_add + ";\
                                    ping -c 5 " + p3_add + ";ping6 -c 5 " + p3v6_add + ";\
                                    ip netns exec cats ping -c 5 " + p1_add + ";ip netns exec cats ping6 -c 5 " + p1v6_add + ";\
                                    ip netns exec dogs ping -c 5 " + p1_add + ";ip netns exec dogs ping6 -c 5 " + p1v6_add + ";\
                                    ip netns exec cats ping -c 5 " + subp3_add + ";ip netns exec cats ping6 -c 5 " + subp3v6_add + ";\
                                    ip netns exec dogs ping -c 10 " + subp1_add +";ip netns exec dogs ping6 -c 10 " + subp1v6_add
                        }
            else:
                command = {
                            "interpreter": "/bin/sh",
                            "script_inline": "ping -c 10 " + p2_add + ";ping -c 10 " + p3_add + ";\
                                    ip netns exec cats ping -c 10 " + p1_add + ";ip netns exec dogs ping -c 10 " + p1_add + ";\
                                    ip netns exec cats ping -c 10 " + subp3_add + ";ip netns exec dogs ping -c 10 " + subp1_add
                        }

            print "\nInter-vlan traffic verification from VM2\n"
            self._remote_command(username, password, fip2, command, vm_tr2)
        except Exception as e:
            raise e 
        finally:
            self.cleanup()

    def cleanup(self):

        self.delete_servers(self.resources_created["vms"])
        self.delete_trunks(self.resources_created["trunks"])

