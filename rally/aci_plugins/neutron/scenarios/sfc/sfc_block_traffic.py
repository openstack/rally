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
@scenario.configure(name="ScenarioPlugin.sfc_block_traffic", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class SFCBlockTraffic(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario,
                      nova_utils.NovaScenario, scenario.OpenStackScenario):
   
    def run(self, src_cidr, dest_cidr, vm_image, service_image, public_network, flavor, username, password):
        
        public_net = self.clients("neutron").show_network(public_network)
        secgroup = self.context.get("user", {}).get("secgroup")
        key_name=self.context["user"]["keypair"]["name"]

        net_list, sub_list = self.create_net_sub_for_sfc(src_cidr, dest_cidr, dualstack=False)
        router = self._create_router({}, False)
        self.add_interface_to_router(router, sub_list, dualstack)

        net1_id = net_list[0].get('network', {}).get('id')
        net2_id = net_list[1].get('network', {}).get('id')

        port_create_args = {}
        port_create_args["security_groups"] = [secgroup.get('id')]
        p1, p1_id = self.create_port(public_net, port_create_args)
        psrc, psrc_id = self.create_port(net_list[0], port_create_args)
        src_vm = self.boot_vm([p1_id, psrc_id], vm_image, flavor, key_name=key_name)
        pdest, pdest_id = self.create_port(net_list[1], port_create_args)
        dest_vm = self.boot_vm(pdest_id, vm_image, flavor, key_name=key_name)
        
        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        pin, pin_id = self.create_port(net_list[2], port_create_args)
        pout, pout_id = self.create_port(net_list[3], port_create_args)
        service_vm = self.boot_vm([pin_id, pout_id], service_image, flavor, key_name=key_name)

        fip = p1.get('port', {}).get('fixed_ips')[0].get('ip_address')
        pdest_add = pdest.get('port', {}).get('fixed_ips')[0].get('ip_address')
        command = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ping -c 10 " + pdest_add 
                } 

        print "\nTraffic verification before SFC\n"
        self._remote_command(username, password, fip, command, src_vm)
        try:
            print "\nCreating a single service function chain...\n"
            pp = self._create_port_pair(pin, pout)
            ppg = self._create_port_pair_group([pp])
            fc = self._create_flow_classifier(src_cidr, dest_cidr, net1_id, net2_id)
            pc = self._create_port_chain([ppg], [fc])
            self.sleep_between(30, 40)
            
            print "\nTraffic verification after creating SFC\n"
            self._remote_command(username, password, fip, command, src_vm)
            self._delete_port_chain(pc)
            self.sleep_between(30, 40)

            print "Traffic verification after deleting SFC\n"
            self._remote_command(username, password, fip, command, src_vm)
        except Exception as e:
            raise e
        finally:
            self.cleanup_sfc()

