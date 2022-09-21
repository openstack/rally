from rally import consts
from rally import exceptions
from rally.common import validation
from rally.aci_plugins import vcpe_utils
from rally.aci_plugins import create_ostack_resources
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils

@validation.add("required_services", services=[consts.Service.NOVA, consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="ScenarioPlugin.nested_allowed_vlans_domain", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class SVIBGPConnectivity(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario,
                         nova_utils.NovaScenario, scenario.OpenStackScenario):

   def run(self, cidr1):

        try:

               net1, sub1 = self._create_network_and_subnets({"apic:nested_domain_name": "dntest1", "apic:nested_domain_type": "dntype1",  "apic:nested_domain_infra_vlan": 1, "apic:nested_domain_service_vlan": 3, "apic:nested_domain_node_network_vlan": 4,"apic:nested_domain_allowed_vlans": {'vlans_list': [2, 3],'vlan_ranges': [{'start': 10, 'end': 12}]}},{"cidr": cidr1}, 1, None)
               net_list = self.admin_clients("neutron").list_networks()
               net = None
               for network in net_list['networks']:
                    if network['id'] == net1['network']['id']:
                         net = network
               assert net["apic:nested_domain_name"] == "dntest1", "Wrong nested_domain_name."
               assert net["apic:nested_domain_type"] == "dntype1", "Wrong nested_domain_type."
               assert net["apic:nested_domain_infra_vlan"] == 1, "Wrong nested_domain_infra_vlan."
               assert net["apic:nested_domain_service_vlan"] == 3, "Wrong nested_domain_service_vlan."
               assert net["apic:nested_domain_node_network_vlan"] == 4, "Wrong nested_domain_node_network_vlan."
               list1 = [10,11,12,2,3]
               assert all(item in net["apic:nested_domain_allowed_vlans"]  for item in list1), "Wrong nested_domain_allowed_vlans."
        except AssertionError as msg:
               raise msg    
