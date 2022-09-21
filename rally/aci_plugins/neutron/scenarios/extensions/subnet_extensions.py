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
@scenario.configure(name="ScenarioPlugin.subnet_extensions", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class SVIBGPConnectivity(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario,
                         nova_utils.NovaScenario, scenario.OpenStackScenario):

   def run(self, cidr1, cidr2, image, flavor, public_net, aci_nodes, username, password, apic):

          try:
              net1, sub1 = self._create_network_and_subnets({"provider:network_type": "vlan"},{"cidr": cidr1, "apic:active_active_aap": True, "apic:snat_host_pool": True}, 1, None)
              server = None
              server = self.admin_clients("nova").servers.create(name = "auto-test"+str(int(time.time())),
                                          image = image,
                                          flavor = flavor,
                                          nics = [{'net-id':net1['network']['id']}]
                                          )
              subnet_list = self.admin_clients("neutron").list_subnets()
              for subnet in subnet_list['subnets']:
                     if subnet['id'] == sub1[0]['subnet']['id']:
                            assert subnet['apic:active_active_aap'] , "Active active app not working"
                            assert subnet['apic:snat_host_pool'] , "snat host pool not working"
                            self.admin_clients("nova").servers.delete(server)
                            server = None
          except AssertionError as msg:
              raise msg
          finally:
              if server:
                     self.admin_clients("nova").servers.delete(server)
