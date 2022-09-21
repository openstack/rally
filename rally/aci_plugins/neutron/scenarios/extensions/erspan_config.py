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
@scenario.configure(name="ScenarioPlugin.erspan_config", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class SVIBGPConnectivity(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario,
                         nova_utils.NovaScenario, scenario.OpenStackScenario):

   def run(self, cidr1, cidr2, image, flavor, public_net, aci_nodes, username, password):
        try:
            # router = self._create_router({}, False)
            net1, sub1 = self._create_network_and_subnets({"provider:network_type": "vlan", "apic:nested_domain_name": "dntest1"},{"cidr": cidr1}, 1, None)

            server = self.admin_clients("nova").servers.create(name = "auto-test"+str(int(time.time())),
                                            image = image,
                                            flavor = flavor,
                                            nics = [{'net-id':net1['network']['id']}]
                                            )

            port_list = self.admin_clients("neutron").list_ports()["ports"]
            port1 = {}
            for port in port_list:
                if (port['network_id'] == net1["network"]["id"]):
                    port1 = port

            data = {'port': {'device_owner':'compute:nova'}}
            self.admin_clients("neutron").update_port(port1['id'], data)
            data = {'port': {'apic:erspan_config': [{'dest_ip': '192.168.0.11','direction': 'both','flow_id': 1022}]}}
            self.admin_clients("neutron").update_port(port1['id'], data)
            port_list = self.admin_clients("neutron").list_ports()["ports"]
            port1 = None
            for port in port_list:
                if (port['network_id'] == net1["network"]["id"]):
                    port1 = port
                    assert port['apic:erspan_config'] == [{'dest_ip': '192.168.0.11','direction': 'both','flow_id': 1022}],"Wrong Erspan."
                    print(port['apic:erspan_config'])
                    data = {'port': {'apic:erspan_config': []}}
                    self.admin_clients("neutron").update_port(port1['id'], data)
                    data = {'port': {'device_owner':'network:dhcp'}}
                    self.admin_clients("neutron").update_port(port1['id'], data)
                    self.admin_clients("neutron").delete_port(port['id'])
                    self.admin_clients("nova").servers.delete(server)
                    port1 = None
                    server = None
        except AssertionError as msg:
            raise msg
        finally:
            if server:
                self.clients("nova").servers.delete(server)
            if port1:
                data = {'port': {'apic:erspan_config': []}}
                self.admin_clients("neutron").update_port(port1['id'], data)
                data = {'port': {'device_owner':'network:dhcp'}}
                self.admin_clients("neutron").update_port(port1['id'], data)
                self.admin_clients("neutron").delete_port(port['id'])
