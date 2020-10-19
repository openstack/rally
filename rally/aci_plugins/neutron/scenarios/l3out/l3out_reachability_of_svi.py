from rally import consts
from rally import exceptions
from rally.common import validation
from rally.aci_plugins import vcpe_utils
from rally.plugins.openstack import scenario
from rally.aci_plugins import create_ostack_resources
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils

@validation.add("required_services", services=[consts.Service.NOVA, consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="ScenarioPlugin.l3out_reachability_of_svi", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")
class L3OutReachabilityofSVI(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario,
                             nova_utils.NovaScenario, scenario.OpenStackScenario):

    def run(self, access_network, nat_network, image, flavor, username, password, access_router_ip, nat_router_ip, router_username):
        
        acc_net = self.clients("neutron").show_network(access_network)
        nat_net = self.clients("neutron").show_network(nat_network)              
        secgroup = self.context.get("user", {}).get("secgroup")
        key_name=self.context["user"]["keypair"]["name"]

        port_create_args = {}
        port_create_args["security_groups"] = [secgroup.get('id')]
        access_vm, nat_vm, fip1, fip2 = self.create_access_vm_nat_vm(acc_net, nat_net, port_create_args,
                                                                      image, flavor, key_name)

        command = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ip link add veth11 type veth peer name veth12;\
                    ip addr add 10.10.251.1/30 dev veth11;ip link set veth11 up"
                }
        print("Configuring the VMs...")
        self._remote_command(username, password, fip1, command, access_vm)
        self._remote_command(username, password, fip2, command, nat_vm)

        print("Verifying the traffic from access-router...")
        command1 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ping -c 10 " + fip1 
                }

        command2 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ping -c 10 " + fip2
                }

        self._remote_command_wo_server(router_username, password, access_router_ip, command1)
        print("Verifying the traffic from nat-router...")
        self._remote_command_wo_server(router_username, password, nat_router_ip, command2)

