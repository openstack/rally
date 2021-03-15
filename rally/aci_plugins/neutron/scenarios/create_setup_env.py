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
@scenario.configure(name="ScenarioPlugin.create_setup_env", context={"cleanup@openstack": ["nova", "neutron"],
                             "keypair@openstack": {},
                             "allow_ssh@openstack": None}, platform="openstack")

class CreateSetupEnv(vcpe_utils.vCPEScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario, scenario.OpenStackScenario):

    def run(self, access_network, access_network_bgp_asn, nat_network, nat_network_bgp_asn, aci_nodes, dualstack):
      
        try:
            acc_net = self.clients("neutron").show_network(access_network)
            nat_net = self.clients("neutron").show_network(nat_network)       
        except:
            acc_net = self._admin_create_network('ACCESS', {"provider:network_type": "vlan", "shared": True, "apic:svi": True, "apic:bgp_enable": True, \
                    "apic:bgp_asn": access_network_bgp_asn, "apic:distinguished_names": {"ExternalNetwork": "uni/tn-common/out-Access-Out/instP-data_ext_pol"}})
            if dualstack:
                acc_sub = self.admin_create_subnets_dual(acc_net, {"cidr": "172.168.0.0/24"}, None, 1, dualstack, {"cidr": "2001:ac::/64", 
                    "gateway_ip": "2001:ac::1", "ipv6_ra_mode":"dhcpv6-stateful", "ipv6_address_mode": "dhcpv6-stateful"}, None)
                self._create_svi_ports(acc_net, acc_sub[0][0], '172.168.0', aci_nodes, dualstack, acc_sub[0][1], '2001:ac')
            else:
                acc_sub = self._admin_create_subnet(acc_net, {"cidr": '172.168.0.0/24'}, None)
                self._create_svi_ports(acc_net, acc_sub, '172.168.0', aci_nodes, dualstack)

            nat_net = self._admin_create_network('INTERNET', {"provider:network_type": "vlan", "shared": True, "apic:svi": True, "apic:bgp_enable": True, \
                    "apic:bgp_asn": nat_network_bgp_asn, "apic:distinguished_names": {"ExternalNetwork": "uni/tn-common/out-Internet-Out/instP-data_ext_pol"}})
            if dualstack:
                nat_sub = self.admin_create_subnets_dual(nat_net, {"cidr": "173.168.0.0/24"}, None, 1, dualstack, {"cidr": "2001:ad::/64", 
                    "gateway_ip": "2001:ad::1", "ipv6_ra_mode":"dhcpv6-stateful", "ipv6_address_mode": "dhcpv6-stateful"}, None)
                self._create_svi_ports(nat_net, nat_sub[0][0], '173.168.0', aci_nodes, dualstack, nat_sub[0][1], '2001:ad')
            else:
                nat_sub = self._admin_create_subnet(nat_net, {"cidr": '173.168.0.0/24'}, None)
                self._create_svi_ports(nat_net, nat_sub, '173.168.0', aci_nodes, dualstack)
