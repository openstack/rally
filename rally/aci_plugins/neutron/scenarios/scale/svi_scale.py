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
@scenario.configure(name="ScenarioPlugin.svi_scale", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class SVIScale(vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario, scenario.OpenStackScenario):

    def run(self, image, flavor, public_network, aci_nodes, username, password, scale):
        
        router = self._create_router({}, False)
        public_net = self.clients("neutron").show_network(public_network)     
        secgroup = self.context.get("user", {}).get("secgroup")
        key_name=self.context["user"]["keypair"]["name"]

        fip = []
        vm = []
        for i in range(101, 101+int(scale)):

            port_create_args = {}
            port_create_args["security_groups"] = [secgroup.get('id')]
            pfip = self._create_port(public_net, port_create_args)
            pfip_id = pfip.get('port', {}).get('id')
            fip.append(pfip.get('port', {}).get('fixed_ips')[0].get('ip_address'))

            net, sub = self._create_network_and_subnets({"provider:network_type": "vlan", "apic:svi": True, "apic:bgp_enable": True, "apic:bgp_asn": i},{"cidr": "192.168."+str(i)+".0/24"}, 1, None)
            self._create_svi_ports(net, sub[0], "192.168."+str(i), aci_nodes)
            self._add_interface_router(sub[0].get("subnet"), router.get("router"))
            port_create_args = {}
            port_create_args.update({"port_security_enabled": "false"})
            port_create_args.update({"fixed_ips": [{"ip_address": "192.168."+str(i)+".101"}]})      
            p = self._create_port(net, port_create_args)
            p_id = p.get('port', {}).get('id')
            nics = [{"port-id": pfip_id},{"port-id": p_id}]
            kwargs = {}
            kwargs.update({'nics': nics})
            kwargs.update({'key_name': key_name})
            vm.append(self._boot_server(image, flavor, False, **kwargs))    
        self.sleep_between(30, 40)
        
        prefix = []
        for i in range(101, 101+int(scale)):
            prefix.append(i)
            print "\nConfiguring the VM-"+str(i%100)+"...\n"
            command1 = {
                        "interpreter": "/bin/sh",
                        "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/orchest_svi_scale.sh"
                    }   
            command2 = {
                        "interpreter": "/bin/sh",
                        "script_inline": "/usr/local/bin/orchest_svi_scale.sh " + str(i) + ";/root/create_bird.sh " + str(i)
                    }
            self._remote_command(username, password, fip[i%101], command1, vm[i%101])
            self._remote_command(username, password, fip[i%101], command2, vm[i%101])
            
            print "\nRunning bird in the VM-"+str(i%100)+"...\n"
            command3 = {
                        "interpreter": "/bin/sh",
                        "script_inline": "bird -c /etc/bird/bird_svi_scale.conf"
                    }
            self._remote_command(username, password, fip[i%101], command3, vm[i%101])
            self.sleep_between(10, 20)

            print "\nValidating BGP session from VM-"+str(i%100)+"...\n"
            command4 = {
                        "interpreter": "/bin/sh",
                        "script_inline": "birdc show protocol;birdc show route"
                    }
            self._remote_command(username, password, fip[i%101], command4, vm[i%101])
        
        for i in range(101, 101+int(scale)):
            print "\nVerify traffic from the VM-"+str(i%100)+"...\n"
            ping = []
            ping.extend(prefix)
            ping.pop(i%101)
            for j in ping:
                command5 = {
                            "interpreter": "/bin/sh",
                            "script_inline": "ping -c 5 11.10."+str(j)+".1;ping -c 5 11.10."+str(j)+".2;ping -c 5 11.10."+str(j)+".3;ping -c 5 11.10."+str(j)+".4;ping -c 5 11.10."+str(j)+".5"
                        }   
                self._remote_command(username, password, fip[i%101], command5, vm[i%101])
