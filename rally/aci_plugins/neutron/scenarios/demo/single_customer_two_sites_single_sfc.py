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
@scenario.configure(name="ScenarioPlugin.single_customer_two_sites_single_sfc",
                    context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")
class SingleCustomerTwoSitesSingleSFC(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario,
                                      scenario.OpenStackScenario):

    resources_created = {"vms": [], "trunks": [], "routers": [], "subnets": [], "ports": [], "networks": []}

    def run(self, access_network, access_network_bgp_asn, nat_network, nat_network_bgp_asn, aci_nodes, bras_image,
            nat_image, service_image1, flavor, username, password, access_router_ip):

        acc_net = self.create_network(access_network, 'ACCESS', access_network_bgp_asn,
                                      "uni/tn-common/out-Access-Out/instP-data_ext_pol", '172.168.0.0/24', aci_nodes)
        nat_net = self.create_network(nat_network, 'INTERNET', nat_network_bgp_asn,
                                      "uni/tn-common/out-Internet-Out/instP-data_ext_pol", '173.168.0.0/24', aci_nodes)

        try:
            print("Creating Bras vm and nat vm...")
            port_create_args = {}
            port_create_args.update({"port_security_enabled": "false"})
            bras_vm1, trunk_bras1, pfip1 = self.boot_server(acc_net, port_create_args, bras_image, flavor, admin=True)
            bras_vm2, trunk_bras2, pfip2 = self.boot_server(acc_net, port_create_args, bras_image, flavor, admin=True)
            nat_vm, trunk_nat, pfip3 = self.boot_server(nat_net, port_create_args, nat_image, flavor, admin=True)
            self.resources_created.update({"vms": [bras_vm1, bras_vm2, nat_vm]})
            self.resources_created.update({"trunks": [trunk_bras1, trunk_bras2, trunk_nat]})
            self.resources_created.update({"ports": [pfip1, pfip2, pfip3]})

            print("Creating network, subnet and subports...")
            router = self._create_router({}, False)
            self.resources_created.update({"routers": [router]})
            net1, sub1, net1_id = self.create_network_subnet(router, "192.168.0.0/24", aci_nodes, "2010")
            self.resources_created.update({"networks": [net1]})
            self.resources_created.update({"subnets": [sub1[0]]})

            subp1_mac, sp1 = self.crete_port_and_add_trunk(net1, port_create_args, trunk_bras1)
            subp2_mac, sp2 = self.crete_port_and_add_trunk(net1, port_create_args, trunk_bras2)
            subp3_mac, sp3 = self.crete_port_and_add_trunk(net1, port_create_args, trunk_nat)
            
            fip1 = pfip1.get('port', {}).get('fixed_ips')[0].get('ip_address')
            fip2 = pfip2.get('port', {}).get('fixed_ips')[0].get('ip_address')
            fip3 = pfip3.get('port', {}).get('fixed_ips')[0].get('ip_address')

            print("Configuring BRAS-VM and NAT VM...")
            self.configure_bras_nat_vm(username, password, fip1, bras_vm1, subp1_mac,
                                       "orchest_single_customer_two_site_bras1.sh")
            self.configure_bras_nat_vm(username, password, fip2, bras_vm2, subp2_mac,
                                       "orchest_single_customer_two_site_bras2.sh")
            self.configure_bras_nat_vm(username, password, fip3, nat_vm, subp3_mac,
                                       "orchest_single_customer_two_site_nat.sh",
                                       nat_vm=True)
            print("\nValidating BGP session from BRAS-VM1, BRAS-VM2 and NAT-VM...\n")
            self.validate_bgp_session(username, password, fip1, bras_vm1)
            self.validate_bgp_session(username, password, fip2, bras_vm2)
            self.validate_bgp_session(username, password, fip3, nat_vm)

            try:
                self.configuring_router('noiro', password, access_router_ip, 'orchest_single_customer_multi_site.sh')

                print("Traffic verification from site-1 before creating SFC")
                command9 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo ip netns exec cats-site1 ping -c 5 10.1.1.1;\
                                                sudo ip netns exec cats-site1 ping -c 5 8.8.8.1;\
                                                sudo ip netns exec cats-site1 ping -c 5 8.8.8.2;\
                                                sudo ip netns exec cats-site1 ping -c 5 8.8.8.3"
                }
                self._remote_command_wo_server('noiro', password, access_router_ip, command9)
                print("Traffic verification from site-2 before creating SFC")
                command10 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "sudo ip netns exec cats-site2 ping -c 5 10.1.1.1;\
                                                sudo ip netns exec cats-site2 ping -c 5 8.8.8.1;\
                                                sudo ip netns exec cats-site2 ping -c 5 8.8.8.2;\
                                                sudo ip netns exec cats-site2 ping -c 5 8.8.8.3"
                }
                self._remote_command_wo_server('noiro', password, access_router_ip, command10)

                print("Creating a single service function chain...")
                service_vm, pin, pout = self.create_service_vm(router, service_image1, flavor, '1.1.0.0/24', '2.2.0.0/24',
                                                             resources=self.resources_created)
                pp = self._create_port_pair(pin, pout)
                ppg = self._create_port_pair_group([pp])
                fc1 = self._create_flow_classifier('10.0.1.0/24', '8.8.8.0/24', net1_id, net1_id)
                fc2 = self._create_flow_classifier('10.0.2.0/24', '8.8.8.0/24', net1_id, net1_id)
                pc = self._create_port_chain([ppg], [fc1, fc2])
                self.sleep_between(30, 40)

                print("Traffic verification from site-1 after creating SFC")
                self.run_ping("noiro", password, access_router_ip, '10.1.1.1', site='cats-site1')
                self.run_ping("noiro", password, access_router_ip, '8.8.8.1', site='cats-site1')
                self.run_ping("noiro", password, access_router_ip, '8.8.8.2', site='cats-site1')
                self.run_ping("noiro", password, access_router_ip, '8.8.8.3', site='cats-site1')
                print("Traffic verification from site-2 after creating SFC")
                self.run_ping("noiro", password, access_router_ip, '10.1.1.1', site='cats-site2')
                self.run_ping("noiro", password, access_router_ip, '8.8.8.1', site='cats-site2')
                self.run_ping("noiro", password, access_router_ip, '8.8.8.2', site='cats-site2')
                self.run_ping("noiro", password, access_router_ip, '8.8.8.3', site='cats-site2')
            except Exception as e:
                raise e
            finally:
                self.configuring_router('noiro', password, access_router_ip, 'orchest_single_customer_multi_site.sh',
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

