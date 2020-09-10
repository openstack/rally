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
@scenario.configure(name="ScenarioPlugin.sfc_block_traffic", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class SFCBlockTraffic(vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario, scenario.OpenStackScenario):
   
    def run(self, src_cidr, dest_cidr, vm_image, service_image, public_network, flavor, username, password):
        
        public_net = self.clients("neutron").show_network(public_network)
        secgroup = self.context.get("user", {}).get("secgroup")
        key_name=self.context["user"]["keypair"]["name"]

        net1, sub1 = self._create_network_and_subnets({"provider:network_type": "vlan"},{"cidr": src_cidr}, 1, None)
        net2, sub2 = self._create_network_and_subnets({"provider:network_type": "vlan"},{"cidr": dest_cidr}, 1, None)
        left, sub3 = self._create_network_and_subnets({"provider:network_type": "vlan"},{"cidr": "1.1.0.0/24", 'host_routes': [{'destination': src_cidr, 'nexthop': '1.1.0.1'}]}, 1, None)
        right, sub4 = self._create_network_and_subnets({"provider:network_type": "vlan"},{"cidr": "2.2.0.0/24", 'host_routes': [{'destination': '0.0.0.0/1', 'nexthop': '2.2.0.1'}, {'destination': '128.0.0.0/1', 'nexthop': '2.2.0.1'}]}, 1, None)

        router = self._create_router({}, False)
        self._add_interface_router(sub1[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub2[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub3[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub4[0].get("subnet"), router.get("router"))

        net1_id = net1.get('network', {}).get('id')
        net2_id = net2.get('network', {}).get('id')

        port_create_args = {}
        port_create_args["security_groups"] = [secgroup.get('id')]
        p1 = self._create_port(public_net, port_create_args)
        p1_id = p1.get('port', {}).get('id')
        psrc = self._create_port(net1, port_create_args)
        psrc_id = psrc.get('port', {}).get('id')
        nics = [{"port-id": p1_id},{"port-id": psrc_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        src_vm = self._boot_server(vm_image, flavor, False, **kwargs)
        
        pdest = self._create_port(net2, port_create_args)
        pdest_id = pdest.get('port', {}).get('id')
        nics = [{"port-id": pdest_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        dest_vm = self._boot_server(vm_image, flavor, False, **kwargs)
        
        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        pin = self._create_port(left, port_create_args)
        pout = self._create_port(right, port_create_args)
        kwargs = {}
        pin_id = pin.get('port', {}).get('id')
        pout_id = pout.get('port', {}).get('id')
        nics = [{"port-id": pin_id}, {"port-id": pout_id}]
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        service_vm = self._boot_server(service_image, flavor, False, **kwargs)
        self.sleep_between(30, 40)

        fip = p1.get('port', {}).get('fixed_ips')[0].get('ip_address')
        pdest_add = pdest.get('port', {}).get('fixed_ips')[0].get('ip_address')
        command = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ping -c 10 " + pdest_add 
                } 
        
        print "\nTraffic verification before SFC\n"
        self._remote_command(username, password, fip, command, src_vm)

        print "\nCreating a single service function chain...\n"
        try:
            pp = self._create_port_pair(pin, pout)
            ppg = self._create_port_pair_group([pp])
            fc = self._create_flow_classifier(src_cidr, dest_cidr, net1_id, net2_id)
            pc = self._create_port_chain([ppg], [fc])
            self.sleep_between(30, 40)
            
            print "\nTraffic verification after creating SFC\n"
            self._remote_command(username, password, fip, command, src_vm)

            self._delete_port_chain(pc)
            self.sleep_between(30, 40)
            
            print "\nTraffic verification after deleting SFC\n"
            self._remote_command(username, password, fip, command, src_vm)
        except Exception as e:
                print "Exception in service function creation\n", repr(e)
                pass
        finally:
            self.cleanup_sfc()
