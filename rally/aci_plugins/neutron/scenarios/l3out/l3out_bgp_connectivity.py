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
@scenario.configure(name="ScenarioPlugin.l3out_bgp_connectivity", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class L3OutBGPConnectivity(vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario, scenario.OpenStackScenario):

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
        
     	print "\nConfiguring the VMs...\n"
        self._remote_command(username, password, fip1, command1, access_vm)
        self._remote_command(username, password, fip2, command2, nat_vm)
        self._remote_command(username, password, fip1, command3, access_vm)
        self._remote_command(username, password, fip2, command4, nat_vm)

        print "\nRunning bird within the VMs...\n"
        command = {
                    "interpreter": "/bin/sh",
                    "script_inline": "bird -c /etc/bird/bird_l3out.conf" 
                }

        self._remote_command(username, password, fip1, command, access_vm)
        self._remote_command(username, password, fip2, command, nat_vm)
        self.sleep_between(30,40)

        print "\nValidating BGP session from ACCESS-VM...\n"
        command = {
                    "interpreter": "/bin/sh",
                    "script_inline": "birdc show protocol;birdc show route" 
                }

        self._remote_command(username, password, fip1, command, access_vm)
        print "\nValidating BGP session from NAT-VM...\n"
        self._remote_command(username, password, fip2, command, nat_vm)

