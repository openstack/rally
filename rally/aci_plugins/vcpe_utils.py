import json
from rally import exceptions
from rally.task import utils
from rally.common import cfg
from rally.task import atomic
from rally.common import logging
from rally.common import sshutils
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.vm import utils as vm_utils

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

class vCPEScenario(vm_utils.VMScenario, scenario.OpenStackScenario):

    def _remote_command(self, username, password, fip, command, server, **kwargs):

        port=22
        wait_for_ping=True
        max_log_length=None

        try:
            if wait_for_ping:
                self._wait_for_ping(fip)

            code, out, err = self._run_command(
                fip, port, username, password, command=command)
            
            print "\n"
            print out

            text_area_output = ["StdErr: %s" % (err or "(none)"),
                                "StdOut:"]

            if code:
                print exceptions.ScriptError(
                    "Error running command %(command)s. "
                    "Error %(code)s: %(error)s" % {
                        "command": command, "code": code, "error": err})
                print "\nRemote command execution failed"
                print "------------------------------"
            else:
                print "Remote command execution passed"
                print "------------------------------"
            # Let's try to load output data
            try:
                data = json.loads(out)
                if not isinstance(data, dict):
                    raise ValueError
            except ValueError:
                # It's not a JSON, probably it's 'script_inline' result
                data = []
        except (exceptions.TimeoutException,
                exceptions.SSHTimeout):
            console_logs = self._get_server_console_output(server,
                                                           max_log_length)
            LOG.debug("VM console logs:\n%s" % console_logs)
            raise

        if isinstance(data, dict) and set(data) == {"additive", "complete"}:
            for chart_type, charts in data.items():
                for chart in charts:
                    self.add_output(**{chart_type: chart})
        else:
            # it's a dict with several unknown lines
            text_area_output.extend(out.split("\n"))
            self.add_output(complete={"title": "Script Output",
                                      "chart_plugin": "TextArea",
                                      "data": text_area_output})

    
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
        port_pair_group_create_args["port_pairs"] = [pp["port_pair"]["id"] for pp in portpair]
        port_pair_group_create_args["name"] = self.generate_random_name()
        return self.clients("neutron").create_sfc_port_pair_group({"port_pair_group": port_pair_group_create_args})


    @atomic.action_timer("neutron.list_port_pair_groups")
    def _list_port_pair_groups(self):

        return self.clients("neutron").list_sfc_port_pair_groups()["port_pair_groups"]


    @atomic.action_timer("neutron.show_port_pair_group")
    def _show_port_pair_group(self, port_pair_group, **params):

        return self.clients("neutron").show_sfc_port_pair_group(port_pair_group["port_pair_group"]["id"], **params)


    @atomic.action_timer("neutron.update_port_pair_group")
    def _update_port_pair_group(self, port_pair_group, portpair, **port_pair_group_update_args):
        
        port_pair_group_update_args["port_pairs"] = [pp["port_pair"]["id"] for pp in portpair]
        port_pair_group_update_args["name"] = self.generate_random_name()
        body = {"port_pair_group": port_pair_group_update_args}
        return self.clients("neutron").update_sfc_port_pair_group(port_pair_group["port_pair_group"]["id"], body)


    @atomic.action_timer("neutron.delete_port_pair_group")
    def _delete_port_pair_group(self, port_pair_group):

        self.clients("neutron").delete_sfc_port_pair_group(port_pair_group["port_pair_group"]["id"])



    @atomic.action_timer("neutron.create_flow_classifier")
    def _create_flow_classifier(self, source_ip, dest_ip, log_src_net, log_dest_net, **flow_classifier_create_args):

    	flow_classifier_create_args = {}
        flow_classifier_create_args["source_ip_prefix"] = source_ip
        flow_classifier_create_args["destination_ip_prefix"] = dest_ip
        flow_classifier_create_args["l7_parameters"] = {"logical_source_network": log_src_net, "logical_destination_network": log_dest_net}
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
        port_chain_create_args["port_pair_groups"] = [ppg["port_pair_group"]["id"] for ppg in portpairgroup]
        port_chain_create_args["flow_classifiers"] = [fc["flow_classifier"]["id"] for fc in flowclassifier]
        port_chain_create_args["name"] = self.generate_random_name()
        return self.clients("neutron").create_sfc_port_chain({"port_chain": port_chain_create_args})


    @atomic.action_timer("neutron.list_port_chains")
    def _list_port_chains(self):

        return self.clients("neutron").list_sfc_port_chains()["port_chains"]


    @atomic.action_timer("neutron.show_port_chain")
    def _show_port_chain(self, port_chain, **params):

        return self.clients("neutron").show_sfc_port_chain(port_chain["port_chain"]["id"], **params)


    @atomic.action_timer("neutron.update_port_chain")
    def _update_port_chain(self, port_chain, portpairgroup, flowclassifier, **port_chain_update_args):

        port_chain_update_args["port_pair_groups"] = [ppg["port_pair_group"]["id"] for ppg in portpairgroup]
        port_chain_update_args["flow_classifiers"] = [fc["flow_classifier"]["id"] for fc in flowclassifier]
        port_chain_update_args["name"] = self.generate_random_name()
        body = {"port_chain": port_chain_update_args}
        return self.clients("neutron").update_sfc_port_chain(port_chain["port_chain"]["id"], body)


    @atomic.action_timer("neutron.delete_port_chain")
    def _delete_port_chain(self, port_chain):

        self.clients("neutron").delete_sfc_port_chain(port_chain["port_chain"]["id"])

    @atomic.action_timer("neutron.delete_trunk")
    def _delete_trunk(self, trunk_port):

        self.clients("neutron").delete_trunk(trunk_port["trunk"]["id"])

    @atomic.action_timer("neutron.create_trunk")
    def _create_trunk(self, trunk_payload):

        trunk_payload["name"] = self.generate_random_name()
        return self.clients("neutron").create_trunk({"trunk": trunk_payload})

    @atomic.action_timer("neutron.list_trunks")
    def _list_trunks(self, **kwargs):

        return self.clients("neutron").list_trunks(**kwargs)["trunks"]

    @atomic.action_timer("neutron.list_ports_by_device_id")
    def _list_ports_by_device_id(self, device_id):

        return self.clients("neutron").list_ports(device_id=device_id)

    @atomic.action_timer("neutron.list_subports_by_trunk")
    def _list_subports_by_trunk(self, trunk_id):

        return self.clients("neutron").trunk_get_subports(trunk_id)

    @atomic.action_timer("neutron._add_subports_to_trunk")
    def _add_subports_to_trunk(self, trunk_id, subports):

        return self.clients("neutron").trunk_add_subports(
            trunk_id, {"sub_ports": subports})

