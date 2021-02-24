from rally import exceptions
from rally.task import utils
from rally.common import cfg
from rally.task import atomic
from rally.common import logging
from rally.aci_plugins import vcpe_utils
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.vm import utils as vm_utils
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

class CreateOstackResources(vcpe_utils.vCPEScenario, vm_utils.VMScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario, scenario.OpenStackScenario):
    
    def create_network(self, network, name, bgp_asn, external_net, cidr, aci_nodes):
        
        print "Creating external network with provided l3out...\n"
        try:
            net = self.clients("neutron").show_network(network)
        except Exception as ex:
            net = self._admin_create_network(name, {"provider:network_type": "vlan", "shared": True,
                                                            "apic:svi": True, "apic:bgp_enable": True,
                                                            "apic:bgp_asn": bgp_asn,
                                                            "apic:distinguished_names": {"ExternalNetwork": external_net}})
            sub = self._admin_create_subnet(net, {"cidr": cidr}, None)
            self._create_svi_ports(net, sub, cidr[0:9], aci_nodes)

        return net

    def boot_vm(self, port_id, image, flavor, key_name=None, admin=False, user=False):
        
        kwargs = {}
        if type(port_id) is list:
            nics = [{"port-id": port_id[0]}, {"port-id": port_id[1]}]
        else:
            nics = [{"port-id": port_id}]
        kwargs.update({'nics': nics})
        if key_name:
            kwargs.update({'key_name': key_name})
        if admin:
            vm = self._admin_boot_server(image, flavor, False, **kwargs)
        elif user:
            vm = self._user_boot_server(image, flavor, False, **kwargs)
        else:
            vm = self._boot_server(image, flavor, False, **kwargs)
        return vm

    def boot_server(self, net, port_args, image, flavor, net2=None, service_vm=False, key_name=False, admin=False, user=False):
        if service_vm:
            pin = self._create_port(net, port_args)
            pout = self._create_port(net2, port_args)
            pin_id = pin.get('port', {}).get('id')
            pout_id = pout.get('port', {}).get('id')
            if key_name:
                vm = self.boot_vm([pin_id, pout_id], image, flavor, key_name=key_name)
            else:
                vm = self.boot_vm([pin_id, pout_id], image, flavor, user=user)
            return vm, pin, pout
        else:
            fip = self._admin_create_port(net, port_args)
            fip_id = fip.get('port', {}).get('id')
            trunk_payload = {"port_id": fip_id}
            trunk = self._admin_create_trunk(trunk_payload)
            vm = self.boot_vm(fip_id, image, flavor, admin=admin)
            return vm, trunk, fip

    def create_network_subnet(self, router, cidr, aci_nodes, bgp_asn):
        
        net1, sub1 = self._create_network_and_subnets(
            {"provider:network_type": "vlan", "apic:svi": True, "apic:bgp_enable": True, "apic:bgp_asn": bgp_asn}, {"cidr": cidr}, 1, None)

        net1_id = net1.get('network', {}).get('id')
        self._create_svi_ports(net1, sub1[0], cidr[0:9], aci_nodes)
        self._add_interface_router(sub1[0].get("subnet"), router.get("router"))

        return net1, sub1, net1_id

    def crete_port_and_add_trunk(self, net, port_create_args, trunk, seg_id='10'):
        
        subp = self._create_port(net, port_create_args)
        subp1_id = subp.get('port', {}).get('id')
        subport_payload = [{"port_id": subp["port"]["id"],
                            "segmentation_type": "vlan",
                            "segmentation_id": seg_id}]
        self._admin_add_subports_to_trunk(trunk, subport_payload)
        subp_mac = subp.get('port', {}).get('mac_address')

        return subp_mac, subp

    def configure_bras_nat_vm(self, username, password, fip, vm, subnet_port_mac, script_name, nat_vm=False):
        
        print("Configuring the VM and running Bird init...")
        command1 = {
            "interpreter": "/bin/sh",
            "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/%s" %script_name
        }
        if nat_vm:
            command2 = {
                "interpreter": "/bin/sh",
                "script_inline": "/usr/local/bin/orchest_nat.sh " + subnet_port_mac + ";/usr/local/bin/run_bird"
            }
        else:
            command2 = {
                "interpreter": "/bin/sh",
                "script_inline": "/usr/local/bin/orchest_bras.sh " + subnet_port_mac + ";/usr/local/bin/run_bird"
            }
        self._remote_command(username, password, fip, command1, vm)
        self._remote_command(username, password, fip, command2, vm)
        self.sleep_between(30, 40)

    def configure_vm(self, username, password, fip, vm, script_name):
        
        command1 = {
            "interpreter": "/bin/sh",
            "script_file": "/usr/local/lib/python2.7/dist-packages/rally/aci_plugins/orchest/%s" %script_name
        }
        self._remote_command(username, password, fip, command1, vm)

    def run_bird_conf(self, username, password, fip, vm, script_name):
        
        print("Running bird in the VMs...")
        command = {
            "interpreter": "/bin/sh",
            "script_inline": "bird -c /etc/bird/%s" %script_name
        }
        self._remote_command(username, password, fip, command, vm)

    def validate_bgp_session(self, username, password, fip, vms, no_demo=False):
        
        if no_demo:
            cmd = "birdc show protocol;birdc show route"
        else:
            cmd = "birdc show protocol;birdc show route;birdc -s /tmp/sock-cats show protocol;\
            birdc -s /tmp/sock-cats show route"
        command = {
            "interpreter": "/bin/sh",
            "script_inline": cmd
        }
        if type(fip) is not list and type(vms) is not list:
            fip = [fip]
            vms = [vms]
        for (ip, vm) in zip(fip, vms):
            self._remote_command(username, password, ip, command, vm)

    def configuring_router(self, username, password, access_router_ip, script_name, delete=False, path=None):
        
        if path:
            req_path = "%s/%s" %(path, script_name)
        else:
            req_path = "/usr/local/bin/%s" %script_name
        if delete:
            print("Cleaning up ACCESS-router...")
            cmd = "sudo %s delsites" %req_path
        else:
            print("Configuring ACCESS-router for traffic verification...")
            cmd = "sudo %s mksites" %req_path
        command = {
            "interpreter": "/bin/sh",
            "script_inline": cmd
        }
        self._remote_command_wo_server(username, password, access_router_ip, command)

    def verify_traffic_without_sfc(self, username, password, access_router_ip):
        
        print("Traffic verification before creating SFC")
        command = {
            "interpreter": "/bin/sh",
            "script_inline": "sudo ip netns exec cats ping -c 5 10.1.1.1;\
            sudo ip netns exec cats ping -c 5 8.8.8.1;\
            sudo ip netns exec cats ping -c 5 8.8.8.2;\
            sudo ip netns exec cats ping -c 5 8.8.8.3"
        }
        self._remote_command_wo_server(username, password, access_router_ip, command)

    def run_ping(self, username, password, access_router_ip, ping_ip, site=None):
        
        if site:
            cmd = "sudo ip netns exec %s ping -c 5 %s" %(site, ping_ip)
        else:
            cmd = "sudo ip netns exec cats ping -c 5 %s" %ping_ip
        command = {
            "interpreter": "/bin/sh",
            "script_inline": cmd
        }
        self._remote_command_wo_server(username, password, access_router_ip, command)

    def create_service_vm(self, router, service_image1, flavor, cidr1, cidr2, src_cidr='10.0.0.0/16', resources=None, user=False, 
                           dualstack=False, ipv6_src_cidr='', left_v6_cidr='', right_v6_cidr=''):
        if dualstack:
            left, sub2 = self.create_network_and_subnets_dual({"provider:network_type": "vlan"}, {"cidr": cidr1, 'host_routes': [
                                                                  {'destination': src_cidr, 'nexthop': cidr1[0:6] + '1'}]}, 1, None, dualstack, 
                                                                  {"cidr": left_v6_cidr, 'host_routes': [{'destination': ipv6_src_cidr, 
                                                                  'nexthop': left_v6_cidr[0:5] + '1'}],
                                                                  "ipv6_ra_mode": "dhcpv6-stateful", "ipv6_address_mode": "dhcpv6-stateful"}, None)
            right, sub3 = self.create_network_and_subnets_dual({"provider:network_type": "vlan"}, {"cidr" :cidr2, 'host_routes': [{'destination': '0.0.0.0/1', 
                                                               'nexthop': cidr2[0:6] + '1'}, {'destination': '128.0.0.0/1', 'nexthop': cidr2[0:6] + '1'}]}, 
                                                                  1, None, dualstack, {"cidr": right_v6_cidr, 'host_routes': [
                                                                      {'destination': '0:0::/1', 'nexthop': right_v6_cidr[0:5]+'1'}, 
                                                                      {'destination': '::/1', 'nexthop': right_v6_cidr[0:5]+'1'}],
                                                                      "ipv6_ra_mode":"dhcpv6-stateful", "ipv6_address_mode": "dhcpv6-stateful"}, None)
            self._add_interface_router(sub2[0][0].get("subnet"), router.get("router"))
            self._add_interface_router(sub2[0][1].get("subnet"), router.get("router"))
            self._add_interface_router(sub3[0][0].get("subnet"), router.get("router"))
            self._add_interface_router(sub3[0][1].get("subnet"), router.get("router"))
        else:
            left, sub2 = self._create_network_and_subnets({"provider:network_type": "vlan"}, {"cidr": cidr1,
                'host_routes': [{'destination': src_cidr, 'nexthop': cidr1[0:6] + '1'}]}, 1, None)
            right, sub3 = self._create_network_and_subnets({"provider:network_type": "vlan"}, {"cidr": cidr2,
                'host_routes': [{'destination': '0.0.0.0/1', 'nexthop': cidr2[0:6] + '1'},
                {'destination': '128.0.0.0/1', 'nexthop': cidr2[0:6] + '1'}]}, 1, None)
            self._add_interface_router(sub2[0].get("subnet"), router.get("router"))
            self._add_interface_router(sub3[0].get("subnet"), router.get("router"))
        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        print("Creating service vm")
        service_vm, pin, pout = self.boot_server(left, port_create_args, service_image1, flavor, net2=right, service_vm=True, user=user)
        if resources:
            resources["networks"].append(left)
            resources["networks"].append(right)
            resources["subnets"].append(sub2[0])
            resources["subnets"].append(sub3[0])
            resources["vms"].append(service_vm)
        return service_vm, pin, pout

    def create_access_vm_nat_vm(self,  acc_net, nat_net, port_create_args, dualstack, image, flavor, key_name=None):
        
        pfip1 = self._create_port(acc_net, port_create_args)
        pfip2 = self._create_port(nat_net, port_create_args)
        access_vm = self.boot_vm(pfip1.get('port', {}).get('id'), image, flavor, key_name=key_name)
        nat_vm = self.boot_vm(pfip2.get('port', {}).get('id'), image, flavor, key_name=key_name)
        self.sleep_between(30, 40)
        if dualstack:
            fip1 = [pfip1.get('port', {}).get('fixed_ips')[0].get('ip_address'), pfip1.get('port', {}).get('fixed_ips')[1].get('ip_address')]
            fip2 = [pfip2.get('port', {}).get('fixed_ips')[0].get('ip_address'), pfip2.get('port', {}).get('fixed_ips')[1].get('ip_address')]
        else:
            fip1 = [pfip1.get('port', {}).get('fixed_ips')[0].get('ip_address')]
            fip2 = [pfip2.get('port', {}).get('fixed_ips')[0].get('ip_address')]
        return access_vm, nat_vm, fip1, fip2

    def create_src_dest_vm(self, secgroup, public_net, net1, net2, vm_image, flavor, svi=False,
                           ips=None, key_name=None, trunk=False):
        
        port_create_args = {}
        port_create_args["security_groups"] = [secgroup.get('id')]
        p1, p1_id = self.create_port(public_net, port_create_args)
        if trunk:
            p2, p2_id = self.create_port(public_net, port_create_args)
        else:
            p2, p2_id = self.create_port(net1, port_create_args)
        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        networks = [net1, net2]
        ports = [p1_id, p2_id]
        vms = []
        trunks = []
        if svi:
            for (net, ip, port) in zip(networks, ips, ports):
                port_create_args.update({"fixed_ips": [{"ip_address": ip}]})
                p3, p3_id = self.create_port(net, port_create_args)
                if key_name:
                    vm1 = self.boot_vm([port, p3_id], vm_image, flavor, key_name=key_name)
                else:
                    vm1 = self.boot_vm([port, p3_id], vm_image, flavor)
                vms.append(vm1)
        else:
            for (net, port) in zip(networks, ports):
                p3, p3_id = self.create_port(net, port_create_args)
                if trunk:
                    trunk_payload = {"port_id": p3_id}
                    trunks.append(self._create_trunk(trunk_payload))
                if key_name:
                    vm1 = self.boot_vm([port, p3_id], vm_image, flavor, key_name=key_name)
                else:
                    vm1 = self.boot_vm([port, p3_id], vm_image, flavor)
                vms.append(vm1)
        self.sleep_between(30, 40)
        if trunk:
            return p1, p2, vms[0], vms[1], trunks[0], trunks[1], port_create_args

        return p1, p2, vms[0], vms[1]
    
    def create_sub_add_to_interfaces_for_trunk(self, cidr1, cidr2, cidr3, dualstack=False, v6cidr1=None, v6cidr2=None, v6cidr3=None):

        if dualstack:
            net1, sub1 = self.create_network_and_subnets_dual({"provider:network_type": "vlan"}, {"cidr": cidr1}, 1, None, \
                    dualstack, {"cidr": v6cidr1, "ipv6_ra_mode":"dhcpv6-stateful", "ipv6_address_mode": "dhcpv6-stateful"}, None)
            net2, sub2 = self.create_network_and_subnets_dual({"provider:network_type": "vlan"}, {"cidr": cidr2}, 1, None, \
                    dualstack, {"cidr": v6cidr2, "ipv6_ra_mode":"dhcpv6-stateful", "ipv6_address_mode": "dhcpv6-stateful"}, None)
            net3, sub3 = self.create_network_and_subnets_dual({"provider:network_type": "vlan"}, {"cidr": cidr3}, 1, None, \
                    dualstack, {"cidr": v6cidr3, "ipv6_ra_mode":"dhcpv6-stateful", "ipv6_address_mode": "dhcpv6-stateful"}, None)
        else:
            net1, sub1 = self._create_network_and_subnets({"provider:network_type": "vlan"}, {"cidr": cidr1}, 1, None)
            net2, sub2 = self._create_network_and_subnets({"provider:network_type": "vlan"}, {"cidr": cidr2}, 1, None)
            net3, sub3 = self._create_network_and_subnets({"provider:network_type": "vlan"}, {"cidr": cidr3}, 1, None)

        router = self._create_router({}, False)
        if dualstack:
            self._add_interface_router(sub1[0][0].get("subnet"), router.get("router"))
            self._add_interface_router(sub2[0][0].get("subnet"), router.get("router"))
            self._add_interface_router(sub3[0][0].get("subnet"), router.get("router"))
            self._add_interface_router(sub1[0][1].get("subnet"), router.get("router"))
            self._add_interface_router(sub2[0][1].get("subnet"), router.get("router"))
            self._add_interface_router(sub3[0][1].get("subnet"), router.get("router"))
        else:
            self._add_interface_router(sub1[0].get("subnet"), router.get("router"))
            self._add_interface_router(sub2[0].get("subnet"), router.get("router"))
            self._add_interface_router(sub3[0].get("subnet"), router.get("router"))
        return [net1, net2, net3], router
    
    def create_net_sub_for_sfc(self, src_cidr, dest_cidr, dualstack=False, ipv6_src_cidr=None, ipv6_dest_cidr=None):
        if dualstack:
            net1, sub1 = self.create_network_and_subnets_dual({"provider:network_type": "vlan"}, {"cidr": src_cidr}, 1, None, dualstack, {"cidr": ipv6_src_cidr, "ipv6_ra_mode":"slaac", "ipv6_address_mode": "slaac"}, None)
            net2, sub2 = self.create_network_and_subnets_dual({"provider:network_type": "vlan"}, {"cidr": dest_cidr}, 1, None, dualstack, {"cidr": ipv6_dest_cidr, "ipv6_ra_mode":"slaac", "ipv6_address_mode": "slaac"}, None)
            left, sub3 = self.create_network_and_subnets_dual({"provider:network_type": "vlan"}, {"cidr": "1.1.0.0/24",
                                                                                          'host_routes': [{'destination': src_cidr, 'nexthop': '1.1.0.1'}]}, 1, None, 
                                                                                     dualstack, {"cidr": 'a:a::/64', 'host_routes': [{
                                                                                    'destination': ipv6_src_cidr, 'nexthop': 'a:a::1'}], 
                                                                                    "ipv6_ra_mode":"dhcpv6-stateful", "ipv6_address_mode": "dhcpv6-stateful"}, None)
            right, sub4 = self.create_network_and_subnets_dual({"provider:network_type": "vlan"}, {"cidr": "2.2.0.0/24",
                                                               'host_routes': [{'destination': '0.0.0.0/1', 'nexthop': '2.2.0.1'},{'destination': '128.0.0.0/1', 
                                                                'nexthop': '2.2.0.1'}]}, 1, None, dualstack, {"cidr":"b:b::/64", 
                                                                'host_routes': [{'destination': '0:0::/1', 'nexthop': 'b:b::1'}, {'destination': '::/1', 
                                                                'nexthop': 'b:b::1'}], "ipv6_ra_mode":"dhcpv6-stateful", "ipv6_address_mode": "dhcpv6-stateful"}, None)
        else:
            net1, sub1 = self._create_network_and_subnets({"provider:network_type": "vlan"}, {"cidr": src_cidr}, 1, None)
            net2, sub2 = self._create_network_and_subnets({"provider:network_type": "vlan"}, {"cidr": dest_cidr}, 1, None)
            left, sub3 = self._create_network_and_subnets({"provider:network_type": "vlan"}, {"cidr": "1.1.0.0/24",
                                                                                          'host_routes': [{'destination': src_cidr, 'nexthop': '1.1.0.1'}]}, 1, None)
            right, sub4 = self._create_network_and_subnets({"provider:network_type": "vlan"}, {"cidr": "2.2.0.0/24",
                                                                                          'host_routes': [{'destination': '0.0.0.0/1', 'nexthop': '2.2.0.1'},
                                                                                              {'destination': '128.0.0.0/1', 'nexthop': '2.2.0.1'}]}, 1, None)

        return [net1, net2, left, right], [sub1, sub2, sub3, sub4]

    def add_interface_to_router(self, router, sub_list, dualstack=False):
        if dualstack:
            self._add_interface_router(sub_list[0][0][0].get("subnet"), router.get("router"))
            self._add_interface_router(sub_list[0][0][1].get("subnet"), router.get("router"))
            self._add_interface_router(sub_list[1][0][0].get("subnet"), router.get("router"))
            self._add_interface_router(sub_list[1][0][1].get("subnet"), router.get("router"))
            self._add_interface_router(sub_list[2][0][0].get("subnet"), router.get("router"))
            self._add_interface_router(sub_list[2][0][1].get("subnet"), router.get("router"))
            self._add_interface_router(sub_list[3][0][0].get("subnet"), router.get("router"))
            self._add_interface_router(sub_list[3][0][1].get("subnet"), router.get("router"))
        else:
            self._add_interface_router(sub_list[0][0].get("subnet"), router.get("router"))
            self._add_interface_router(sub_list[1][0].get("subnet"), router.get("router"))
            self._add_interface_router(sub_list[2][0].get("subnet"), router.get("router"))
            self._add_interface_router(sub_list[3][0].get("subnet"), router.get("router"))
        
    def create_vms_for_sfc_test(self, secgroup, public_net, net1, net2, vm_image, flavor, key_name=None, multi_sfc=False):
        
        port_create_args = {}
        port_create_args["security_groups"] = [secgroup.get('id')]
        p1, p1_id = self.create_port(public_net, port_create_args)
        p2, p2_id = self.create_port(public_net, port_create_args)
        port_create_args = {}
        port_create_args.update({"port_security_enabled": "false"})
        psrc, psrc_id = self.create_port(net1, port_create_args)
        if key_name: 
            src_vm = self.boot_vm([p1_id, psrc_id], vm_image, flavor, key_name=key_name)
        else:
            src_vm = self.boot_vm([p1_id, psrc_id], vm_image, flavor)
        pdesr, pdest_id = self.create_port(net2, port_create_args)
        dest_vm = self.boot_vm([p2_id, pdest_id], vm_image, flavor)
        if multi_sfc:
            return p1, p2, src_vm, dest_vm, port_create_args

        return p1, p2, src_vm, dest_vm
    
    def create_vms_for_svi_tests(self, secgroup, public_network, vm_image, flavor, key_name, dualstack, networks=[], ips=[], v6ips=None):
        
        port_create_args = {}
        port_create_args["security_groups"] = [secgroup.get('id')]
        pfip1, pfip1_id = self.create_port(public_network, port_create_args)
        pfip2, pfip2_id = self.create_port(public_network, port_create_args)
        ports = [pfip1_id, pfip2_id]
        vms = []
        for (net, ip, port, v6ip) in zip(networks, ips, ports, v6ips):
            port_create_args = {}
            port_create_args.update({"port_security_enabled": "false"})
            if dualstack:port_create_args.update({"fixed_ips": [{"ip_address": ip}, {"ip_address": v6ip}]})
            else:port_create_args.update({"fixed_ips": [{"ip_address": ip}]})
            p3, p3_id = self.create_port(net, port_create_args)
            vm1 = self.boot_vm([port, p3_id], vm_image, flavor, key_name=key_name)
            vms.append(vm1)
        return pfip1, pfip2, vms[0], vms[1]

    def create_port(self, net, port_create_args):
        
        p1 = self._create_port(net, port_create_args)
        port_id = p1.get('port', {}).get('id')
        return p1, port_id

    def delete_servers(self, servers):
        
        print("cleaning up servers...")
        for vm in servers:
            self._delete_server(vm)

    def delete_trunks(self, trunks):
        
        print("deleting trunks...")
        for trunk in trunks:
            self._admin_delete_trunk(trunk)

    def delete_ports(self, ports):
        
        print("Deleting ports...")
        for port in ports:
            self._admin_delete_port(port)

    def delete_router_interface(self, interfaces, router):
        
        print("Deleting router interfaces...")
        for subnet in interfaces:
            self._admin_remove_interface_router(subnet, router)

    def delete_network(self, networks):
       
        print("Deleting networks...")
        for nw in networks:
            self._delete_all_ports(nw)
            self.sleep_between(5, 10)
            self._delete_svi_ports(nw)
            self._admin_delete_network(nw)

