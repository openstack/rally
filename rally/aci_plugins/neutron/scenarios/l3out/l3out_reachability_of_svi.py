from rally import consts
from rally import exceptions
from rally.task import utils
from rally.task import atomic
from rally.task import validation
from rally.common import validation
from rally.aci_plugins import vcpe_utils
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils

@validation.add("required_services", services=[consts.Service.NOVA, consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="ScenarioPlugin.l3out_reachability_of_svi", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class L3OutReachabilityofSVI(vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario, scenario.OpenStackScenario):

    def run(self, access_network, nat_network, image, flavor, username, password):
        
        acc_net = self.clients("neutron").show_network(access_network)
        nat_net = self.clients("neutron").show_network(nat_network)              
        secgroup = self.context.get("user", {}).get("secgroup")
        key_name=self.context["user"]["keypair"]["name"]

        port_create_args = {}
        port_create_args["security_groups"] = [secgroup.get('id')]
        pfip1 = self._create_port(acc_net, port_create_args)
        pfip1_id = pfip1.get('port', {}).get('id')
        nics = [{"port-id": pfip1_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        access_vm = self._boot_server(image, flavor, False, **kwargs)
        
        port_create_args = {}
        port_create_args["security_groups"] = [secgroup.get('id')]
        pfip2 = self._create_port(nat_net, port_create_args)
        pfip2_id = pfip2.get('port', {}).get('id')
        nics = [{"port-id": pfip2_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        kwargs.update({'key_name': key_name})
        nat_vm = self._boot_server(image, flavor, False, **kwargs)
        self.sleep_between(30, 40)

	fip1 = pfip1.get('port', {}).get('fixed_ips')[0].get('ip_address')
        fip2 = pfip2.get('port', {}).get('fixed_ips')[0].get('ip_address')
       
        command = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ip link add veth11 type veth peer name veth12;ip addr add 10.10.251.1/30 dev veth11;ip link set veth11 up" 
                }
 
     	print "\nConfiguring the VMs...\n"
        self._remote_command(username, password, fip1, command, access_vm)
        self._remote_command(username, password, fip2, command, nat_vm)

        print "\nVerifying the traffic from access-router...\n"
        command1 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ping -c 10 " + fip1 
                }

        command2 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "ping -c 10 " + fip2
                }

        self._remote_command_wo_server('noiro', password, '10.108.1.5', command1)
        print "\nVerifying the traffic from nat-router...\n"
        self._remote_command_wo_server('noiro', password, '10.108.1.6', command2)

