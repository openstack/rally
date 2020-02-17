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
@scenario.configure(name="ScenarioPlugin.sfc_multi_parallel", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class SFCMultiParallel(vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario, scenario.OpenStackScenario):

    def run(self, src_cidr, dest_cidr, image, flavor, public_net, username, password):

        public_network = self.clients("neutron").show_network(public_net)        
        secgroup = self.context.get("user", {}).get("secgroup")
        key_name=self.context["user"]["keypair"]["name"]

        net1, sub1 = self._create_network_and_subnets({},{"cidr": src_cidr}, 1, None)
        net2, sub2 = self._create_network_and_subnets({},{"cidr": dest_cidr}, 1, None)
        left1, sub3 = self._create_network_and_subnets({},{"cidr": "1.1.0.0/24", 'host_routes': [{'destination': src_cidr, 'nexthop': '1.1.0.1'}]}, 1, None)
        right1, sub4 = self._create_network_and_subnets({},{"cidr": "2.2.0.0/24", 'host_routes': [{'destination': '0.0.0.0/1', 'nexthop': '2.2.0.1'}, {'destination': '128.0.0.0/1', 'nexthop': '2.2.0.1'}]}, 1, None)
        left2, sub5 = self._create_network_and_subnets({},{"cidr": "3.3.0.0/24", 'host_routes': [{'destination': src_cidr, 'nexthop': '3.3.0.1'}]}, 1, None)
        right2, sub6 = self._create_network_and_subnets({},{"cidr": "4.4.0.0/24", 'host_routes': [{'destination': '0.0.0.0/1', 'nexthop': '4.4.0.1'}, {'destination': '128.0.0.0/1', 'nexthop': '4.4.0.1'}]}, 1, None)
        left3, sub7 = self._create_network_and_subnets({},{"cidr": "5.5.0.0/24", 'host_routes': [{'destination': src_cidr, 'nexthop': '5.5.0.1'}]}, 1, None)
        right3, sub8 = self._create_network_and_subnets({},{"cidr": "6.6.0.0/24", 'host_routes': [{'destination': '0.0.0.0/1', 'nexthop': '6.6.0.1'}, {'destination': '128.0.0.0/1', 'nexthop': '6.6.0.1'}]}, 1, None)


        router = self._create_router({}, False)
        self._add_interface_router(sub1[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub2[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub3[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub4[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub5[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub6[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub7[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub8[0].get("subnet"), router.get("router"))

        net1_id = net1.get('network', {}).get('id')
        net2_id = net2.get('network', {}).get('id')

        port_create_args = {}
        port_create_args["security_groups"] = [secgroup.get('id')]
        p1 = self._create_port(public_network, port_create_args)
        p1_id = p1.get('port', {}).get('id')
        psrc = self._create_port(net1, port_create_args)
        psrc_id = psrc.get('port', {}).get('id')
        nics = [{"port-id": p1_id},{"port-id": psrc_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        src_vm = self._boot_server(image, flavor, False, **kwargs)
        
        pdest = self._create_port(net2, port_create_args)
        pdest_id = pdest.get('port', {}).get('id')
        nics = [{"port-id": pdest_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        dest_vm = self._boot_server(image, flavor, False, **kwargs)
        
        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        pin1 = self._create_port(left1, port_create_args)
        pout1 = self._create_port(right1, port_create_args)
        kwargs = {}
        pin1_id = pin1.get('port', {}).get('id')
        pout1_id = pout1.get('port', {}).get('id')
        nics = [{"port-id": pin1_id}, {"port-id": pout1_id}]
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        service_vm1 = self._boot_server(image, flavor, False, **kwargs)
        
        pin21 = self._create_port(left2, port_create_args)
        pout21 = self._create_port(right2, port_create_args)
        kwargs = {}
        pin21_id = pin21.get('port', {}).get('id')
        pout21_id = pout21.get('port', {}).get('id')
        nics = [{"port-id": pin21_id}, {"port-id": pout21_id}]
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        service_vm21 = self._boot_server(image, flavor, False, **kwargs)

        pin22 = self._create_port(left2, port_create_args)
        pout22 = self._create_port(right2, port_create_args)
        kwargs = {}
        pin22_id = pin22.get('port', {}).get('id')
        pout22_id = pout22.get('port', {}).get('id')
        nics = [{"port-id": pin22_id}, {"port-id": pout22_id}]
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        service_vm22 = self._boot_server(image, flavor, False, **kwargs)

        pin23 = self._create_port(left2, port_create_args)
        pout23 = self._create_port(right2, port_create_args)
        kwargs = {}
        pin23_id = pin23.get('port', {}).get('id')
        pout23_id = pout23.get('port', {}).get('id')
        nics = [{"port-id": pin23_id}, {"port-id": pout23_id}]
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        service_vm23 = self._boot_server(image, flavor, False, **kwargs)

        pin3 = self._create_port(left3, port_create_args)
        pout3 = self._create_port(right3, port_create_args)
        kwargs = {}
        pin3_id = pin3.get('port', {}).get('id')
        pout3_id = pout3.get('port', {}).get('id')
        nics = [{"port-id": pin3_id}, {"port-id": pout3_id}]
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        service_vm3 = self._boot_server(image, flavor, False, **kwargs)
        self.sleep_between(30, 40) 
        
        fip = p1.get('port', {}).get('fixed_ips')[0].get('ip_address')
        pdest_add = pdest.get('port', {}).get('fixed_ips')[0].get('ip_address')
        command = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ping -c 10 " + pdest_add 
                } 
         
        print "\nTraffic verification before SFC\n"
        self._remote_command(username, password, fip, command, src_vm)

        pp1 = self._create_port_pair(pin1, pout1)
        ppg1 = self._create_port_pair_group([pp1])
        pp21 = self._create_port_pair(pin21, pout21)
        pp22 = self._create_port_pair(pin22, pout22)
        pp23 = self._create_port_pair(pin23, pout23)
        ppg2 = self._create_port_pair_group([pp21, pp22, pp23])
        pp3 = self._create_port_pair(pin3, pout3)
        ppg3 = self._create_port_pair_group([pp3])
        fc = self._create_flow_classifier(src_cidr, '0.0.0.0/0', net1_id, net2_id)
        pc = self._create_port_chain([ppg1, ppg2, ppg3], [fc])
        self.sleep_between(50, 60)

        print "\nTraffic verification after creating SFC\n"
        self._remote_command(username, password, fip, command, src_vm)

        self._delete_port_chain(pc)
        self._delete_port_pair_group(ppg1)
        self._delete_port_pair_group(ppg2)
        self._delete_port_pair_group(ppg3)
        self._delete_flow_classifier(fc)
        self._delete_port_pair(pp1)
        self._delete_port_pair(pp21)
        self._delete_port_pair(pp22)
        self._delete_port_pair(pp23)
        self._delete_port_pair(pp3)

