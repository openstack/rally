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
@scenario.configure(name="ScenarioPlugin.trunk_scale", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")
class TrunkScale(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario,
                 nova_utils.NovaScenario, scenario.OpenStackScenario):
   
    resources_created = {"vms": [], "trunks": []}

    def run(self, image, flavor, public_network, username, password, scale, dualstack):

        try:
            public_net = self.clients("neutron").show_network(public_network)
            secgroup = self.context.get("user", {}).get("secgroup")
            key_name=self.context["user"]["keypair"]["name"]

            router = self._create_router({}, False)
            if dualstack:
                net0, sub0 = self.create_network_and_subnets_dual({"provider:network_type": "vlan"}, {"cidr": '192.168.0.0/24'}, 1, None, \
                        dualstack, {"cidr": '2001:a0::/64', "gateway_ip": "2001:a0::1", "ipv6_ra_mode":"dhcpv6-stateful", \
                    "ipv6_address_mode": "dhcpv6-stateful"}, None)
                self._add_interface_router(sub0[0][0].get("subnet"), router.get("router"))
                self._add_interface_router(sub0[0][1].get("subnet"), router.get("router"))
            else:
                net0, sub0 = self._create_network_and_subnets({"provider:network_type": "vlan"}, {"cidr": '192.168.0.0/24'}, 1, None)
                self._add_interface_router(sub0[0].get("subnet"), router.get("router"))

            port_create_args = {}
            port_create_args["security_groups"] = [secgroup.get('id')]
            pf1, pf1_id = self.create_port(public_net, port_create_args)
            pf2, pf2_id = self.create_port(public_net, port_create_args)
            
            port_create_args = {}
            port_create_args.update({"port_security_enabled": "false"})
            ptr1, ptr1_id = self.create_port(net0, port_create_args)
            trunk_payload = {"port_id": ptr1_id}
            trunk1 = self._create_trunk(trunk_payload)
            vm_tr1 = self.boot_vm([pf1_id, ptr1_id], image, flavor, key_name=key_name)
            self.resources_created["vms"].append(vm_tr1)
            self.resources_created["trunks"].append(trunk1)

            ptr2, ptr2_id = self.create_port(net0, port_create_args)
            trunk_payload = {"port_id": ptr2_id}
            trunk2 = self._create_trunk(trunk_payload)
            vm_tr2 = self.boot_vm([pf2_id, ptr2_id], image, flavor, key_name=key_name)
            self.resources_created["vms"].append(vm_tr2)
            self.resources_created["trunks"].append(trunk2)

            for i in range(101, 101+int(scale)):
                hex_i = hex(int(i))[2:]
                if dualstack:
                    net, sub = self.create_network_and_subnets_dual({"provider:network_type": "vlan"}, {"cidr": "192.168."+str(i)+".0/24"}, 1, None, \
                            dualstack, {"cidr": '2001:'+hex_i+'::/64', "gateway_ip": "2001:"+hex_i+"::1", "ipv6_ra_mode":"dhcpv6-stateful", "ipv6_address_mode": "dhcpv6-stateful"}, None)
                    self._add_interface_router(sub[0][0].get("subnet"), router.get("router"))
                    self._add_interface_router(sub[0][1].get("subnet"), router.get("router"))
                else:
                    net, sub = self._create_network_and_subnets({"provider:network_type": "vlan"}, {"cidr": "192.168."+str(i)+".0/24"}, 1, None)
                    self._add_interface_router(sub[0].get("subnet"), router.get("router"))

                port_create_args = {}
                port_create_args.update({"port_security_enabled": "false"})
                if dualstack:
                    port_create_args.update({"fixed_ips": [{"ip_address": "192.168."+str(i)+".101"}, {"ip_address": "2001:"+hex_i+":0:0:0:0:0:0065"}]})
                else:
                    port_create_args.update({"fixed_ips": [{"ip_address": "192.168."+str(i)+".101"}]})
                port_create_args["mac_address"] = 'fa:16:3e:bc:d5:' + hex_i
                sub_mac1, sp1 = self.crete_port_and_add_trunk(net, port_create_args, trunk1, seg_id=i)

                port_create_args = {}
                port_create_args.update({"port_security_enabled": "false"})
                if dualstack:
                    port_create_args.update({"fixed_ips": [{"ip_address": "192.168."+str(i)+".102"}, {"ip_address": "2001:"+hex_i+":0:0:0:0:0:0066"}]})
                else:
                    port_create_args.update({"fixed_ips": [{"ip_address": "192.168."+str(i)+".102"}]})
                port_create_args["mac_address"] = 'fa:16:3e:1b:a1:' + hex_i
                sub_mac2, sp2 = self.crete_port_and_add_trunk(net, port_create_args, trunk2, seg_id=i)

            fip1 = pf1.get('port', {}).get('fixed_ips')[0].get('ip_address')
            fip2 = pf2.get('port', {}).get('fixed_ips')[0].get('ip_address')

            if dualstack:
                command1 = {
                            "interpreter": "/bin/sh",
                            "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/orchest_trunk_scale_vm1_dual.sh"
                        }

                command2 = {
                            "interpreter": "/bin/sh",
                            "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/orchest_trunk_scale_vm2_dual.sh"
                        }
            else:
                command1 = {
                            "interpreter": "/bin/sh",
                            "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/orchest_trunk_scale_vm1.sh"
                        }

                command2 = {
                            "interpreter": "/bin/sh",
                            "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/orchest_trunk_scale_vm2.sh"
                        }

            
            print("Adding sub-interfaces into the VM1...")
            self._remote_command(username, password, fip1, command1, vm_tr1)
            print("Adding sub-interfaces into the VM2...")
            self._remote_command(username, password, fip2, command2, vm_tr2)
            command3 = {
                        "interpreter": "/bin/sh",
                        "script_inline": "/usr/local/bin/orchest_trunk_scale.sh " + str(scale)
                    }
            self._remote_command(username, password, fip1, command3, vm_tr1)
            self._remote_command(username, password, fip2, command3, vm_tr2)
            self.sleep_between(30, 40)

            print("Traffic verification from VM1")
            command4 = {
                        "interpreter": "/bin/sh",
                        "script_inline": "/root/traffic.sh " + str(scale)
                    }
            self._remote_command(username, password, fip1, command4, vm_tr1)
            print("Traffic verification from VM2")
            self._remote_command(username, password, fip2, command4, vm_tr2)
        except Exception as e:
            raise e
        finally:
            self.cleanup()

    def cleanup(self):

        self.delete_servers(self.resources_created["vms"])
        self.delete_trunks(self.resources_created["trunks"])
