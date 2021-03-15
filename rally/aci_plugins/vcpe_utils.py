import copy
import json
import itertools
from rally import exceptions
from rally.task import utils
from rally.common import cfg
from rally.task import atomic
from rally.common import logging
from rally.common import sshutils
from rally.plugins.openstack import osclients
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.vm import utils as vm_utils
from rally.plugins.openstack.wrappers import network as network_wrapper

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

class vCPEScenario(vm_utils.VMScenario, scenario.OpenStackScenario):
    
    @atomic.action_timer("run_remote_command")
    def _remote_command(self, username, password, fip, command, server, **kwargs):

        port=22
        wait_for_ping=True
        max_log_length=None

        try:
            if wait_for_ping:
                self._wait_for_ping(fip)

            code, out, err = self._run_command(
                fip, port, username, password, command=command)
            
            print out

            text_area_output = ["StdOut:"]

            if code:
                print exceptions.ScriptError(
                    "Error running command %(command)s. "
                    "Error %(code)s: %(error)s" % {
                        "command": command, "code": code, "error": err})
                print "------------------------------"
            else:
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

        return self.admin_clients("neutron").list_sfc_port_pairs()["port_pairs"]


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

        self.admin_clients("neutron").delete_sfc_port_pair(port_pair["port_pair"]["id"])



    @atomic.action_timer("neutron.create_port_pair_group")
    def _create_port_pair_group(self, portpair, **port_pair_group_create_args):

    	port_pair_group_create_args = {}
        port_pair_group_create_args["port_pairs"] = [pp["port_pair"]["id"] for pp in portpair]
        port_pair_group_create_args["name"] = self.generate_random_name()
        return self.clients("neutron").create_sfc_port_pair_group({"port_pair_group": port_pair_group_create_args})


    @atomic.action_timer("neutron.list_port_pair_groups")
    def _list_port_pair_groups(self):

        return self.admin_clients("neutron").list_sfc_port_pair_groups()["port_pair_groups"]


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

        self.admin_clients("neutron").delete_sfc_port_pair_group(port_pair_group["port_pair_group"]["id"])



    @atomic.action_timer("neutron.create_flow_classifier")
    def _create_flow_classifier(self, source_ip, dest_ip, log_src_net, log_dest_net, ethertype=None, **flow_classifier_create_args):

    	flow_classifier_create_args = {}
        flow_classifier_create_args["source_ip_prefix"] = source_ip
        flow_classifier_create_args["destination_ip_prefix"] = dest_ip
        flow_classifier_create_args["l7_parameters"] = {"logical_source_network": log_src_net, "logical_destination_network": log_dest_net}
        if ethertype:
            flow_classifier_create_args["ethertype"] = ethertype
        flow_classifier_create_args["name"] = self.generate_random_name()
        return self.clients("neutron").create_sfc_flow_classifier({"flow_classifier": flow_classifier_create_args})


    @atomic.action_timer("neutron.list_flow_classifiers")
    def _list_flow_classifiers(self):

        return self.admin_clients("neutron").list_sfc_flow_classifiers()["flow_classifiers"]


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

        self.admin_clients("neutron").delete_sfc_flow_classifier(flow_classifier["flow_classifier"]["id"])


    @atomic.action_timer("neutron.create_port_chain")
    def _create_port_chain(self, portpairgroup, flowclassifier, **port_chain_create_args):

    	port_chain_create_args = {}
        port_chain_create_args["port_pair_groups"] = [ppg["port_pair_group"]["id"] for ppg in portpairgroup]
        port_chain_create_args["flow_classifiers"] = [fc["flow_classifier"]["id"] for fc in flowclassifier]
        port_chain_create_args["name"] = self.generate_random_name()
        return self.clients("neutron").create_sfc_port_chain({"port_chain": port_chain_create_args})


    @atomic.action_timer("neutron.list_port_chains")
    def _list_port_chains(self):

        return self.admin_clients("neutron").list_sfc_port_chains()["port_chains"]


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

        self.admin_clients("neutron").delete_sfc_port_chain(port_chain["port_chain"]["id"])
    
    @atomic.action_timer("cleanup_sfc_resources")
    def cleanup_sfc(self):
        
        print "Deleting sfc resources"
        try:
            pc_list = self._list_port_chains()
            if len(pc_list):
                for pc in pc_list:
                    self._delete_port_chain({"port_chain":pc})
            fc_list = self._list_flow_classifiers()
            if len(fc_list):
                for fc in fc_list:
                    self._delete_flow_classifier({"flow_classifier":fc})
            ppg_list = self._list_port_pair_groups()
            if len(ppg_list):
                for ppg in ppg_list:
                    self._delete_port_pair_group({"port_pair_group":ppg})
            pp_list = self._list_port_pairs()
            if len(pp_list):
                for pp in pp_list:
                    self._delete_port_pair({"port_pair":pp})
        except Exception as e:
            raise e

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
    def _list_subports_by_trunk(self, trunk):

        return self.clients("neutron").trunk_get_subports(trunk["trunk"]["id"])

    @atomic.action_timer("neutron._add_subports_to_trunk")
    def _add_subports_to_trunk(self, trunk, subports):

        return self.clients("neutron").trunk_add_subports(
            trunk["trunk"]["id"], {"sub_ports": subports})

    @atomic.action_timer("neutron._remove_subports_from_trunk")
    def _remove_subports_from_trunk(self, trunk, subports):

        return self.clients("neutron").trunk_remove_subports(
            trunk["trunk"]["id"], {"sub_ports": subports})


    @atomic.action_timer("create_svi_ports")
    def _create_svi_ports(self, network, subnet, prefix, nodes, dualstack=False, v6sub=None, v6prefix=None):
              
        port_create_args = {}
        port_create_args["device_owner"] = 'apic:svi'
        port_create_args["name"] = 'apic-svi-port:' + str(nodes[1])
        port_create_args["network_id"] = network["network"]["id"]
        if dualstack:
            port_create_args.update({"fixed_ips": [{"subnet_id": subnet.get("subnet", {}).get("id"), "ip_address": prefix+".200"}, \
                    {"subnet_id": v6sub.get("subnet", {}).get("id"), "ip_address": v6prefix+"::c8"}]})
        else:
            port_create_args.update({"fixed_ips": [{"subnet_id": subnet.get("subnet", {}).get("id"), "ip_address": prefix+".200"}]})
        p2 = self.admin_clients("neutron").create_port({"port": port_create_args})
        p2_id = p2.get('port', {}).get('id')
        self.sleep_between(10,15) 

        port_list = self.admin_clients("neutron").list_ports()["ports"]
        for port in port_list:
            if (port['network_id'] == network["network"]["id"]) and (port["id"] != p2_id):
                self.admin_clients("neutron").delete_port(port["id"])

        port_create_args = {}
        port_create_args["device_owner"] = 'apic:svi'
        port_create_args["name"] = 'apic-svi-port:' + str(nodes[0])
        port_create_args["network_id"] = network["network"]["id"]
        if dualstack:
            port_create_args.update({"fixed_ips": [{"subnet_id": subnet.get("subnet", {}).get("id"), "ip_address": prefix+".199"}, \
                    {"subnet_id": v6sub.get("subnet", {}).get("id"), "ip_address": v6prefix+"::c7"}]})
        else:
            port_create_args.update({"fixed_ips": [{"subnet_id": subnet.get("subnet", {}).get("id"), "ip_address": prefix+".199"}]})
        self.admin_clients("neutron").create_port({"port": port_create_args})
        
        for i in range(1, len(nodes)-1):

            port_create_args = {}
            port_create_args["device_owner"] = 'apic:svi'
            port_create_args["name"] = 'apic-svi-port:' + str(nodes[i+1])
            port_create_args["network_id"] = network["network"]["id"]
            port_create_args.update({"fixed_ips": [{"subnet_id": subnet.get("subnet", {}).get("id"), "ip_address": prefix+"."+str(200+i)}]})
            self.admin_clients("neutron").create_port({"port": port_create_args})

    @atomic.action_timer("delete_svi_ports")
    def _delete_svi_ports(self, network):

        port_list = self.admin_clients("neutron").list_ports()["ports"]
        for port in port_list:
            if port['network_id'] == network["network"]["id"] and port['name'].startswith("apic-svi-port"):
                self.admin_clients("neutron").delete_port(port["id"])

    @atomic.action_timer("delete_all_ports")
    def _delete_all_ports(self, network):

        port_list = self.admin_clients("neutron").list_ports()["ports"]
        for port in port_list:
            if port['network_id'] == network["network"]["id"]:
                self.admin_clients("neutron").delete_port(port["id"])


    @atomic.action_timer("nova.admin_boot_server")
    def _admin_boot_server(self, image, flavor,
                 auto_assign_nic=False, **kwargs):
  
        server_name = self.generate_random_name()
        
        if auto_assign_nic and not kwargs.get("nics", False):
            nic = self._pick_random_nic()
            if nic:
                kwargs["nics"] = nic

        server = self.admin_clients("nova").servers.create(
            server_name, image, flavor, **kwargs)

        self.sleep_between(CONF.openstack.nova_server_boot_prepoll_delay)
        server = utils.wait_for_status(
            server,
            ready_statuses=["ACTIVE"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.openstack.nova_server_boot_timeout,
            check_interval=CONF.openstack.nova_server_boot_poll_interval
        )
        return server

    @atomic.action_timer("neutron.admin_create_network")
    def _admin_create_network(self, name, network_create_args):
       
        network_create_args["name"] = name
        return self.admin_clients("neutron").create_network(
            {"network": network_create_args})

    @atomic.action_timer("neutron.admin_delete_network")
    def _admin_delete_network(self, network):
       
        self.admin_clients("neutron").delete_network(network["network"]["id"])

    @atomic.action_timer("neutron.admin_create_subnet")
    def _admin_create_subnet(self, network, subnet_create_args, start_cidr=None):
        
        network_id = network["network"]["id"]

        if not subnet_create_args.get("cidr"):
            start_cidr = start_cidr or "10.2.0.0/24"
            subnet_create_args["cidr"] = (
                network_wrapper.generate_cidr(start_cidr=start_cidr))

        subnet_create_args["network_id"] = network_id
        subnet_create_args["name"] = self.generate_random_name()
        subnet_create_args.setdefault("ip_version", self.SUBNET_IP_VERSION)

        return self.admin_clients("neutron").create_subnet(
            {"subnet": subnet_create_args})

    @atomic.action_timer("neutron.admin_create_port")
    def _admin_create_port(self, network, port_create_args):
    
        port_create_args["network_id"] = network["network"]["id"]
        port_create_args["name"] = self.generate_random_name()
        return self.admin_clients("neutron").create_port({"port": port_create_args})

    @atomic.action_timer("neutron.admin_delete_port")
    def _admin_delete_port(self, port):
       
        self.admin_clients("neutron").delete_port(port["port"]["id"])

    @atomic.action_timer("neutron.delete_router")
    def _admin_delete_router(self, router):
        
        self.admin_clients("neutron").delete_router(router["router"]["id"])

    @atomic.action_timer("neutron.admin_remove_interface_router")
    def _admin_remove_interface_router(self, subnet, router):
        
        self.admin_clients("neutron").remove_interface_router(
            router["router"]["id"], {"subnet_id": subnet["subnet"]["id"]})

    @atomic.action_timer("neutron.admin_create_trunk")
    def _admin_create_trunk(self, trunk_payload):

        trunk_payload["name"] = self.generate_random_name()
        return self.admin_clients("neutron").create_trunk({"trunk": trunk_payload})

    @atomic.action_timer("neutron.admin_delete_trunk")
    def _admin_delete_trunk(self, trunk_port):

        self.admin_clients("neutron").delete_trunk(trunk_port["trunk"]["id"])

    @atomic.action_timer("neutron._admin_add_subports_to_trunk")
    def _admin_add_subports_to_trunk(self, trunk, subports):

        return self.admin_clients("neutron").trunk_add_subports(
            trunk["trunk"]["id"], {"sub_ports": subports})

    @atomic.action_timer("run_remote_command_wo_server")
    def _remote_command_wo_server(self, username, password, fip, command, **kwargs):

        port=22
        wait_for_ping=True
        max_log_length=None

        try:
            if wait_for_ping:
                self._wait_for_ping(fip)

            code, out, err = self._run_command(
                fip, port, username, password, command=command)

            print out

            text_area_output = ["StdOut:"]

            if code:
                print exceptions.ScriptError(
                    "Error running command %(command)s. "
                    "Error %(code)s: %(error)s" % {
                        "command": command, "code": code, "error": err})
                print "------------------------------"
            else:
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

    @atomic.action_timer("change_user")
    def _change_client(self, pos, context=None, admin_clients=None, clients=None):
        
        if context:
            api_info = {}
            if "api_versions@openstack" in context.get("config", {}):
                api_versions = context["config"]["api_versions@openstack"]
                for service in api_versions:
                    api_info[service] = {
                        "version": api_versions[service].get("version"),
                        "service_type": api_versions[service].get(
                            "service_type")}

            if admin_clients is None and "admin" in context:
                self._admin_clients = osclients.Clients(
                    context["admin"]["credential"], api_info)
            if clients is None:
                if "users" in context and "user" not in context:
                    self._choose_user(context)
                
                if "user" in context:
                    self._clients = osclients.Clients(context["users"][pos]["credential"], api_info)
            
        if admin_clients:
            self._admin_clients = admin_clients

        if clients:
            self._clients = clients

    @atomic.action_timer("run_remote_command_validate")
    def _remote_command_validate(self, username, password, fip, command, **kwargs):

        port=22
        wait_for_ping=True
        max_log_length=None

        try:
            if wait_for_ping:
                self._wait_for_ping(fip)

            code, out, err = self._run_command(
                fip, port, username, password, command=command)
            
            text_area_output = ["StdOut:"]

            print out

            if code:
                raise exceptions.ScriptError(
                    "Error running command %(command)s. "
                    "Error %(code)s: %(error)s" % {
                        "command": command, "code": code, "error": err})
            # Let's try to load output data
            try:
                data = json.loads(out)
                # 'echo 42' produces very json-compatible result
                #  - check it here
                if not isinstance(data, dict):
                    raise ValueError
            except ValueError:
                # It's not a JSON, probably it's 'script_inline' result
                data = []
        except (exceptions.TimeoutException,
                exceptions.SSHTimeout):
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

    def _get_domain_id(self, domain_name_or_id):

        domains = self._admin_clients.keystone("3").domains.list(
                name=domain_name_or_id)
        
        return domains[0].id

    @atomic.action_timer("keystone_v3.create_project")
    def _create_project(self, project_name, domain_name):

        project_name = project_name or self.generate_random_name()
        domain_id = self._get_domain_id(domain_name)
        
        return self._admin_clients.keystone("3").projects.create(name=project_name,
                                                           domain=domain_id)

    @atomic.action_timer("keystone_v3.delete_project")
    def _delete_project(self, project_id):

        self._admin_clients.keystone("3").projects.delete(project_id)

    @atomic.action_timer("keystone_v3.add_role")
    def _add_role(self, role_name, user_id, project_id):
        
        role_id = self._admin_clients.keystone("3").roles.list(name=role_name)[0].id
        self._admin_clients.keystone("3").roles.grant(role=role_id,
                                                user=user_id,
                                                project=project_id)

    @atomic.action_timer("keystone_v3.create_user")
    def _create_user(self, username, password, project_id, domain_name, enabled=True,
                    default_role="Admin"):
        
        domain_id = self._get_domain_id(domain_name)
        username = username or self.generate_random_name()
        user = self._admin_clients.keystone("3").users.create(
            name=username, password=password, default_project=project_id,
            domain=domain_id, enabled=enabled)

        limit = len(self._admin_clients.keystone("3").users.list())
        for i in range(0, limit):
            if self._admin_clients.keystone("3").users.list()[i].name == 'admin' :
                admin_id = self._admin_clients.keystone("3").users.list()[i].id

        if project_id:
            # we can't setup role without project_id

            self._add_role(default_role, user_id=user.id,
                                  project_id=project_id)
            self._add_role(default_role, user_id=admin_id, project_id=project_id)
        return user

    @atomic.action_timer("keystone_v3.delete_user")
    def _delete_user(self, user):
        
        self._admin_clients.keystone("3").users.delete(user)

    @atomic.action_timer("nova.user_boot_server")
    def _user_boot_server(self, image, flavor,
                 auto_assign_nic=False, **kwargs):

        server_name = self.generate_random_name()

        if auto_assign_nic and not kwargs.get("nics", False):
            nic = self._pick_random_nic()
            if nic:
                kwargs["nics"] = nic

        server = self.clients("nova").servers.create(
            server_name, image, flavor, **kwargs)

        self.sleep_between(CONF.openstack.nova_server_boot_prepoll_delay)
        server = utils.wait_for_status(
            server,
            ready_statuses=["ACTIVE"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.openstack.nova_server_boot_timeout,
            check_interval=CONF.openstack.nova_server_boot_poll_interval
        )
        return server

    def create_rally_client(self, pro_name, username, context):

        pro = self._create_project(pro_name, 'admin_domain')
        user = self._create_user(username, 'noir0123', pro.id, "admin_domain", True, "Admin")
        dic = copy.deepcopy(context)
        new_user = dic.get("users")[0]
        new_user.get("credential").update({'username': username, 'tenant_name': username, 'password': 'noir0123'})
        
        return pro, user, new_user

    def create_network_and_subnets_dual(self,
                                    network_create_args=None,
                                    subnet_create_args=None,
                                    subnets_per_network=1,
                                    subnet_cidr_start="1.0.0.0/24",
                                    dualstack = False,
                                    ipv6_subnet_args=None,
                                    subnet_ipv6_cidr_start="2001:db::/64"):
        network = self._create_network(network_create_args or {})
        self.sleep_between(5,10)
        subnets = self.create_subnets_dual(network, subnet_create_args,
                                       subnet_cidr_start, subnets_per_network,
                                       dualstack, ipv6_subnet_args, subnet_ipv6_cidr_start)
        return network, subnets

    def create_subnets_dual(self, network,
                        subnet_create_args=None,
                        subnet_cidr_start=None,
                        subnets_per_network=1,
                        dualstack = False,
                        ipv6_subnet_args=None,
                        subnet_ipv6_cidr_start="2001:db::/64"):
        
        return [self.create_subnet_dual(network, subnet_create_args or {},
                                    subnet_cidr_start, dualstack, ipv6_subnet_args,
                                    subnet_ipv6_cidr_start)
                for i in range(subnets_per_network)]

    def create_subnet_dual(self, network, subnet_create_args, start_cidr=None,
            dualstack=False, ipv6_subnet_args=None, subnet_ipv6_cidr_start=None):
        network_id = network["network"]["id"]
        subnets = []
        subnets_num = 2 if dualstack else 1
        ip_versions = itertools.cycle(
            [self.SUBNET_IP_VERSION, "6"]
            if dualstack else [self.SUBNET_IP_VERSION])
        for i in range(subnets_num):
            ip_version = next(ip_versions)
            if ip_version == "6":
                subnet_create_args = ipv6_subnet_args
            if not subnet_create_args.get("cidr"):
                if ip_version == 6:
                    start_cidr = subnet_ipv6_cidr_start or "2001:db::/64"
                else:
                    start_cidr = start_cidr or "10.2.0.0/24"
                subnet_create_args["cidr"] = (
                        network_wrapper.generate_cidr(start_cidr=start_cidr))
            subnet_create_args["network_id"] = network_id
            subnet_create_args["ip_version"] = ip_version
            subnet_create_args["name"] = self.generate_random_name()
            subnet = self.clients("neutron").create_subnet({"subnet": subnet_create_args})
            self.sleep_between(10,15)
            subnets.append(subnet)

        return subnets

    def admin_create_subnets_dual(self, network,
                        subnet_create_args=None,
                        subnet_cidr_start=None,
                        subnets_per_network=1,
                        dualstack = False,
                        ipv6_subnet_args=None,
                        subnet_ipv6_cidr_start="2001:db::/64"):

        return [self.admin_create_subnet_dual(network, subnet_create_args or {},
                                    subnet_cidr_start, dualstack, ipv6_subnet_args,
                                    subnet_ipv6_cidr_start)
                for i in range(subnets_per_network)]

    def admin_create_subnet_dual(self, network, subnet_create_args, start_cidr=None,
            dualstack=False, ipv6_subnet_args=None, subnet_ipv6_cidr_start=None):

        network_id = network["network"]["id"]
        subnets = []
        subnets_num = 2 if dualstack else 1
        ip_versions = itertools.cycle(
            [self.SUBNET_IP_VERSION, "6"]
            if dualstack else [self.SUBNET_IP_VERSION])
        for i in range(subnets_num):
            ip_version = next(ip_versions)
            if ip_version == "6":
                subnet_create_args = ipv6_subnet_args
            if not subnet_create_args.get("cidr"):
                if ip_version == 6:
                    start_cidr = subnet_ipv6_cidr_start or "2001:db::/64"
                else:
                    start_cidr = start_cidr or "10.2.0.0/24"
                subnet_create_args["cidr"] = (
                        network_wrapper.generate_cidr(start_cidr=start_cidr))
            subnet_create_args["network_id"] = network_id
            subnet_create_args["ip_version"] = ip_version
            subnet_create_args["name"] = self.generate_random_name()
            subnet = self.admin_clients("neutron").create_subnet({"subnet": subnet_create_args})
            subnets.append(subnet)

        return subnets


    @atomic.action_timer("neutron.create_address_scope")
    def create_address_scope(self, name, ip_version, shared=False, admin=False, **kwargs):
        """
                Create an Address Scope
                """
        address_scope = {"name": name, "ip_version": ip_version, "shared": shared}
        for arg, val in kwargs.items():
            address_scope[arg] = val
        body = {"address_scope": address_scope}
        if admin:
            return self.admin_clients("neutron").create_address_scope(body)
        else:
            return self.clients("neutron").create_address_scope(body)

    @atomic.action_timer("neutron.delete_address_scope")
    def delete_address_scope(self, addscope_id):

        self.admin_clients("neutron").delete_address_scope(addscope_id)

    @atomic.action_timer("neutron.create_subnet_pool")
    def create_subnet_pool(self, name, add_scope, prefixes, def_prefixlen, shared=False, admin=False, **kwargs):
        """
                Create an Address Scope
                """
        subnet_pool = {"name": name, "address_scope_id": add_scope, "prefixes": [prefixes],
                       "default_prefixlen": def_prefixlen, "shared": shared}
        for arg, val in kwargs.items():
            subnet_pool[arg] = val
        body = {"subnetpool": subnet_pool}
        if admin:
            return self.admin_clients("neutron").create_subnetpool(body)
        else:
            return self.clients("neutron").create_subnetpool(body)

    @atomic.action_timer("neutron.delete_subnet_pool")
    def delete_subnet_pool(self, subpool_id):

        self.admin_clients("neutron").delete_subnetpool(subpool_id)

    def create_subnet_with_pool(self, network, subnet_create_args, start_cidr=None):

        """Create neutron subnet from pool.
        :param network: neutron network dict
        :param subnet_create_args: POST /v2.0/subnets request options
        :returns: neutron subnet dict
        """
        network_id = network["network"]["id"]

        subnet_create_args["network_id"] = network_id
        subnet_create_args["name"] = self.generate_random_name()

        return self.clients("neutron").create_subnet(
            {"subnet": subnet_create_args})

