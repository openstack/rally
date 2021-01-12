from pyaci import Node
from rally import consts
from rally import exceptions
from rally.common import validation
from rally.plugins.openstack import scenario
from rally.aci_plugins import create_ostack_resources
from rally.cli import envutils
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils
from rally.plugins.openstack.scenarios.keystone import basic as kbasic
from rally.plugins.openstack.scenarios.vm import utils as vm_utils
import time
import logging
import os
import json

logging.basicConfig(format='%(asctime)s||%(filename)s:%(lineno)s %(funcName)s||%(levelname)s||%(message)s')
logger = logging.getLogger('test_qos')
logger.setLevel(logging.DEBUG)

@validation.add("required_services", services=[consts.Service.NOVA, consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="ScenarioPlugin.simple_qos", context={"cleanup@openstack": ["nova", "neutron", "keystone"],
                              "keypair@openstack": {},
                              "allow_ssh@openstack": None}, platform="openstack")

class SimpleQOS(create_ostack_resources.CreateOstackResources,vm_utils.VMScenario, neutron_utils.NeutronScenario, kbasic.KeystoneBasic
                ):

    def _remote_command(self, username, password, fip, command):
        port=22
        wait_for_ping=True
        max_log_length=None

        try:
            if wait_for_ping:
                self._wait_for_ping(fip)

            code, out, err = self._run_command(
                fip, port, username, password, command=command)

            if code:
                print exceptions.ScriptError(
                    "Error running command %(command)s. "
                    "Error %(code)s: %(error)s" % {
                        "command": command, "code": code, "error": err})
                print "------------------------------"
            return out
        except (exceptions.TimeoutException,
                exceptions.SSHTimeout):
            raise


    def retriable_delete(self, node, dn, retries, waittime):
	for i in range(retries):
	    print 'dn try ..... %s %s' % (dn, i)
	    result = node.mit.FromDn(dn).GET()
	    if not result or len(result) == 0:
		break
	    time.sleep(waittime)
	if result and  len(result) > 0:
	    raise Exception("dn %s still not deleted on node" % dn)
	return result


    def retriable_exec(self, fn, args, retries, waittime):
	result = None
	for i in range(retries):
	    print 'fn try ..... %s %s' % (fn, i)
	    try:
		result = fn(*args)
	    except:
		if i < retries - 1:
		    time.sleep(waittime)
		else:
		    logger.exception("Fatal error")
		    raise
		continue
	    break
	return result


    def verify_dict(self, result, expected):
	for i in expected.items():
	    try:
		assert str(i[1]) ==  getattr(result, i[0])
	    except:
		print "Expected: %s" % i[1]
		print "Got: %s" % getattr(result, i[0])
		raise


    def retriable_fetch(self, node, dn, retries, waittime):
	for i in range(retries):
	    print 'dn try ..... %s %s' % (dn, i)
	    result = node.mit.FromDn(dn).GET()
	    if result and  len(result) > 0:
		break
	    time.sleep(waittime)
	if not result or len(result) == 0:
	    raise Exception("dn %s not found on node" % dn)
	return result


    def retriable_fetch_verify(self, node, dn, expected, retries, waittime):
	for i in range(retries):
	    print 'fetch_verify try ..... %s %s' % (dn, i)
	    try:
		result = self.retriable_fetch(node, dn, retries, waittime)
		self.verify_dict(result[0], expected)
		return
	    except:
		time.sleep(waittime)
	logger.exception("Fatal error")


    def getPortFromServer(self, server):
        ports = self.admin_clients("neutron").list_ports(device_id=server.id)
        port = ports["ports"][0]
        return port


    def getComputeNode(self, compute1, compute2, interface, user, password):
        try:
            if  not compute1 or not compute2:
                return ""

            command = {
                        "interpreter": "/bin/sh",
                        "script_inline": "ovs-vsctl list interface %s" % (interface)
                    }
            data = self._remote_command(user, password, compute1, command)
            print data
            if not data:
                data = self._remote_command(user, password, compute2, command)
                if not data:
                    return ""
                else:
                    return compute2
            else:
                return compute1
        except Exception as e:
            logger.exception("Compute node not found")
        return ""


    def fetchEgressParams(self, interface, compute, user, password):
        try:
            command = {
                        "interpreter": "/bin/sh",
                        "script_inline": "ovs-vsctl list interface %s" % (interface)
                    }
            data = self._remote_command(user, password, compute, command)
            row = data.splitlines()
            burst = row[15].replace(" ", "").split(':')[1]
            rate = row[16].replace(" ", "").split(':')[1]
            return int(rate), int(burst)
        except Exception as e:
            logger.exception("Fatal error fetching egress params")
            raise


    def verifyEgressParams(self, rate, burst, interface, compute, user, password, retries, waittime):
        for i in range(retries):
            print 'fetch and verify egress params for %s, try %d' % (interface, i)
            try:
                ovsRate, ovsBurst = self.fetchEgressParams(interface, compute, user, password)
                assert rate == ovsRate and burst == ovsBurst
                print 'Egress params verified.'
                return
            except:
                time.sleep(waittime)
        raise Exception("Egress parameter verification failed")


    def fetchIngressParams(self, interface, compute, user, password):
        try:
            command = {
                        "interpreter": "/bin/sh",
                        "script_inline": "ovs-vsctl list port %s" % (interface)
                    }
            data = self._remote_command(user, password, compute, command)
            row = data.splitlines()
            qos = row[15].replace(" ", "").split(':')[1]
            if not qos :
                return 0, 0
            command = {
                        "interpreter": "/bin/sh",
                        "script_inline": "ovs-vsctl list qos %s" % (qos)
                    }
            data = self._remote_command(user, password, compute, command)
            row = data.splitlines()
            queue = row[3].replace(" ", "").split(':')[1][1:-1].split('=')[1]

            command = {
                        "interpreter": "/bin/sh",
                        "script_inline": "ovs-vsctl list queue %s" % (queue)
                    }
            data =  self._remote_command(user, password, compute, command)
            row = data.splitlines()
            burst = row[3].replace(" ", "").split(':')[1][1:-1].split(',')[0].split('=')[1][1:-1]
            rate = row[3].replace(" ", "").split(':')[1][1:-1].split(',')[1].split('=')[1][1:-1]

            return int(rate), int(burst)
        except Exception as e:
            logger.exception("Fatal error fetching ingress params")
            raise


    def verifyIngressParams(self, rate, burst, interface, compute, user, password, retries, waittime):
        for i in range(retries):
            print 'fetch and verify egress params for %s, try..... %d' % (interface, i)
            try:
                resRate, resBurst = self.fetchIngressParams(interface, compute, user, password)
                assert resRate == rate*1024 and resBurst == burst*1024
                print "Ingress params verified"
                return
            except:
                time.sleep(waittime)
        raise Exception("Ingress parameter verification failed")


    def run(self, imageid, flavorid, apic, leaf1, leaf2, compute1, compute2, user, password):
        try:
            metagen_cmd = "rmetagen.py -u admin -p ins3965! " + apic
            os.system(metagen_cmd)
            project_name = envutils.get_project_name_from_env()

            projects = self.admin_keystone.list_projects()
            for i in projects:
                if i.name == project_name:
                    pid = i.id
            print "---- Testing create ----"

            qos_name = 'sample_qos1'
            qos_body = {'policy': {'name': qos_name}}
            bw_rules = [{'bandwidth_limit_rule': {'max_kbps': 4000, 'direction': 'egress', 'max_burst_kbps': 400}},
                     {'bandwidth_limit_rule': {'max_kbps': 6000, 'direction': 'ingress', 'max_burst_kbps': 600}}]
            dscp_rule = {'dscp_marking_rule': {'dscp_mark': 26 }}

            print "OSP create qos..."
            qosp = self.admin_clients("neutron").create_qos_policy(body=qos_body)
            print qosp
            print('QoS %s created' % qosp['policy']['id'])

            i_rslt = None
            e_rslt = None
            print "OSP create bandwidth rules..."
            for r in bw_rules:
                rslt = self.admin_clients("neutron").create_bandwidth_limit_rule(qosp['policy']['id'], r)
                print rslt
                if r['bandwidth_limit_rule']['direction'] == 'ingress':
                    i_rslt = rslt
                else:
                    e_rslt = rslt
            print "OSP create dscp rule..."
            dscp_rslt = self.admin_clients("neutron").create_dscp_marking_rule(qosp['policy']['id'], dscp_rule)

            network_name = 'sample_network1'
            body_sample = {'network': {'name': network_name,
                       'qos_policy_id': qosp['policy']['id'],
                       'admin_state_up': True}}

            print "OSP create network..."
            network_id = None
            netw = self.admin_clients("neutron").create_network(body=body_sample)
            net_dict = netw['network']
            network_id = net_dict['id']
            print('Network %s created' % network_id)

            body_create_subnet = {'subnets': [{'cidr': '192.168.199.0/24',
                                  'ip_version': 4, 'network_id': network_id}]}

            print "OSP create subnet..."
            subnet = self.admin_clients("neutron").create_subnet(body=body_create_subnet)

            print "OSP create vm..."
            server = self.admin_clients("nova").servers.create(name = "auto-test"+str(int(time.time())),
                                        image = imageid,
                                        flavor = flavorid,
                                        nics = [{'net-id':network_id}]
                                        )

            ports = self.admin_clients("neutron").list_ports(device_id=server.id)
            port = self.retriable_exec(lambda x:self.getPortFromServer(x), [server], 30, 5)
            portUuid =  port.get("id")
            interface = "tap" + portUuid[0:10]

            print "tap interface name: %s" %(interface)
            compute = None
            compute = self.getComputeNode(compute1, compute2, interface, user, password)
            if compute:
                print "found compute node: %s" % (compute)
            else:
                print "No compute node found, skipping ovsdb verifications"

            time.sleep(15)
            apic = 'https://' + apic
            apic = Node(apic)
            apic.methods.Login('admin', 'ins3965!').POST()
            result = apic.mit.polUni().fvTenant('prj_'+pid).qosRequirement(qosp['policy']['id']).GET()
            if not result or len(result) == 0:
                raise Exception("qos %s not found on apic" % qosp['policy']['id'])

            # QosRequirement, QosRsIngressDppPol, QosRsEgressDppPol, QosDppPol (egress/ingress)
            # QosDppPolDef (egress/ingress)
            tn_dn = 'uni/tn-prj_'+pid
            qos_req = { 'dn': tn_dn+'/qosreq-'+qosp['policy']['id'],
                    'ingressDppPolDn': tn_dn+'/qosdpppol-'+i_rslt['bandwidth_limit_rule']['id'],
                    'egressDppPolDn': tn_dn+'/qosdpppol-'+e_rslt['bandwidth_limit_rule']['id'],
                    'name': qosp['policy']['id']
                    }
            rs_in = {
                    'dn': tn_dn+'/qosreq-'+qosp['policy']['id']+'/rsingressDppPol',
                    'tnQosDppPolName': i_rslt['bandwidth_limit_rule']['id'],
                    }
            rs_eg = {
                    'dn': tn_dn+'/qosreq-'+qosp['policy']['id']+'/rsegressDppPol',
                    'tnQosDppPolName': e_rslt['bandwidth_limit_rule']['id'],
                    }
            in_dpp = { 'dn': tn_dn+'/qosdpppol-'+i_rslt['bandwidth_limit_rule']['id'],
                    'rate': 6000, 'burst': 600, 'rateUnit': 'kilo', 'burstUnit': 'kilo' }
            eg_dpp = { 'dn': tn_dn+'/qosdpppol-'+e_rslt['bandwidth_limit_rule']['id'],
                    'rate': 4000, 'burst': 400, 'rateUnit': 'kilo', 'burstUnit': 'kilo' }
            in_dpp_def = { 'dn': 'qosdpppolcont/qosdpppold-['+tn_dn+'/qosdpppol-'+i_rslt['bandwidth_limit_rule']['id']+']',
                    'rate': 6000, 'burst': 600, 'rateUnit': 'kilo', 'burstUnit': 'kilo' }
            eg_dpp_def = { 'dn': 'qosdpppolcont/qosdpppold-['+tn_dn+'/qosdpppol-'+e_rslt['bandwidth_limit_rule']['id']+']',
                    'rate': 4000, 'burst': 400, 'rateUnit': 'kilo', 'burstUnit': 'kilo' }

            dscp_dict = {
                "CS0": 0,
                "CS1": 8,
                "AF11": 10,
                "AF12": 12,
                "AF13": 14,
                "CS2": 16,
                "AF21": 18,
                "AF22": 20,
                "AF23": 22,
                "CS3": 24,
                "AF31": 26,
                "AF32": 28,
                "AF33": 30,
                "CS4": 32,
                "AF41": 34,
                "AF42": 36,
                "AF43": 38,
                "CS5": 40,
                "VA": 44,
                "EF": 46,
                "CS6": 48,
                "CS7": 56,}
            inv_dscp_dict = {v: k for k, v in dscp_dict.items()}

            # QosDscp_Marking, qosRsQosRequirement
            dscp = { 'dn': tn_dn+'/qosreq-'+qosp['policy']['id']+'/dscp_marking',
                     'mark': inv_dscp_dict[dscp_rule['dscp_marking_rule']['dscp_mark']] }
            rs_epg = { 'dn': tn_dn+'/ap-OpenStack/epg-net_'+network_id+'/rsqosRequirement',
                       'tnQosRequirementName': qosp['policy']['id'],
                       'tDn': qos_req['dn'] }
            result = None
            self.retriable_fetch_verify(apic, qos_req['dn'], qos_req, 30, 5)
            self.retriable_fetch_verify(apic, rs_in['dn'], rs_in, 30, 5)
            self.retriable_fetch_verify(apic, rs_eg['dn'], rs_eg, 30, 5)
            self.retriable_fetch_verify(apic, in_dpp['dn'], in_dpp, 30, 5)
            self.retriable_fetch_verify(apic, eg_dpp['dn'], eg_dpp, 30, 5)
            self.retriable_fetch_verify(apic, dscp['dn'], dscp, 30, 5)
            self.retriable_fetch_verify(apic, rs_epg['dn'], rs_epg, 30, 5)
            #print result[0].Xml
            print "Apic................................ok"

            leaf1 = "https://" + leaf1
            leaf2 = "https://" + leaf2
            lnodes = [Node(leaf1), Node(leaf2)]
            for leaf in lnodes:
                leaf.methods.Login('admin', 'ins3965!').POST()
            leaf = None
            for i in range(30):
                print 'Leaf try..... %s' % i
                for l in lnodes:
                    result = l.mit.FromDn(qos_req['dn']).GET()
                    if result and  len(result) > 0:
                        leaf = l
                        break
                if leaf:
                    break
                time.sleep(5)
            if not result or len(result) == 0:
                raise Exception("qos %s not found on leaf" % qosp['policy']['id'])
            print 'leaf is %s' % leaf
            self.verify_dict(result[0], qos_req)
            self.retriable_fetch_verify(leaf, in_dpp_def['dn'], in_dpp_def, 30, 5)

            self.retriable_fetch_verify(leaf, eg_dpp_def['dn'], eg_dpp_def, 30, 5)

            self.retriable_fetch_verify(leaf, dscp['dn'], dscp, 30, 5)

            print "Leaf................................ok"

            if compute:
                self.verifyEgressParams(4000, 400, interface, compute, user, password, 1, 5)
                self.verifyIngressParams(6000, 600, interface, compute, user, password, 1, 5)
                print "OVS.................................ok"

            print "\n---- Testing update ----"
            self.admin_clients("neutron").update_bandwidth_limit_rule(i_rslt['bandwidth_limit_rule']['id'], qosp['policy']['id'], {'bandwidth_limit_rule': {'max_kbps': 6100, 'direction': 'ingress', 'max_burst_kbps': 610}})
            self.admin_clients("neutron").update_bandwidth_limit_rule(e_rslt['bandwidth_limit_rule']['id'], qosp['policy']['id'], {'bandwidth_limit_rule': {'max_kbps': 4100, 'direction': 'egress', 'max_burst_kbps': 410}})
            in_dpp = { 'dn': tn_dn+'/qosdpppol-'+i_rslt['bandwidth_limit_rule']['id'],
                       'rate': 6100, 'burst': 610, 'rateUnit': 'kilo', 'burstUnit': 'kilo' }
            eg_dpp = { 'dn': tn_dn+'/qosdpppol-'+e_rslt['bandwidth_limit_rule']['id'],
                       'rate': 4100, 'burst': 410, 'rateUnit': 'kilo', 'burstUnit': 'kilo' }
            in_dpp_def = { 'dn': 'qosdpppolcont/qosdpppold-['+tn_dn+'/qosdpppol-'+i_rslt['bandwidth_limit_rule']['id']+']',
                       'rate': 6100, 'burst': 610, 'rateUnit': 'kilo', 'burstUnit': 'kilo' }
            eg_dpp_def = { 'dn': 'qosdpppolcont/qosdpppold-['+tn_dn+'/qosdpppol-'+e_rslt['bandwidth_limit_rule']['id']+']',
                       'rate': 4100, 'burst': 410, 'rateUnit': 'kilo', 'burstUnit': 'kilo' }
            self.retriable_fetch_verify(apic, in_dpp['dn'], in_dpp, 30, 5)
            self.retriable_fetch_verify(apic, eg_dpp['dn'], eg_dpp, 30, 5)
            print "Apic................................ok"
            self.retriable_fetch_verify(leaf, in_dpp_def['dn'], in_dpp_def, 30, 5)
            self.retriable_fetch_verify(leaf, eg_dpp_def['dn'], eg_dpp_def, 30, 5)
            print "Leaf................................ok"

            if compute:
                self.verifyEgressParams(4100, 410, interface, compute, user, password, 1, 5)
                self.verifyIngressParams(6100, 610, interface, compute, user, password, 1, 5)
                print "OVS.................................ok"

            print "\n---- Testing delete ----"
            print "Deleting vm..."
            self.admin_clients("nova").servers.delete(server)
            server = None
            print "Deleting network..."
            self.retriable_exec(lambda x:self.admin_clients("neutron").delete_network(x), [network_id], 30, 5)
            self.retriable_delete(apic, rs_epg['dn'], 30, 5)
            network_id = None
            print "Apic................................ok"
            self.retriable_delete(leaf, in_dpp_def['dn'], 30, 5)
            self.retriable_delete(leaf, eg_dpp_def['dn'], 30, 5)
            self.retriable_delete(leaf, dscp['dn'], 30, 5)
            self.retriable_delete(leaf, qos_req['dn'], 30, 5)
            print "Leaf................................ok"
            print "Deleting qos..."
            self.retriable_exec(lambda x:self.admin_clients("neutron").delete_qos_policy(x), [qosp['policy']['id']], 30, 5)
            qosp = None
            self.retriable_delete(apic, qos_req['dn'], 30, 5)
            self.retriable_delete(apic, rs_in['dn'], 30, 5)
            self.retriable_delete(apic, rs_eg['dn'], 30, 5)
            self.retriable_delete(apic, in_dpp['dn'], 30, 5)
            self.retriable_delete(apic, eg_dpp['dn'], 30, 5)
            self.retriable_delete(apic, dscp['dn'], 30, 5)
            print "Apic................................ok"

            if compute:
                self.verifyEgressParams(0, 0, interface, compute, user, password, 1, 5)
                self.verifyIngressParams(0, 0, interface, compute, user, password, 1, 5)
                print "OVS.................................ok"

        except Exception as e:
	    raise e
	finally:
	    if server:
		self.admin_clients("nova").servers.delete(server)
	    if network_id:
	        self.retriable_exec(lambda x:self.admin_clients("neutron").delete_network(x), [network_id], 30, 5)
	        print('Deleted Network %s' % network_id)
	    if qosp:
	        self.retriable_exec(lambda x:self.admin_clients("neutron").delete_qos_policy(x), [qosp['policy']['id']], 30, 5)
	        print('Deleted QoS %s' % qosp['policy']['id'])
	    print("Execution completed")


