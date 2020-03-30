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
@scenario.configure(name="ScenarioPlugin.sfc_single_parallel", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class SFCSingleParallel(vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario, scenario.OpenStackScenario):

    def run(self, src_cidr, dest_cidr, vm_image, service_image1, flavor, public_network, username, password):
        
        public_net = self.clients("neutron").show_network(public_network)  
        secgroup = self.context.get("user", {}).get("secgroup")
        key_name=self.context["user"]["keypair"]["name"]

        net1, sub1 = self._create_network_and_subnets({},{"cidr": src_cidr}, 1, None)
        net2, sub2 = self._create_network_and_subnets({},{"cidr": dest_cidr}, 1, None)
        left, sub3 = self._create_network_and_subnets({},{"cidr": "1.1.0.0/24", 'host_routes': [{'destination': src_cidr, 'nexthop': '1.1.0.1'}]}, 1, None)
        right, sub4 = self._create_network_and_subnets({},{"cidr": "2.2.0.0/24", 'host_routes': [{'destination': '0.0.0.0/1', 'nexthop': '2.2.0.1'}, {'destination': '128.0.0.0/1', 'nexthop': '2.2.0.1'}]}, 1, None)

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
        p2 = self._create_port(public_net, port_create_args)
        p2_id = p2.get('port', {}).get('id')
        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        psrc = self._create_port(net1, port_create_args)
        psrc_id = psrc.get('port', {}).get('id')
        nics = [{"port-id": p1_id},{"port-id": psrc_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        src_vm = self._boot_server(vm_image, flavor, False, **kwargs)
        
        pdest = self._create_port(net2, port_create_args)
        pdest_id = pdest.get('port', {}).get('id')
        nics = [{"port-id": p2_id},{"port-id": pdest_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        dest_vm = self._boot_server(vm_image, flavor, False, **kwargs)
         
        pin1 = self._create_port(left, port_create_args)
        pout1 = self._create_port(right, port_create_args)
        kwargs = {}
        pin1_id = pin1.get('port', {}).get('id')
        pout1_id = pout1.get('port', {}).get('id')
        nics = [{"port-id": pin1_id}, {"port-id": pout1_id}]
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        service_vm11 = self._boot_server(service_image1, flavor, False, **kwargs)
        
        pin2 = self._create_port(left, port_create_args)
        pout2 = self._create_port(right, port_create_args)
        kwargs = {}
        pin2_id = pin2.get('port', {}).get('id')
        pout2_id = pout2.get('port', {}).get('id')
        nics = [{"port-id": pin2_id}, {"port-id": pout2_id}]
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        service_vm12 = self._boot_server(service_image1, flavor, False, **kwargs)
        
        pin3 = self._create_port(left, port_create_args)
        pout3 = self._create_port(right, port_create_args)
        kwargs = {}
        pin3_id = pin3.get('port', {}).get('id')
        pout3_id = pout3.get('port', {}).get('id')
        nics = [{"port-id": pin3_id}, {"port-id": pout3_id}]
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        service_vm13 = self._boot_server(service_image1, flavor, False, **kwargs)
        self.sleep_between(30, 40) 
        
        fip1 = p1.get('port', {}).get('fixed_ips')[0].get('ip_address')
        fip2 = p2.get('port', {}).get('fixed_ips')[0].get('ip_address')

        print "\nConfiguring destination-vm for traffic verification..\n"
        command1 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ip address add 192.168.200.101/24 dev eth1;ip address add 192.168.200.102/24 dev eth1;ip address add 192.168.200.103/24 dev eth1;route add default gw 192.168.200.1 eth1"
                }
        self._remote_command(username, password, fip2, command1, dest_vm)

        command2 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ping -c 5 192.168.200.101;ping -c 5 192.168.200.102;ping -c 5 192.168.200.103"
                }
         
        print "\nTraffic verification before SFC\n"
        self._remote_command(username, password, fip1, command2, src_vm)
        
        print "\nCreating a parallel service function chain...\n"
        pp1 = self._create_port_pair(pin1, pout1)
        pp2 = self._create_port_pair(pin2, pout2)
        pp3 = self._create_port_pair(pin3, pout3)
        ppg = self._create_port_pair_group([pp1, pp2, pp3])
        fc = self._create_flow_classifier(src_cidr, dest_cidr, net1_id, net2_id)
        pc = self._create_port_chain([ppg], [fc])
        self.sleep_between(30, 40)

        print "\nTraffic verification after creating SFC\n"
        self._remote_command(username, password, fip1, command2, src_vm)

        self._delete_port_chain(pc)
        self._delete_port_pair_group(ppg)
        self._delete_flow_classifier(fc)
        self._delete_port_pair(pp1)
        self._delete_port_pair(pp2)
        self._delete_port_pair(pp3)