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
@scenario.configure(name="ScenarioPlugin.trunk_scale", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class TrunkScale(vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario, scenario.OpenStackScenario):
   
    def run(self, image, flavor, public_network, username, password, scale):

        public_net = self.clients("neutron").show_network(public_network)
        secgroup = self.context.get("user", {}).get("secgroup")
        key_name=self.context["user"]["keypair"]["name"]

        net0, sub0 = self._create_network_and_subnets({}, {"cidr": '192.168.0.0/24'}, 1, None)
        router = self._create_router({}, False)
        self._add_interface_router(sub0[0].get("subnet"), router.get("router"))

        port_create_args = {}
        port_create_args["security_groups"] = [secgroup.get('id')]
        pf1 = self._create_port(public_net, port_create_args)
        pf1_id = pf1.get('port', {}).get('id')
        pf2 = self._create_port(public_net, port_create_args)
        pf2_id = pf2.get('port', {}).get('id')
        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        ptr1 = self._create_port(net0, port_create_args)
        ptr1_id = ptr1.get('port', {}).get('id')
        trunk_payload = {"port_id": ptr1_id}
        trunk1 = self._create_trunk(trunk_payload)
        nics = [{"port-id": pf1_id}, {"port-id": ptr1_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        vm_tr1 = self._boot_server(image, flavor, False, **kwargs)

        ptr2 = self._create_port(net0, port_create_args)
        ptr2_id = ptr2.get('port', {}).get('id')
        trunk_payload = {"port_id": ptr2_id}
        trunk2 = self._create_trunk(trunk_payload)
        nics = [{"port-id": pf2_id}, {"port-id": ptr2_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        vm_tr2 = self._boot_server(image, flavor, False, **kwargs)

        for i in range(101, 101+int(scale)):
            hex_i = hex(int(i))[2:]
            net, sub = self._create_network_and_subnets({}, {"cidr": "192.168."+str(i)+".0/24"}, 1, None)
            self._add_interface_router(sub[0].get("subnet"), router.get("router"))
            port_create_args = {}
            port_create_args.update({"port_security_enabled": "false"})
            port_create_args.update({"fixed_ips": [{"ip_address": "192.168."+str(i)+".101"}]})
            port_create_args["mac_address"] = 'fa:16:3e:bc:d5:' + hex_i
            subp1 = self._create_port(net, port_create_args)
            subp1_id = subp1.get('port', {}).get('id')
            subport_payload = [{"port_id": subp1["port"]["id"],
                                "segmentation_type": "vlan",
                                "segmentation_id": i}]
            self._add_subports_to_trunk(trunk1, subport_payload)
    
            port_create_args = {}
            port_create_args.update({"port_security_enabled": "false"})
            port_create_args.update({"fixed_ips": [{"ip_address": "192.168."+str(i)+".102"}]})
            port_create_args["mac_address"] = 'fa:16:3e:1b:a1:' + hex_i
            subp2 = self._create_port(net, port_create_args)
            subp2_id = subp2.get('port', {}).get('id')
            subport_payload = [{"port_id": subp2["port"]["id"],
                                "segmentation_type": "vlan",
                                "segmentation_id": i}]
            self._add_subports_to_trunk(trunk2, subport_payload)

        fip1 = pf1.get('port', {}).get('fixed_ips')[0].get('ip_address')
        fip2 = pf2.get('port', {}).get('fixed_ips')[0].get('ip_address')

        command1 = {
                    "interpreter": "/bin/sh",
                    "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/orchest_trunk_scale_vm1.sh"
                }

        command2 = {
                    "interpreter": "/bin/sh",
                    "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/orchest_trunk_scale_vm2.sh"
                }
        
        print "\nAdding sub-interfaces into the VM1...\n"
        self._remote_command(username, password, fip1, command1, vm_tr1)
        print "\nAdding sub-interfaces into the VM2...\n"
        self._remote_command(username, password, fip2, command2, vm_tr2)
        command3 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "/usr/local/bin/orchest_trunk_scale.sh " + str(scale)
                }

        self._remote_command(username, password, fip1, command3, vm_tr1)
        self._remote_command(username, password, fip2, command3, vm_tr2)
        self.sleep_between(30, 40)

        print "\nTraffic verification from VM1\n"
        command4 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "/root/traffic.sh " + str(scale)
                }
        self._remote_command(username, password, fip1, command4, vm_tr1)
        print "\nTraffic verification from VM2\n"
        self._remote_command(username, password, fip2, command4, vm_tr2)

        self._delete_server(vm_tr1)
        self._delete_server(vm_tr2)
        self._delete_trunk(trunk1)
        self._delete_trunk(trunk2)
