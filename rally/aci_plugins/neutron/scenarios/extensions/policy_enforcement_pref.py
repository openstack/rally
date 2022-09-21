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
@scenario.configure(name="ScenarioPlugin.policy_enforcement_pref", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class SVIBGPConnectivity(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario,
                         nova_utils.NovaScenario, scenario.OpenStackScenario):

   def run(self, cidr1, apic):

          try:
               net1, sub1 = self._create_network_and_subnets({"apic:policy_enforcement_pref": "enforced"},{"cidr": cidr1}, 1, None)
               net_id = net1['network']['id']
               net_id = "net_"+net_id
               self.sleep_between(50,60)
               token = self.get_token(apic, "admin", "noir0123")
               self.sleep_between(5,10)
               fvRsProv_resource = self.get_apic_resource(apic, token, "fvAEPg").json()
               self.sleep_between(5,10)
               policy_enforcements = fvRsProv_resource['imdata']
               res = []
               names = []
               for policy_enforcement in policy_enforcements:
                    res.append(policy_enforcement['fvAEPg']['attributes']['pcEnfPref'])
                    names.append(policy_enforcement['fvAEPg']['attributes']['name'])
               assert net_id in names and "enforced" in res, "Resource not created."
               print("enforced")
          except AssertionError as msg:
               raise msg
