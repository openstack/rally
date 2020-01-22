from rally import exceptions
from rally.plugins.openstack import scenario
from rally.task import atomic
from rally.task import utils

class vCPEScenario(scenario.OpenStackScenario):
    
    
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

