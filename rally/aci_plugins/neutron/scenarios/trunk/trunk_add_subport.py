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
@scenario.configure(name="ScenarioPlugin.trunk_add_subport", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class TrunkAddSubport(vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario, scenario.OpenStackScenario):
   
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
        p0 = self._create_port(public_network, port_create_args)
        p0_id = p0.get('port', {}).get('id')
        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        ptr = self._create_port(net1, port_create_args)
        ptr_id = ptr.get('port', {}).get('id')
        trunk_payload = {"port_id": ptr_id}
        trunk = self._create_trunk(trunk_payload)
        nics = [{"port-id": p0_id}, {"port-id": ptr_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        vm_tr = self._boot_server(image, flavor, False, **kwargs)

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
        self._add_subports_to_trunk(trunk, subport_payload)
        
        p2 = self._create_port(net2, port_create_args)
        p2_id = p2.get('port', {}).get('id')
        nics = [{"port-id": p2_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        vm2 = self._boot_server(image, flavor, False, **kwargs) 

        p3 = self._create_port(net3, port_create_args)
        p3_id = p3.get('port', {}).get('id')
        nics = [{"port-id": p3_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        vm3 = self._boot_server(image, flavor, False, **kwargs)
        self.sleep_between(30, 40)
        
        fip = p0.get('port', {}).get('fixed_ips')[0].get('ip_address')
        subp1_mac = subp1.get('port', {}).get('mac_address')

        command = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ip netns add cats;ip link add link eth1 name subp1 type vlan id 10;ip link set subp1 netns cats;ip netns exec cats ifconfig subp1 hw ether " + subp1_mac + ";ip netns exec cats udhcpc -i subp1"
                }

        self._remote_command(username, password, fip, command, vm1)
        self.sleep_between(30, 40)
        
        p1_add = p1.get('port', {}).get('fixed_ips')[0].get('ip_address')
        p2_add = p2.get('port', {}).get('fixed_ips')[0].get('ip_address')
        p3_add = p3.get('port', {}).get('fixed_ips')[0].get('ip_address')

        command1 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ping -c 10 " + p1_add + ";ip netns exec cats ping -c 10 " + p2_add + ";ip netns exec dogs ping -c 10 " + p3_add
                }

        print "\nVerify traffic between the networks through trunk\n"
        self._remote_command(username, password, fip, command1, vm1)

        print "\nAdding a new subport into the trunk...\n"
        subp2 = self._create_port(net3, port_create_args)
        subp2_id = subp2.get('port', {}).get('id')
        nics = [{"port-id": subp2_id}]
        subport_payload = [{"port_id": subp2["port"]["id"],
                                "segmentation_type": "vlan",
                                "segmentation_id": '20'}]
        self._add_subports_to_trunk(trunk, subport_payload)
        subp2_mac = subp2.get('port', {}).get('mac_address')
        
        command = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ip netns add dogs;ip link add link eth1 name subp2 type vlan id 20;ip link set subp2 netns dogs;ip netns exec dogs ifconfig subp2 hw ether " + subp2_mac + ";ip netns exec dogs udhcpc -i subp2"
                }
        self._remote_command(username, password, fip, command, vm1)

        print "\nVerify traffic to the new vlan through trunk\n"
        self._remote_command(username, password, fip, command1, vm1)

        self._delete_server(vm_tr)
        self._delete_trunk(trunk)

