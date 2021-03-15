from rally import consts
from rally import exceptions
from rally.task import utils
from rally.common import validation
from rally.aci_plugins import vcpe_utils
from rally.plugins.openstack import scenario
from rally.aci_plugins import create_ostack_resources
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils


@validation.add("required_services", services=[consts.Service.NOVA, consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="ScenarioPlugin.single_customer_multiple_sfc",
                    context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {}, "allow_ssh@openstack": None}, platform="openstack")
class SingleCustomerMultipleSFC(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario,
        scenario.OpenStackScenario):

    resources_created = {"vms": [], "trunks": [], "routers": [], "subnets": [], "ports": [], "networks": []}

    def run(self, access_network, access_network_bgp_asn, nat_network, nat_network_bgp_asn, aci_nodes, bras_image,
            nat_image, service_image1, service_image2, service_image3, flavor, username, password, access_router_ip):

        acc_net = self.create_network(access_network, 'ACCESS', access_network_bgp_asn,
                                      "uni/tn-common/out-Access-Out/instP-data_ext_pol", '172.168.0.0/24', aci_nodes)
        nat_net = self.create_network(nat_network, 'INTERNET', nat_network_bgp_asn,
                                      "uni/tn-common/out-Internet-Out/instP-data_ext_pol", '173.168.0.0/24', aci_nodes)

        try:
            print("Creating Bras vm and nat vm...")
            port_create_args = {}
            port_create_args.update({"port_security_enabled": "false"})
            bras_vm, trunk1, pfip1 = self.boot_server(acc_net, port_create_args, bras_image, flavor, admin=True)
            nat_vm, trunk2, pfip2 = self.boot_server(nat_net, port_create_args, nat_image, flavor, admin=True)
            self.resources_created["vms"].extend([bras_vm, nat_vm])
            self.resources_created["trunks"].extend([trunk1, trunk2])

            print("Creating network, subnet and subports...")
            router = self._create_router({}, False)
            self.resources_created["routers"].append(router)
            net1, sub1, net1_id = self.create_network_subnet(router, "192.168.0.0/24", aci_nodes, "2010")
            subp1_mac, subp = self.crete_port_and_add_trunk(net1, port_create_args, trunk1)
            self.resources_created["networks"].append(net1)
            self.resources_created["subnets"].append(sub1[0])

            port_create_args = {}
            port_create_args.update({"port_security_enabled": "false"})
            subp2_mac, subp2 = self.crete_port_and_add_trunk(net1, port_create_args, trunk2)

            fip1 = pfip1.get('port', {}).get('fixed_ips')[0].get('ip_address')
            fip2 = pfip2.get('port', {}).get('fixed_ips')[0].get('ip_address')
            self.resources_created["ports"].extend([pfip1, pfip2])

            print("Configuring BRAS-VM...")
            self.configure_bras_nat_vm(username, password, fip1, bras_vm, subp1_mac, "orchest_single_customer_bras.sh")
            print("Configuring NAT-VM...")
            self.configure_bras_nat_vm(username, password, fip2, nat_vm, subp2_mac, "orchest_single_customer_nat.sh",
                                       nat_vm=True)
            print("Validating BGP session from BRAS-VM...")
            self.validate_bgp_session(username, password, fip1, bras_vm)
            print("Validating BGP session from NAT-VM...")
            self.validate_bgp_session(username, password, fip2, nat_vm)

            try:
                self.configuring_router('noiro', password, access_router_ip, 'orchest_single_customer.sh')

                self.verify_multi_sfc_without_sfc('noiro', password, access_router_ip)

                print("Creating a single service function chain...")
                service_vm, pin1, pout1 = self.create_service_vm(router, service_image1, flavor, '1.1.0.0/24', '2.2.0.0/24',
                                                             resources=self.resources_created)
                pp1 = self._create_port_pair(pin1, pout1)
                ppg1 = self._create_port_pair_group([pp1])
                fc = self._create_flow_classifier('10.0.1.0/24', '8.8.8.0/24', net1_id, net1_id)
                
                service_vm21, pin21, pout21 = self.create_service_vm(router, service_image2, flavor, '3.3.0.0/24', '4.4.0.0/24',
                                                          resources=self.resources_created)
                pp21 = self._create_port_pair(pin21, pout21)
                service_vm22, pin22, pout22 = self.boot_server(self.resources_created["networks"][-2], port_create_args,
                                                       service_image2, flavor,
                                                       net2=self.resources_created["networks"][-1], service_vm=True)
                pp22 = self._create_port_pair(pin22, pout22)

                service_vm23, pin23, pout23 = self.boot_server(self.resources_created["networks"][-2], port_create_args,
                                                       service_image2, flavor,
                                                       net2=self.resources_created["networks"][-1], service_vm=True)
                pp23 = self._create_port_pair(pin23, pout23)
                ppg2 = self._create_port_pair_group([pp21, pp22, pp23])

                service_vm3, pin3, pout3 = self.create_service_vm(router, service_image3, flavor, '5.5.0.0/24', '6.6.0.0/24',
                                                        resources=self.resources_created)
                pp3 = self._create_port_pair(pin3, pout3)
                ppg3 = self._create_port_pair_group([pp3])
                pc = self._create_port_chain([ppg1, ppg2, ppg3], [fc])
                self.sleep_between(30, 40)

                print("Traffic verification after creating SFC...")
                self.run_ping('noiro', password, access_router_ip, '10.1.1.1', True)
                self.run_ping('noiro', password, access_router_ip, '8.8.8.1')
                self.run_ping('noiro', password, access_router_ip, '8.8.8.2')
                self.run_ping('noiro', password, access_router_ip, '8.8.8.3')
                self.run_ping('noiro', password, access_router_ip, '8.8.8.4', True)
                self.run_ping('noiro', password, access_router_ip, '8.8.8.5', True)
            except Exception as e:
                raise e
            finally:
                self.configuring_router('noiro', password, access_router_ip, 'orchest_single_customer.sh',
                                    delete=True)
        except Exception as e:
            raise e
        finally:
            self.cleanup()

    def cleanup(self):
        
        print "Cleaning up setup after testing..."
        self.delete_servers(self.resources_created["vms"])
        self.delete_trunks(self.resources_created["trunks"])
        self.delete_ports(self.resources_created["ports"])
        self.cleanup_sfc()
        for nw in self.resources_created["networks"]:
            self._delete_svi_ports(nw)

    def verify_multi_sfc_without_sfc(self, username, password, access_router_ip):

        command = {
            "interpreter": "/bin/sh",
            "script_inline": "sudo ip netns exec cats ping -c 5 10.1.1.1;\
                    sudo ip netns exec cats ping -c 5 8.8.8.1;\
                    sudo ip netns exec cats ping -c 5 8.8.8.2;\
                    sudo ip netns exec cats ping -c 5 8.8.8.3;\
                    sudo ip netns exec cats ping -c 5 8.8.8.4;\
                    sudo ip netns exec cats ping -c 5 8.8.8.5"
        }
        self._remote_command_validate(username, password, access_router_ip, command)
