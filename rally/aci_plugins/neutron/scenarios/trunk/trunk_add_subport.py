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
@scenario.configure(name="ScenarioPlugin.trunk_add_subport", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class TrunkAddSubport(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario,
                      scenario.OpenStackScenario):

    resources_created = {"vms": [], "trunks": []}

    def run(self, cidr1, cidr2, cidr3, image, flavor, public_net, username, password, dualstack, v6cidr1, v6cidr2, v6cidr3):

        try:
            public_network = self.clients("neutron").show_network(public_net)
            secgroup = self.context.get("user", {}).get("secgroup")
            key_name=self.context["user"]["keypair"]["name"]

            net_list, router = self.create_sub_add_to_interfaces_for_trunk(cidr1, cidr2, cidr3, dualstack, v6cidr1, v6cidr2, v6cidr3)

            port_create_args = {}
            port_create_args["security_groups"] = [secgroup.get('id')]
            p0, p0_id = self.create_port(public_network, port_create_args)
            port_create_args = {}
            port_create_args.update({"port_security_enabled": "false"})
            ptr, ptr_id = self.create_port(net_list[0], port_create_args)
            trunk_payload = {"port_id": ptr_id}
            trunk = self._create_trunk(trunk_payload)
            vm_tr = self.boot_vm([p0_id, ptr_id], image, flavor, key_name=key_name)
            self.resources_created["vms"].append(vm_tr)
            self.resources_created["trunks"].append(trunk)

            p1, p1_id = self.create_port(net_list[0], port_create_args)
            vm1 = self.boot_vm(p1_id, image, flavor, key_name=key_name)
            subp1_mac, sp1 = self.crete_port_and_add_trunk(net_list[1], port_create_args, trunk)
            
            p2, p2_id = self.create_port(net_list[1], port_create_args)
            vm2 = self.boot_vm(p2_id, image, flavor, key_name=key_name)

            p3, p3_id = self.create_port(net_list[2], port_create_args)
            vm3 = self.boot_vm(p3_id, image, flavor, key_name=key_name)
            self.sleep_between(30, 40)
            
            fip = p0.get('port', {}).get('fixed_ips')[0].get('ip_address')

            command = {
                        "interpreter": "/bin/sh",
                        "script_inline": "ip netns add cats;ip link add link eth1 name subp1 type vlan id 10;\
                                ip link set subp1 netns cats;ip netns exec cats ifconfig subp1 hw ether " + subp1_mac + ";\
                                ip netns exec cats udhcpc -i subp1"
                    }

            self._remote_command(username, password, fip, command, vm1)
            self.sleep_between(30, 40)
            
            p1_add = p1.get('port', {}).get('fixed_ips')[0].get('ip_address')
            p2_add = p2.get('port', {}).get('fixed_ips')[0].get('ip_address')
            p3_add = p3.get('port', {}).get('fixed_ips')[0].get('ip_address')

            if dualstack:
                p1v6_add = p1.get('port', {}).get('fixed_ips')[1].get('ip_address')
                p2v6_add = p2.get('port', {}).get('fixed_ips')[1].get('ip_address')
                p3v6_add = p3.get('port', {}).get('fixed_ips')[1].get('ip_address')
                command1 = {
                            "interpreter": "/bin/sh",
                            "script_inline": "ping -c 5 " + p1_add + ";ping6 -c 5 " + p1v6_add + ";ip netns exec cats ping -c 5 " + p2_add + ";\
                            ip netns exec cats ping6 -c 5 " + p2v6_add + ";ip netns exec dogs ping -c 5 " + p3_add +";ip netns exec dogs ping6 -c 5 " + p3v6_add
                        }
            else:
                command1 = {
                            "interpreter": "/bin/sh",
                            "script_inline": "ping -c 5 " + p1_add + ";ip netns exec cats ping -c 5 " + p2_add + ";\
                            ip netns exec dogs ping -c 5 " + p3_add
                        }

            print "\nVerify traffic between the networks through trunk\n"
            self._remote_command(username, password, fip, command1, vm1)

            print "\nAdding a new subport into the trunk...\n"
            subp2_mac, sp2 = self.crete_port_and_add_trunk(net_list[2], port_create_args, trunk, seg_id=20)
            
            command = {
                        "interpreter": "/bin/sh",
                        "script_inline": "ip netns add dogs;ip link add link eth1 name subp2 type vlan id 20;\
                        ip link set subp2 netns dogs;ip netns exec dogs ifconfig subp2 hw ether " + subp2_mac + ";\
                        ip netns exec dogs udhcpc -i subp2"
                    }
            self._remote_command(username, password, fip, command, vm1)

            print "\nVerify traffic to the new vlan through trunk\n"
            self._remote_command(username, password, fip, command1, vm1)
        except Exception as e:
            raise e
        finally:
            self.cleanup()

    def cleanup(self):

        self.delete_servers(self.resources_created["vms"])
        self.delete_trunks(self.resources_created["trunks"])
       
