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
@scenario.configure(name="ScenarioPlugin.sfc_scale_parallel", context={"cleanup@openstack": ["nova", "neutron"],
                                                                       "keypair@openstack": {},
                                                                       "allow_ssh@openstack": None},
                    platform="openstack")
class SFCScaleParallel(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario,
                       scenario.OpenStackScenario):

    def run(self, src_cidr, dest_cidr, vm_image, service_image1, flavor, public_network, username, password, scale):

        public_net = self.clients("neutron").show_network(public_network)
        secgroup = self.context.get("user", {}).get("secgroup")

        net_list, sub_list = self.create_net_sub_for_sfc(src_cidr, dest_cidr)
        router = self._create_router({}, False)
        self.add_interface_to_router(router, sub_list)

        net1_id = net_list[0].get('network', {}).get('id')
        net2_id = net_list[1].get('network', {}).get('id')
        
        p1, p2, src_vm, dest_vm = self.create_vms_for_sfc_test(secgroup, public_net, net_list[0], net_list[1],
                                                               vm_image, flavor)

        fip1 = p1.get('port', {}).get('fixed_ips')[0].get('ip_address')
        fip2 = p2.get('port', {}).get('fixed_ips')[0].get('ip_address')

        print("Configuring destination-vm for traffic verification...")
        command1 = {
            "interpreter": "/bin/sh",
            "script_inline": "ip address add 192.168.200.101/24 dev eth1;\
                    ip address add 192.168.200.102/24 dev eth1;\
                    ip address add 192.168.200.103/24 dev eth1;\
                    route add default gw 192.168.200.1 eth1"
        }
        self._remote_command(username, password, fip2, command1, dest_vm)

        command2 = {
            "interpreter": "/bin/sh",
            "script_inline": "ping -c 5 192.168.200.101;ping -c 5 192.168.200.102;ping -c 5 192.168.200.103"
        }

        print("Traffic verification before SFC")
        self._remote_command(username, password, fip1, command2, src_vm)
        try:
            print("Creating parallel service function chain")
            pp = []
            port_create_args = {}
            port_create_args.update({"port_security_enabled": "false"})
            for x in range(0, int(scale)):
                service_vm, pin, pout = self.boot_server(net_list[2], port_create_args, service_image1, flavor,
                                                         net2=net_list[3], service_vm=True)
                pp.append(self._create_port_pair(pin, pout))

            ppg = self._create_port_pair_group(pp)
            fc = self._create_flow_classifier(src_cidr, dest_cidr, net1_id, net2_id)
            pc = self._create_port_chain([ppg], [fc])
            self.sleep_between(30, 40)

            print("Traffic verification after creating SFC")
            self._remote_command(username, password, fip1, command2, src_vm)
        except Exception as e:
            raise e
        finally:
            self.cleanup_sfc()
