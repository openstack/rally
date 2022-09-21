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
@scenario.configure(name="ScenarioPlugin.extra_contracts", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class SVIBGPConnectivity(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario,
                         nova_utils.NovaScenario, scenario.OpenStackScenario):

   def run(self, cidr1, cidr2, image, flavor, public_net, aci_nodes, username, password, apic):

          try:
               net1, sub1 = self._create_network_and_subnets({"provider:network_type": "vlan", "apic:extra_provided_contracts": ["pcontest1"], "apic:extra_consumed_contracts":["contest1"]},{"cidr": cidr1}, 1, None)

               self.sleep_between(50,60)
               token = self.get_token(apic, "admin", "noir0123")
               self.sleep_between(5,10)
               fvRsProv_resource = self.get_apic_resource(apic, token, "fvRsProv").json()
               self.sleep_between(5,10)
               extra_contracts = fvRsProv_resource['imdata']
               res = []
               for extra_contract in extra_contracts:
                    res.append(extra_contract['fvRsProv']['attributes']['tnVzBrCPName'])
               assert "pcontest1" in res, "Resource not getting created."
               print("pcontest1")
               
               fvRsCons_resource = self.get_apic_resource(apic, token, "fvRsCons").json()
               self.sleep_between(5,10)
               extra_contracts = fvRsCons_resource['imdata']
               res = []
               for extra_contract in extra_contracts:
                    res.append(extra_contract['fvRsCons']['attributes']['tnVzBrCPName'])
               assert "contest1" in res, "Resource not created."
               print("contest1")
          except AssertionError as msg:
               raise msg
