from rally import consts
from rally import exceptions
from rally.common import validation
from rally.aci_plugins import vcpe_utils
from rally.aci_plugins import create_ostack_resources
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils
import time

@validation.add("required_services", services=[consts.Service.NOVA, consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="ScenarioPlugin.address_scope", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class SVIBGPConnectivity(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario,
                         nova_utils.NovaScenario, scenario.OpenStackScenario):

   def run(self, cidr1):

        try:
            net1, sub1 = self._create_network_and_subnets({},{"cidr": cidr1}, 1, None)
            address_scope_name = "auto-test"+str(int(time.time()))
            self.create_address_scope(address_scope_name,4)
            address_scope_list = self.clients("neutron").list_address_scopes()["address_scopes"]
            address_scope=None
            for address_scope in address_scope_list:
                if(address_scope['name'] == address_scope_name):
                    assert address_scope["apic:synchronization_state"]=="synced","Wrong synchronization state."
                    print(address_scope["apic:distinguished_names"])
                    self.clients("neutron").delete_address_scope(address_scope['id'])
                    address_scope=None
                    break
        except AssertionError as msg:
            raise msg
        finally:
            if address_scope:
                self.clients("neutron").delete_address_scope(address_scope['id'])
