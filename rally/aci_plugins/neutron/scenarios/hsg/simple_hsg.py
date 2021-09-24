from rally import consts
from rally import exceptions
from rally.common import validation
from rally.plugins.openstack import scenario
from rally.aci_plugins import create_ostack_resources
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils
from rally.plugins.openstack.scenarios.keystone import basic as kbasic
from rally.plugins.openstack.scenarios.vm import utils as vm_utils
import time
import logging
import os
import json

logging.basicConfig(format='%(asctime)s||%(filename)s:%(lineno)s %(funcName)s||%(levelname)s||%(message)s')
logger = logging.getLogger('test_hsg')
logger.setLevel(logging.DEBUG)

@validation.add("required_services", services=[consts.Service.NOVA, consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="ScenarioPlugin.simple_hsg", context={"cleanup@openstack": ["nova", "neutron", "keystone"],
                              "keypair@openstack": {},
                              "allow_ssh@openstack": None}, platform="openstack")

class SimpleHSG(vm_utils.VMScenario, neutron_utils.NeutronScenario):

    def _remote_command(self, command, username, password, fip):
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
            raise Exception("Exception occured during remote command execution.")

    def retriable_exec(self, cmd, retries, waittime, node):
        user = node['user']
        password = node['password']
        fip = node['fip']

	result = None
	for i in range(retries):
	    try:
                if callable(cmd):
                    print 'fn try ..... %s' % (cmd.__name__)
                    cmd()
                else:
                    print 'fn try ..... %s' % (cmd['script_inline'])
		    result = self._remote_command(cmd, user, password, fip)
	    except Exception as e:
		if i < retries - 1:
		    time.sleep(waittime)
		else:
		    raise e
		continue
	    break
	return result

    def config(self, cmd, node=None):
        command = {
                "interpreter": "/bin/sh",
                "script_inline": cmd
                }
        if not node:
            node = SimpleHSG.controller_meta
        res = self.retriable_exec(command, 30, 5, node)
        return res


    def configSystemSg(self):
        cmd = self.cmdList["prefix"] + self.cmdList["group_create"]
        self.config(cmd)

    def configSubject(self):
        cmd = self.cmdList["prefix"] + self.cmdList["subject_create"]
        cmd += "rally"
        self.config(cmd)

    def configTcpRule(self, remote_ips):
        cmd_prefix = self.cmdList["prefix"] + self.cmdList["rule_create"]
        cmd_param = 'rally tcpV4In --ip_protocol=tcp  --ethertype=ipv4 --direction=egress --remote_ips=%s'%(remote_ips)
        self.config(cmd_prefix+cmd_param)

        cmd_param = 'rally tcpV4Out --ip_protocol=tcp --ethertype=ipv4 --direction=ingress --remote_ips=%s'%(remote_ips)
        self.config(cmd_prefix+cmd_param)

    def updateTcpRule(self, remote_ips):
        cmd_prefix = self.cmdList["prefix"] + self.cmdList["rule_update"]
        cmd_param = 'rally tcpV4In --ip_protocol=tcp  --ethertype=ipv4 --direction=egress --remote_ips=%s'%(remote_ips)
        self.config(cmd_prefix+cmd_param)

        cmd_param = 'rally tcpV4Out --ip_protocol=tcp --ethertype=ipv4 --direction=ingress --remote_ips=%s'%(remote_ips)
        self.config(cmd_prefix+cmd_param)

    def deleteTcpRule(self):
        cmd_prefix = self.cmdList["prefix"] + self.cmdList["rule_delete"]
        cmd_param = "rally tcpV4In"
        self.config(cmd_prefix+cmd_param)

        cmd_param = "rally tcpV4Out"
        self.config(cmd_prefix+cmd_param)

    def deleteArpRule(self):
        cmd_prefix = self.cmdList["prefix"] + self.cmdList["rule_delete"]
        cmd_param = "rally arpIn"
        self.config(cmd_prefix+cmd_param)

        cmd_param = "rally arpOut"
        self.config(cmd_prefix+cmd_param)

    def deleteSubject(self):
        cmd_prefix = self.cmdList["prefix"] + self.cmdList["subject_delete"]
        cmd_param = "rally"
        self.config(cmd_prefix+cmd_param)

    def deleteSecurityGroup(self):
        cmd_prefix = self.cmdList["prefix"] + self.cmdList["group_delete"]
        self.config(cmd_prefix)

    def getFlows(self, table):
        cmd = 'ovs-ofctl dump-flows br-int table=%d'%(table)
        command = {
                "interpreter": "/bin/sh",
                "script_inline": cmd
                }

        res = self._remote_command(command, SimpleHSG.compute_meta["user"], SimpleHSG.compute_meta["password"],SimpleHSG.compute_meta["fip"])
        res =  res.splitlines()
        return res[1:]

    def validateTcp(self, remote_ips, direction):
        table = 5
        nw = "nw_dst"
        if direction is "ingress":
            table = 3
            nw = "nw_src"

        res = self.getFlows(table)
        tcp_flows = {"origin_untracked": "ct_state=-trk,tcp,%s=%s actions=ct(table=2,zone=NXM_NX_REG6[0..15])"%(nw, remote_ips),
            "origin_new_tracked": "ct_state=+new+trk,tcp,%s=%s actions=resubmit(,%d)"%(nw, remote_ips, table+1),
            "origin_est_tracked": "ct_state=+est+trk,tcp,%s=%s actions=resubmit(,%d)"%(nw, remote_ips, table+1),
            "reply_untracked": "ct_state=-trk,tcp actions=ct(table=2,zone=NXM_NX_REG6[0..15])",
            "reply_related": "ct_state=-new-est+rel+rpl-inv+trk,ip actions=resubmit(,%d)"%(table+1),
            "reply_established": "ct_state=-new+est-rel+rpl-inv+trk,tcp actions=resubmit(,%d)"%(table+1)}

        match_flows = []
        for x in res:
            if x.find("ct_state") is  not -1:
                match_flows.append( x[x.find("ct_state"):])
            else:
                match_flows.append( x[x.find("priority"):])

        print "Verifying TCP flows in system %s table.........\n"%(direction)
        for key, value in tcp_flows.iteritems():
            if value in match_flows:
                print "# %s found.\n"  % (key)
            else:
                msg = "Fatal error: System-%s: TCP flow not found: %s" % (direction,key)
                logger.exception(msg)
                raise Exception(msg)
        print "TCP flows in System %s table.................................ok\n"%(direction)    
        self.validateBypassAndDropFlows(match_flows, direction, False)
        print "All flows  in System %s table................................ok\n"%(direction)

    def validateNoRules(self,direction):
        table = 5
        if direction is "ingress":
            table = 3

        res = self.getFlows(table)
        assert len(res) == 2
        match_flows = []
        for x in res:
            match_flows.append(x[x.find("priority"):])
        self.validateBypassAndDropFlows(match_flows, direction, True)
        print 'Flows when no system-%s rule is configured.....................ok\n'%(direction)

    def validateBypassAndDropFlows(self, match_flows, direction, norules):
        table = 5
        if direction  is 'ingress':
            table = 3 
        bypass_flow = 'priority=1 actions=resubmit(,%d)'%(table+1)
        if bypass_flow not in match_flows:
            msg = "Fatal error: System-%s: bypass flow not found"%(direction)
            logger.exception(msg)
            raise Exception(msg)
        print "Bypass flow in System %s table.................................ok\n"%(direction)

        set_field = '0x3'
        if direction == "egress":
            set_field = '0x5'

        prio = 2
        if norules:
            prio = 0
        drop_flow = '''priority=%d actions=move:NXM_NX_REG0[]->NXM_NX_TUN_METADATA0[0..31],move:NXM_NX_REG1[]->NXM_NX_TUN_METADATA1[0..31],move:NXM_NX_REG2[]->NXM_NX_TUN_METADATA2[0..31],move:NXM_NX_REG3[]->NXM_NX_TUN_METADATA3[0..31],move:NXM_NX_REG4[]->NXM_NX_TUN_METADATA4[0..31],move:NXM_NX_REG5[]->NXM_NX_TUN_METADATA5[0..31],move:NXM_NX_REG6[]->NXM_NX_TUN_METADATA6[0..31],move:NXM_NX_REG7[]->NXM_NX_TUN_METADATA7[0..31],move:NXM_NX_CT_STATE[]->NXM_NX_TUN_METADATA8[0..31],move:NXM_NX_CT_ZONE[]->NXM_NX_TUN_METADATA9[0..15],move:NXM_NX_CT_MARK[]->NXM_NX_TUN_METADATA10[0..31],move:NXM_NX_CT_LABEL[]->NXM_NX_TUN_METADATA11[0..127],set_field:%s->tun_metadata12,set_field:0->tun_metadata13,resubmit(,9)'''%(prio,set_field)
        if drop_flow not in match_flows:
            msg = "Fatal error: System-%s: drop flow not found"%(direction)
            logger.exception(msg)
            raise Exception(msg)
        print "Drop flow in System %s table.................................ok\n"%(direction)

    def configArp(self):
        cmd_prefix = self.cmdList["prefix"] + self.cmdList["rule_create"]
        cmd_param = 'rally arpIn  --ethertype=arp --direction=egress --conn_track=normal'
        self.config(cmd_prefix+cmd_param)

        cmd_param = 'rally arpOut --ethertype=arp --direction=ingress --conn_track=normal'
        self.config(cmd_prefix+cmd_param)


    def validateArp(self):
        self.validateArpUtil(3)
        self.validateArpUtil(5)

    def validateArpUtil(self, table):
        direction = "Egress"
        priority = 8064
        if table == 3:
            direction = "Ingress"
            priority = 8192


        res =  self.getFlows(table)
        arp_flow = 'priority=%d,arp actions=resubmit(,%d)' % (priority, table+1)
   
        match_flows = []
        for x in res:
            match_flows.append( x[x.find("priority"):])    
        print "Verifying ARP flow in System-%s table.........\n" % (direction)
        if arp_flow in match_flows:
            print "# Arp-%s found.\n" % (direction)
        else:
            msg = "Fatal error: System-%s: ARP flow not found" % (direction)
            logger.exception(msg)
            raise Exception(msg)
        print "ARP flow in System-%s table.................................ok\n" % (direction)


    def run(self, compute, controller, vmm_domain, user, password):
        try:
            SimpleHSG.compute_meta={'user': user,
                'password': password,
                'fip': compute}
            SimpleHSG.controller_meta={'user': user,
                'password': password,
                'fip': controller}

            self.cmdList={"prefix": "docker exec -u 0 ciscoaci_aim aimctl manager ",
                'group_create': "system-security-group-create ",
                "subject_create": "system-security-group-subject-create ",
                "rule_create": "system-security-group-rule-create ",
                "rule_update": "system-security-group-rule-update ",
                "rule_delete": "system-security-group-rule-delete ",
                "subject_delete": "system-security-group-subject-delete ",
                "group_delete": "system-security-group-delete "}

            self.configSystemSg()
            self.configSubject()
            
            #create
            remote_ips = "30.30.30.0/24"
            self.configTcpRule(remote_ips)
            self.retriable_exec(lambda: self.validateTcp(remote_ips, "ingress"), 30,5,SimpleHSG.compute_meta)
            self.retriable_exec(lambda: self.validateTcp(remote_ips, "egress"),30,5,SimpleHSG.compute_meta)

            self.configArp()
            self.retriable_exec(self.validateArp,30,5,SimpleHSG.compute_meta)

            #update
            remote_ips = "30.40.0.0/16"
            self.updateTcpRule(remote_ips)
            self.retriable_exec(lambda: self.validateTcp(remote_ips, "ingress"), 30,5,SimpleHSG.compute_meta)
            self.retriable_exec(lambda: self.validateTcp(remote_ips, "egress"),30,5,SimpleHSG.compute_meta)

            #delete
            self.deleteArpRule()
            self.deleteTcpRule()
            self.retriable_exec(lambda: self.validateNoRules("ingress"), 30, 5, SimpleHSG.compute_meta)
            self.retriable_exec(lambda: self.validateNoRules("egress"), 30, 5, SimpleHSG.compute_meta)

        except Exception as e:
	    raise e
	finally:
            self.deleteArpRule()
            self.deleteTcpRule()
            self.deleteSubject()
            self.deleteSecurityGroup()
	    print("Execution completed")
