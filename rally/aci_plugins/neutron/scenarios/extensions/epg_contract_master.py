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
@scenario.configure(name="ScenarioPlugin.epg_contract_master", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class SVIBGPConnectivity(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario,
                         nova_utils.NovaScenario, scenario.OpenStackScenario):

   def run(self, cidr1, apic):

          try:
                net, sub = self._create_network_and_subnets({}, {"cidr": cidr1}, 1, None)
                epg_name = 'net_' +  net['network']['id']
                net1, sub1 = self._create_network_and_subnets({"apic:epg_contract_masters": [{'app_profile_name': 'OpenStack','name': epg_name}]}, {"cidr": cidr1}, 1, None)

                self.sleep_between(50, 60)
                token = self.get_token(apic, "admin", "noir0123")
                self.sleep_between(5, 10)
                fvRsSecInherited_resource = self.get_apic_resource(apic, token, "fvRsSecInherited").json()
                self.sleep_between(5,10)
                contract_masters = fvRsSecInherited_resource['imdata']

                for contract_master in contract_masters:
                    res = contract_master['fvRsSecInherited']['attributes']['dn']
                    if 'epg-net_' + net1['network']['id'] in res:
                        assert epg_name in res, "Resource not created."
          except AssertionError as msg:
            raise msg
