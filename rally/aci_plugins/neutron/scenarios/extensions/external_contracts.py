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
@scenario.configure(name="ScenarioPlugin.external_contracts", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class SVIBGPConnectivity(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario,
                         nova_utils.NovaScenario, scenario.OpenStackScenario):

   def run(self, cidr1, cidr2, image, flavor, public_net, aci_nodes, username, password, apic):
        
          try:
               router = self._create_router({"apic:external_provided_contracts": ["ptest1"], "apic:external_consumed_contracts":["ctest1"]}, False) 

               net1, sub1 = self._create_network_and_subnets({"provider:network_type": "vlan"},{"cidr": cidr1}, 1, None)
               self._add_interface_router(sub1[0].get("subnet"), router.get("router"))
               print("Creating openstack resources...\n")
               self.sleep_between(50,60)
               token = self.get_token(apic, "admin", "noir0123")
               self.sleep_between(5,10)
               fvRsProv_resource = self.get_apic_resource(apic, token, "fvRsProv").json()
               self.sleep_between(5,10)
               external_contracts = fvRsProv_resource['imdata']
               res = []
               for external_contract in external_contracts:
                    res.append(external_contract['fvRsProv']['attributes']['tnVzBrCPName'])
               assert "rtr_"+router['router']['id'] in res, "Resource not created."
               print("rtr_"+router['router']['id']+"\n")
               fvRsCons_resource = self.get_apic_resource(apic, token, "fvRsCons").json()
               self.sleep_between(5,10)
               external_contracts = fvRsCons_resource['imdata']
               res = []
               for external_contract in external_contracts:
                    res.append(external_contract['fvRsCons']['attributes']['tnVzBrCPName'])
               assert "rtr_"+router['router']['id'] in res, "Resource not created."
               print("rtr_"+router['router']['id']+"\n")
          except AssertionError as msg:
               raise msg
