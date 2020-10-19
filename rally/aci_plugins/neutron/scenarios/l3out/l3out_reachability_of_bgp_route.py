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
@scenario.configure(name="ScenarioPlugin.l3out_reachability_of_bgp_route", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")
class L3OutReachabilityofBGPRoute(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario,
                                  nova_utils.NovaScenario, scenario.OpenStackScenario):

    resources_created = {"vms": [], "ports": []}

    def run(self, access_network, nat_network, image, flavor, username, password, access_router_ip, nat_router_ip, router_username):
        
        try:
            acc_net = self.clients("neutron").show_network(access_network)
            nat_net = self.clients("neutron").show_network(nat_network)              
            
            port_create_args = {}
            port_create_args.update({"port_security_enabled": "false"})
            pfip1 = self._admin_create_port(acc_net, port_create_args)
            access_vm = self.boot_vm(pfip1.get('port', {}).get('id'), image, flavor, admin=True)
            self.resources_created["vms"].append(access_vm)
            self.resources_created["ports"].append(pfip1)

            pfip2 = self._admin_create_port(nat_net, port_create_args)
            nat_vm = self.boot_vm(pfip2.get('port', {}).get('id'), image, flavor, admin=True)
            self.resources_created["vms"].append(nat_vm)
            self.resources_created["ports"].append(pfip2)
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

            print("Verifying the traffic from ACCESS-VM...")
            command1 = {
                        "interpreter": "/bin/sh",
                        "script_inline": "ping -c 5 10.10.240.1;ping -c 5 10.10.240.2;\
                        ping -c 5 -I 10.10.251.1 10.10.240.1;ping -c 5 -I 10.10.251.1 10.10.240.2"
                    }
            command2 = {
                        "interpreter": "/bin/sh",
                        "script_inline": "ping -c 5 10.10.241.1;ping -c 5 10.10.241.2;\
                        ping -c 5 -I 10.10.251.1 10.10.241.1;ping -c 5 -I 10.10.251.1 10.10.241.2"
                    }

            self._remote_command(username, password, fip1, command1, access_vm)
            print("Verifying the traffic from NAT-VM..")
            self._remote_command(username, password, fip2, command2, nat_vm)

            print("Verifying the traffic from external routers...")
            command = {
                        "interpreter": "/bin/sh",
                        "script_inline": "ping -c 10 10.10.251.1"
                    }
            self._remote_command_wo_server(router_username, password, access_router_ip, command)
            self._remote_command_wo_server(router_username, password, nat_router_ip, command)
        except Exception as e:
            raise e
        finally:
            self.cleanup()

    def cleanup(self):

        self.delete_servers(self.resources_created["vms"])
        self.delete_ports(self.resources_created["ports"])
