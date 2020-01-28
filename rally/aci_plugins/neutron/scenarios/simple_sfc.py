from rally import consts
from rally.plugins.openstack import scenario
from rally.task import atomic
from rally.task import validation
from rally.task import utils
from rally.common import validation
from rally import exceptions
from rally_openstack.scenarios.nova import utils as nova_utils
from rally_openstack.scenarios.neutron import utils as neutron_utils

@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="ScenarioPlugin.simple_sfc", context={"cleanup@openstack": ["nova", "neutron"]}, platform="openstack")
class SimpleSFC(scenario.OpenStackScenario, neutron_utils.NeutronScenario, nova_utils.NovaScenario):
    
     
    @atomic.action_timer("neutron.create_port_pair")
    def _create_port_pair(self, port1, port2, **port_pair_create_args):
        
    	port_pair_create_args = {}
        port_pair_create_args["ingress"] = port1["port"]["id"]
        port_pair_create_args["egress"] = port2["port"]["id"]
        port_pair_create_args["name"] = self.generate_random_name()
        return self.clients("neutron").create_sfc_port_pair({"port_pair": port_pair_create_args})


    @atomic.action_timer("neutron.list_port_pairs")
    def _list_port_pairs(self):
        
        return self.clients("neutron").list_sfc_port_pairs()["port_pairs"]


    @atomic.action_timer("neutron.show_port_pair")
    def _show_port_pair(self, port_pair, **params):
        
        return self.clients("neutron").show_sfc_port_pair(port_pair["port_pair"]["id"], **params)


    @atomic.action_timer("neutron.update_port_pair")
    def _update_port_pair(self, port_pair, **port_pair_update_args):
        
        port_pair_update_args["name"] = self.generate_random_name()
        body = {"port_pair": port_pair_update_args}
        return self.clients("neutron").update_sfc_port_pair(port_pair["port_pair"]["id"], body)


    @atomic.action_timer("neutron.delete_port_pair")
    def _delete_port_pair(self, port_pair):
        
        self.clients("neutron").delete_sfc_port_pair(port_pair["port_pair"]["id"])



    @atomic.action_timer("neutron.create_port_pair_group")
    def _create_port_pair_group(self, portpair, **port_pair_group_create_args):
        
    	port_pair_group_create_args = {}
        port_pair_group_create_args["port_pairs"] = [portpair["port_pair"]["id"]]
        port_pair_group_create_args["name"] = self.generate_random_name()
        return self.clients("neutron").create_sfc_port_pair_group({"port_pair_group": port_pair_group_create_args})


    @atomic.action_timer("neutron.list_port_pair_groups")
    def _list_port_pair_groups(self):
        
        return self.clients("neutron").list_sfc_port_pair_groups()["port_pair_groups"]


    @atomic.action_timer("neutron.show_port_pair_group")
    def _show_port_pair_group(self, port_pair_group, **params):
        
        return self.clients("neutron").show_sfc_port_pair_group(port_pair_group["port_pair_group"]["id"], **params)


    @atomic.action_timer("neutron.update_port_pair_group")
    def _update_port_pair_group(self, port_pair_group, **port_pair_group_update_args):
        
        port_pair_group_update_args["name"] = self.generate_random_name()
        body = {"port_pair_group": port_pair_group_update_args}
        return self.clients("neutron").update_sfc_port_pair_group(port_pair_group["port_pair_group"]["id"], body)


    @atomic.action_timer("neutron.delete_port_pair_group")
    def _delete_port_pair_group(self, port_pair_group):
        
        self.clients("neutron").delete_sfc_port_pair_group(port_pair_group["port_pair_group"]["id"])



    @atomic.action_timer("neutron.create_flow_classifier")
    def _create_flow_classifier(self, source_ip, dest_ip, l7_para, **flow_classifier_create_args):
        
    	flow_classifier_create_args = {}
        flow_classifier_create_args["source_ip_prefix"] = source_ip
        flow_classifier_create_args["destination_ip_prefix"] = dest_ip
        flow_classifier_create_args["l7_parameters"] = l7_para    
        flow_classifier_create_args["name"] = self.generate_random_name()
        return self.clients("neutron").create_sfc_flow_classifier({"flow_classifier": flow_classifier_create_args})


    @atomic.action_timer("neutron.list_flow_classifiers")
    def _list_flow_classifiers(self):
        
        return self.clients("neutron").list_sfc_flow_classifiers()["flow_classifiers"]


    @atomic.action_timer("neutron.show_flow_classifier")
    def _show_flow_classifier(self, flow_classifier, **params):
        
        return self.clients("neutron").show_sfc_flow_classifier(flow_classifier["flow_classifier"]["id"], **params)


    @atomic.action_timer("neutron.update_flow_classifier")
    def _update_flow_classifier(self, flow_classifier, **flow_classifier_update_args):
        
        flow_classifier_update_args["name"] = self.generate_random_name()
        body = {"flow_classifier": flow_classifier_update_args}
        return self.clients("neutron").update_sfc_flow_classifier(flow_classifier["flow_classifier"]["id"], body)


    @atomic.action_timer("neutron.delete_flow_classifier")
    def _delete_flow_classifier(self, flow_classifier):
        
        self.clients("neutron").delete_sfc_flow_classifier(flow_classifier["flow_classifier"]["id"])


    @atomic.action_timer("neutron.create_port_chain")
    def _create_port_chain(self, portpairgroup, flowclassifier, **port_chain_create_args):
        
    	port_chain_create_args = {}
        port_chain_create_args["port_pair_groups"] = [portpairgroup["port_pair_group"]["id"]]
        port_chain_create_args["flow_classifiers"] = [flowclassifier["flow_classifier"]["id"]]
        port_chain_create_args["name"] = self.generate_random_name()
        return self.clients("neutron").create_sfc_port_chain({"port_chain": port_chain_create_args})


    @atomic.action_timer("neutron.list_port_chains")
    def _list_port_chains(self):
        
        return self.clients("neutron").list_sfc_port_chains()["port_chains"]


    @atomic.action_timer("neutron.show_port_chain")
    def _show_port_chain(self, port_chain, **params):
        
        return self.clients("neutron").show_sfc_port_chain(port_chain["port_chain"]["id"], **params)


    @atomic.action_timer("neutron.update_port_chain")
    def _update_port_chain(self, port_chain, **port_chain_update_args):
        
        port_chain_update_args["name"] = self.generate_random_name()
        body = {"port_chain": port_chain_update_args}
        return self.clients("neutron").update_sfc_port_chain(port_chain["port_chain"]["id"], body)


    @atomic.action_timer("neutron.delete_port_chain")
    def _delete_port_chain(self, port_chain):
        
        self.clients("neutron").delete_sfc_port_chain(port_chain["port_chain"]["id"])
    

    def run(self, src_cidr, dest_cidr, image, flavor):
        
        net1, sub1 = self._create_network_and_subnets({},{"cidr": src_cidr}, 1, None)
        net2, sub2 = self._create_network_and_subnets({},{"cidr": dest_cidr}, 1, None)
        net3, sub3 = self._create_network_and_subnets({},{"cidr": "1.1.0.0/24"}, 1, None)
        net4, sub4 = self._create_network_and_subnets({},{"cidr": "2.2.0.0/24"}, 1, None)

        router = self._create_router({}, False)
        self._add_interface_router(sub1[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub2[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub3[0].get("subnet"), router.get("router"))
        self._add_interface_router(sub4[0].get("subnet"), router.get("router"))
  
        net1_id = net1.get('network', {}).get('id')
        net2_id = net2.get('network', {}).get('id')
        
        port_create_args = {}
        psrc = self._create_port(net1, port_create_args)
        p1_id = psrc.get('port', {}).get('id')
        nics = [{"port-id": p1_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        src_vm = self._boot_server(image, flavor, False, **kwargs)

        pdest = self._create_port(net2, port_create_args)
        p2_id = pdest.get('port', {}).get('id')
        nics = [{"port-id": p2_id}]
        kwargs = {}
        kwargs.update({'nics': nics})
        dest_vm = self._boot_server(image, flavor, False, **kwargs)

        pin = self._create_port(net3, port_create_args)
        pout = self._create_port(net4, port_create_args)
        kwargs = {}
        pin_id = pin.get('port', {}).get('id')
        pout_id = pout.get('port', {}).get('id')
        nics = [{"port-id": pin_id}, {"port-id": pout_id}]
        kwargs.update({'nics': nics})
        service_vm = self._boot_server(image, flavor, False, **kwargs)
    
        pp = self._create_port_pair(pin, pout)
        ppg = self._create_port_pair_group(pp)
        l7_para = {"logical_source_network": net1_id, "logical_destination_network": net2_id}
        fc = self._create_flow_classifier(src_cidr, '0.0.0.0/0', l7_para)
        pc = self._create_port_chain(ppg, fc)
        
        self._delete_port_chain(pc)
        self._delete_port_pair_group(ppg)
        self._delete_flow_classifier(fc)
        self._delete_port_pair(pp)

