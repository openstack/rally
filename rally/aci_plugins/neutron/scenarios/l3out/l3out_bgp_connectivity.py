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
@scenario.configure(name="ScenarioPlugin.l3out_bgp_connectivity", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")
class L3OutBGPConnectivity(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario,
                           nova_utils.NovaScenario, scenario.OpenStackScenario):

    def run(self, access_network, nat_network, image, flavor, username, password):
        
        acc_net = self.clients("neutron").show_network(access_network)
        nat_net = self.clients("neutron").show_network(nat_network)              
        secgroup = self.context.get("user", {}).get("secgroup")
        key_name = self.context["user"]["keypair"]["name"]
        
        port_create_args = {}
        port_create_args["security_groups"] = [secgroup.get('id')]
        
        access_vm, nat_vm, fip1, fip2 = self.create_access_vm_nat_vm(acc_net, nat_net, port_create_args,
                                                                     image, flavor, key_name)
        command1 = {
                    "interpreter": "/bin/sh",
                    "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/l3out_orchest_access.sh" 
                }

        command2 = {
                    "interpreter": "/bin/sh",
                    "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/l3out_orchest_nat.sh"
                }
 
        command3 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "chmod +x /root/create_bird.sh;/root/create_bird.sh " + fip1
                }

        command4 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "chmod +x /root/create_bird.sh;/root/create_bird.sh " + fip2
                }
        print("Configuring the VMs...")
        self._remote_command(username, password, fip1, command1, access_vm)
        self._remote_command(username, password, fip2, command2, nat_vm)
        self._remote_command(username, password, fip1, command3, access_vm)
        self._remote_command(username, password, fip2, command4, nat_vm)

        print("Running bird within the VMs...")
        command = {
                    "interpreter": "/bin/sh",
                    "script_inline": "bird -c /etc/bird/bird_l3out.conf" 
                }

        self._remote_command(username, password, fip1, command, access_vm)
        self._remote_command(username, password, fip2, command, nat_vm)
        self.sleep_between(30,40)

        print("Validating BGP session from ACCESS-VM...")
        command = {
                    "interpreter": "/bin/sh",
                    "script_inline": "birdc show protocol;birdc show route" 
                }

        self._remote_command(username, password, fip1, command, access_vm)
        print("Validating BGP session from NAT-VM...")
        self._remote_command(username, password, fip2, command, nat_vm)

