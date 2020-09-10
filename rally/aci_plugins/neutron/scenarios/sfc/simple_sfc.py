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
@scenario.configure(name="ScenarioPlugin.simple_sfc", context={"cleanup@openstack": ["nova", "neutron"]}, platform="openstack")

class SimpleSFC(neutron_utils.NeutronScenario, vcpe_utils.vCPEScenario, nova_utils.NovaScenario, scenario.OpenStackScenario):
    
    def run(self, src_cidr, dest_cidr, image, flavor):
 
        net1, sub1 = self._create_network_and_subnets({"provider:network_type": "vlan"},{"cidr": src_cidr}, 1, None)
        net2, sub2 = self._create_network_and_subnets({"provider:network_type": "vlan"},{"cidr": dest_cidr}, 1, None)
        left, sub3 = self._create_network_and_subnets({"provider:network_type": "vlan"},{'cidr': '1.1.0.0/24', 'host_routes': [{'destination': src_cidr, 'nexthop': '1.1.0.1'}]}, 1, None)
        right, sub4 = self._create_network_and_subnets({"provider:network_type": "vlan"},{"cidr": "2.2.0.0/24", 'host_routes': [{'destination': '0.0.0.0/1', 'nexthop': '2.2.0.1'}]}, 1, None)
        
        router = self._create_router({}, False)
        self._add_interface_router(sub1[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub2[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub3[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub4[0].get("subnet"), router.get("router"))
  
        net1_id = net1.get('network', {}).get('id')
        net2_id = net2.get('network', {}).get('id')
        
        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        psrc = self._create_port(net1, port_create_args)
        p1_id = psrc.get('port', {}).get('id')
        nics = [{"port-id": p1_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        src_vm = self._boot_server(image, flavor, False, **kwargs)

        pdest = self._create_port(net2, port_create_args)
        p2_id = pdest.get('port', {}).get('id')
        nics = [{"port-id": p2_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        dest_vm = self._boot_server(image, flavor, False, **kwargs)

        pin = self._create_port(left, port_create_args)
        pout = self._create_port(right, port_create_args)
        kwargs = {}
        pin_id = pin.get('port', {}).get('id')
        pout_id = pout.get('port', {}).get('id')
        nics = [{"port-id": pin_id}, {"port-id": pout_id}]
        kwargs.update({'nics': nics})
        service_vm = self._boot_server(image, flavor, False, **kwargs)
       
        try:
            pp = self._create_port_pair(pin, pout)
            ppg = self._create_port_pair_group([pp])
            fc = self._create_flow_classifier(src_cidr, dest_cidr, net1_id, net2_id)
            pc = self._create_port_chain([ppg], [fc])
            self.sleep_between(20, 30)
        except Exception as e:
                print "Exception in service function creation\n", repr(e)
                pass
        finally:
            self.cleanup_sfc()
