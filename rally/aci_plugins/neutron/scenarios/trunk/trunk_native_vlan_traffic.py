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
@scenario.configure(name="ScenarioPlugin.trunk_native_vlan_traffic", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class TrunkNativevlanTraffic(vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario, scenario.OpenStackScenario):
   
    def run(self, cidr1, cidr2, cidr3, image, flavor, public_net, username, password):

        public_network = self.clients("neutron").show_network(public_net)
        secgroup = self.context.get("user", {}).get("secgroup")
        key_name=self.context["user"]["keypair"]["name"]

        net1, sub1 = self._create_network_and_subnets({"provider:network_type": "vlan"}, {"cidr": cidr1}, 1, None)
        net2, sub2 = self._create_network_and_subnets({"provider:network_type": "vlan"}, {"cidr": cidr2}, 1, None)
        net3, sub3 = self._create_network_and_subnets({"provider:network_type": "vlan"}, {"cidr": cidr3}, 1, None)

        router = self._create_router({}, False)
        self._add_interface_router(sub1[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub2[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub3[0].get("subnet"), router.get("router"))

        port_create_args = {}
        port_create_args["security_groups"] = [secgroup.get('id')]
        pf1 = self._create_port(public_network, port_create_args)
        pf1_id = pf1.get('port', {}).get('id')
        pf2 = self._create_port(public_network, port_create_args)
        pf2_id = pf2.get('port', {}).get('id')
        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        ptr1 = self._create_port(net1, port_create_args)
        ptr1_id = ptr1.get('port', {}).get('id')
        trunk_payload = {"port_id": ptr1_id}
        trunk1 = self._create_trunk(trunk_payload)
        nics = [{"port-id": pf1_id}, {"port-id": ptr1_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        vm_tr1 = self._boot_server(image, flavor, False, **kwargs)

        ptr2 = self._create_port(net1, port_create_args)
        ptr2_id = ptr2.get('port', {}).get('id')
        trunk_payload = {"port_id": ptr2_id}
        trunk2 = self._create_trunk(trunk_payload)
        nics = [{"port-id": pf2_id}, {"port-id": ptr2_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        vm_tr2 = self._boot_server(image, flavor, False, **kwargs)

        p1 = self._create_port(net1, port_create_args)
        p1_id = p1.get('port', {}).get('id')
        nics = [{"port-id": p1_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        vm1 = self._boot_server(image, flavor, False, **kwargs)

        subp1 = self._create_port(net2, port_create_args)
        subp1_id = subp1.get('port', {}).get('id')
        subport_payload = [{"port_id": subp1["port"]["id"],
                                "segmentation_type": "vlan",
                                "segmentation_id": '10'}]
        self._add_subports_to_trunk(trunk1, subport_payload)
        
        subp2 = self._create_port(net2, port_create_args)
        subp2_id = subp2.get('port', {}).get('id')
        subport_payload = [{"port_id": subp2["port"]["id"],
                                "segmentation_type": "vlan",
                                "segmentation_id": '10'}]
        self._add_subports_to_trunk(trunk2, subport_payload)

        p2 = self._create_port(net2, port_create_args)
        p2_id = p2.get('port', {}).get('id')
        nics = [{"port-id": p2_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        vm2 = self._boot_server(image, flavor, False, **kwargs)
        
        subp3 = self._create_port(net3, port_create_args)
        subp3_id = subp3.get('port', {}).get('id')
        nics = [{"port-id": subp3_id}]
        subport_payload = [{"port_id": subp3["port"]["id"],
                                "segmentation_type": "vlan",
                                "segmentation_id": '20'}]
        self._add_subports_to_trunk(trunk1, subport_payload)

        subp4 = self._create_port(net3, port_create_args)
        subp4_id = subp4.get('port', {}).get('id')
        nics = [{"port-id": subp4_id}]
        subport_payload = [{"port_id": subp4["port"]["id"],
                                "segmentation_type": "vlan",
                                "segmentation_id": '20'}]
        self._add_subports_to_trunk(trunk2, subport_payload)

        p3 = self._create_port(net3, port_create_args)
        p3_id = p3.get('port', {}).get('id')
        nics = [{"port-id": p3_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        vm3 = self._boot_server(image, flavor, False, **kwargs)
        self.sleep_between(30, 40)
        
        fip1 = pf1.get('port', {}).get('fixed_ips')[0].get('ip_address')
        fip2 = pf2.get('port', {}).get('fixed_ips')[0].get('ip_address')
        subp1_mac = subp1.get('port', {}).get('mac_address')
        subp2_mac = subp2.get('port', {}).get('mac_address')
        subp3_mac = subp3.get('port', {}).get('mac_address')
        subp4_mac = subp4.get('port', {}).get('mac_address')

        command1 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ip netns add cats;ip link add link eth1 name subp1 type vlan id 10;ip link set subp1 netns cats;ip netns exec cats ifconfig subp1 hw ether " + subp1_mac + ";ip netns exec cats udhcpc -i subp1;ip netns add dogs;ip link add link eth1 name subp2 type vlan id 20;ip link set subp2 netns dogs;ip netns exec dogs ifconfig subp2 hw ether " + subp3_mac + ";ip netns exec dogs udhcpc -i subp2"
                }

        command2 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ip netns add cats;ip link add link eth1 name subp1 type vlan id 10;ip link set subp1 netns cats;ip netns exec cats ifconfig subp1 hw ether " + subp2_mac + ";ip netns exec cats udhcpc -i subp1;ip netns add dogs;ip link add link eth1 name subp2 type vlan id 20;ip link set subp2 netns dogs;ip netns exec dogs ifconfig subp2 hw ether " + subp4_mac + ";ip netns exec dogs udhcpc -i subp2"
                }

        print "\nAdding sub-interfaces into the VMs...\n"
        self._remote_command(username, password, fip1, command1, vm_tr1)
        self._remote_command(username, password, fip2, command2, vm_tr2)
        self.sleep_between(30, 40)
        
        p1_add = p1.get('port', {}).get('fixed_ips')[0].get('ip_address')

        command = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ping -c 10 " + p1_add
                    }
        
        print "\nTraffic verification from VM1 default namespace\n"
        self._remote_command(username, password, fip1, command, vm_tr1)
        print "\nTraffic verification from VM2 default namespace\n"
        self._remote_command(username, password, fip2, command, vm_tr2)
        
        self._delete_server(vm_tr1)
        self._delete_server(vm_tr2)
        self._delete_trunk(trunk1)
        self._delete_trunk(trunk2)
