from rally import consts
from rally.common import validation
from rally.aci_plugins import create_ostack_resources
from rally.aci_plugins import vcpe_utils
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils


@validation.add("required_services", services=[consts.Service.NOVA, consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="ScenarioPlugin.two_customer_single_sfc", context={"cleanup@openstack": ["nova", "neutron"],
                                                                            "keypair@openstack": {},
                                                                            "allow_ssh@openstack": None},
                    platform="openstack")
class TwoCustomerSingleSFC(create_ostack_resources.CreateOstackResources, vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario,
                           scenario.OpenStackScenario):
    resources_created = {"vms": [], "trunks": [], "routers": [], "subnets": [], "ports": [], "networks": []}
    resources_created2 = {"vms": [], "routers": [], "subnets": [], "networks": []}

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
            bras_vm, trunk_bras, pfip1 = self.boot_server(acc_net, port_create_args, bras_image, flavor, admin=True)
            nat_vm, trunk_nat, pfip2 = self.boot_server(nat_net, port_create_args, nat_image, flavor, admin=True)
            self.resources_created.update({"vms": [bras_vm, nat_vm]})
            self.resources_created.update({"trunks": [trunk_bras, trunk_nat]})
            self.resources_created.update({"ports": [pfip1, pfip2]})

            pro1, user1, new_user = self.create_rally_client("customer-1", "customer-1", self.context)
            self.context.get("users").append(new_user)
            self._change_client(1, self.context, None, None)
            self.resources_created.update({"projects": [pro1]})
            self.resources_created.update({"users": [user1]})

            print("Creating network, subnet and subports...")
            router1 = self._create_router({}, False)
            self.resources_created.update({"routers": [router1]})

            net1, sub1, net1_id = self.create_network_subnet(router1, "192.168.0.0/24", aci_nodes, "2010")
            self.resources_created.update({"networks": [net1]})
            self.resources_created.update({"subnets": [sub1[0]]})

            port_create_args = {}
            port_create_args.update({"port_security_enabled": "false"})
            subp1_mac, sp1 = self.crete_port_and_add_trunk(net1, port_create_args, trunk_bras)
            subp2_mac, sp2 = self.crete_port_and_add_trunk(net1, port_create_args, trunk_nat)

            fip1 = pfip1.get('port', {}).get('fixed_ips')[0].get('ip_address')
            fip2 = pfip2.get('port', {}).get('fixed_ips')[0].get('ip_address')

            try:
                self.configuring_router('noiro', password, access_router_ip, 'orchest_two_customer.sh')

                print("Creating a single service function chain for customer-1...")
                service_vm1, pin1, pout1 = self.create_service_vm(router1, service_image1, flavor,'1.1.0.0/24', '2.2.0.0/24',
                                                                resources=self.resources_created, user=True)
                pp1 = self._create_port_pair(pin1, pout1)
                ppg1 = self._create_port_pair_group([pp1])
                fc1 = self._create_flow_classifier('10.0.1.0/24', '8.8.8.0/24', net1_id, net1_id)
                pc1 = self._create_port_chain([ppg1], [fc1])
                
                print("Creating a single service function chain for customer-2...")
                pro2, user2, new_user = self.create_rally_client("customer-2", "customer-2", self.context)
                self.context.get("users").append(new_user)
                self._change_client(2, self.context, None, None)
                self.resources_created["projects"].append(pro2)
                self.resources_created["users"].append(user2)

                router2 = self._create_router({}, False)
                self.resources_created2.update({"routers": [router2]})

                net2, sub2, net2_id = self.create_network_subnet(router2, "192.168.0.0/24", aci_nodes, "3010")
                self.resources_created2.update({"networks": [net2]})
                self.resources_created2.update({"subnets": [sub2[0]]})

                port_create_args = {}
                port_create_args.update({"port_security_enabled": "false"})
                subp3_mac, sp3 = self.crete_port_and_add_trunk(net2, port_create_args, trunk_bras, seg_id='20')
                subp4_mac, sp4 = self.crete_port_and_add_trunk(net2, port_create_args, trunk_nat,  seg_id='20')
                      
                service_vm2, pin2, pout2 = self.create_service_vm(router2, service_image1, flavor, '1.1.0.0/24', '2.2.0.0/24',
                                                                resources=self.resources_created2, user=True)
                pp2 = self._create_port_pair(pin2, pout2)
                ppg2 = self._create_port_pair_group([pp2])
                fc2 = self._create_flow_classifier('10.0.1.0/24', '8.8.8.0/24', net2_id, net2_id)
                pc2 = self._create_port_chain([ppg2], [fc2])
                self.sleep_between(30, 40)

                command2 = {
                    "interpreter": "/bin/sh",
                    "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/orchest_two_customer_bras.sh"
                }
                command3 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "/usr/local/bin/orchest_bras.sh " + subp1_mac + " " + subp3_mac + ";/usr/local/bin/run_bird"
                }

                command4 = {
                    "interpreter": "/bin/sh",
                    "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/orchest_two_customer_nat.sh"
                }
                command5 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "/usr/local/bin/orchest_nat.sh " + subp2_mac + " " + subp4_mac + ";/usr/local/bin/run_bird"
                }

                print("Configuring the BRAS-VM and running Bird init...")
                self._remote_command(username, password, fip1, command2, bras_vm)
                self._remote_command(username, password, fip1, command3, bras_vm)
                print("Configuring the NAT-VM and running Bird init...")
                self._remote_command(username, password, fip2, command4, nat_vm)
                self._remote_command(username, password, fip2, command5, nat_vm)
                self.sleep_between(30, 40)

                print("Validating BGP session from BRAS-VM...")
                command6 = {
                    "interpreter": "/bin/sh",
                    "script_inline": "birdc show protocol;\
                    birdc show route;birdc -s /tmp/sock-cats show protocol;\
                    birdc -s /tmp/sock-cats show route;birdc -s /tmp/sock-dogs show protocol;\
                    birdc -s /tmp/sock-dogs show route"
                }

                self._remote_command(username, password, fip1, command6, bras_vm)
                print("Validating BGP session from NAT-VM...")
                self._remote_command(username, password, fip2, command6, nat_vm)
                print("Traffic verification from Customer-1 after creating SFC\n")
                self.run_ping('noiro', password, access_router_ip, '10.1.1.1', "cats")
                self.run_ping('noiro', password, access_router_ip, '8.8.8.1', "cats")
                self.run_ping('noiro', password, access_router_ip, '8.8.8.2', "cats")
                self.run_ping('noiro', password, access_router_ip, '8.8.8.3', "cats")

                print("Traffic verification from Customer-2 after creating SFC\n")
                self.run_ping('noiro', password, access_router_ip, '10.1.1.1', "dogs")
                self.run_ping('noiro', password, access_router_ip, '8.8.8.1', "dogs")
                self.run_ping('noiro', password, access_router_ip, '8.8.8.2', "dogs")
                self.run_ping('noiro', password, access_router_ip, '8.8.8.3', "dogs")
            except Exception as e:
                raise e
            finally:
                self.configuring_router('noiro', password, access_router_ip, 'orchest_two_customer.sh',
                                        delete=True)
        except Exception as e:
            raise e
        finally:
            self.cleanup()
       
    def cleanup(self):

        self.delete_servers(self.resources_created["vms"])
        self.delete_servers(self.resources_created2["vms"])
        self.delete_trunks(self.resources_created["trunks"])
        self.delete_ports(self.resources_created["ports"])
        self.cleanup_sfc()
        self.delete_router_interface(self.resources_created["subnets"],
                                     self.resources_created["routers"][0])
        self._admin_delete_router(self.resources_created["routers"][0])
        self.delete_network(self.resources_created["networks"])
        self.delete_router_interface(self.resources_created2["subnets"],
                                     self.resources_created2["routers"][0])
        self._admin_delete_router(self.resources_created2["routers"][0])
        self.delete_network(self.resources_created2["networks"])
        for pro in self.resources_created["projects"]:
            self._delete_project(pro)
        for user in self.resources_created["users"]:
            self._delete_user(user)

