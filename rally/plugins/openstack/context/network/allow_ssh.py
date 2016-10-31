# Copyright 2013: Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from rally.common.i18n import _
from rally.common import logging
from rally.common import utils
from rally import osclients
from rally.plugins.openstack.wrappers import network
from rally.task import context


LOG = logging.getLogger(__name__)


def _prepare_open_secgroup(credential, secgroup_name):
    """Generate secgroup allowing all tcp/udp/icmp access.

    In order to run tests on instances it is necessary to have SSH access.
    This function generates a secgroup which allows all tcp/udp/icmp access.

    :param credential: clients credential
    :param secgroup_name: security group name

    :returns: dict with security group details
    """
    nova = osclients.Clients(credential).nova()

    if secgroup_name not in [sg.name for sg in nova.security_groups.list()]:
        descr = "Allow ssh access to VMs created by Rally for benchmarking"
        rally_open = nova.security_groups.create(secgroup_name, descr)

    rally_open = nova.security_groups.find(name=secgroup_name)

    rules_to_add = [
        {
            "ip_protocol": "tcp",
            "to_port": 65535,
            "from_port": 1,
            "ip_range": {"cidr": "0.0.0.0/0"}
        },
        {
            "ip_protocol": "udp",
            "to_port": 65535,
            "from_port": 1,
            "ip_range": {"cidr": "0.0.0.0/0"}
        },
        {
            "ip_protocol": "icmp",
            "to_port": -1,
            "from_port": -1,
            "ip_range": {"cidr": "0.0.0.0/0"}
        }
    ]

    def rule_match(criteria, existing_rule):
        return all(existing_rule[key] == value
                   for key, value in criteria.items())

    for new_rule in rules_to_add:
        if not any(rule_match(new_rule, existing_rule) for existing_rule
                   in rally_open.rules):
            nova.security_group_rules.create(
                rally_open.id,
                from_port=new_rule["from_port"],
                to_port=new_rule["to_port"],
                ip_protocol=new_rule["ip_protocol"],
                cidr=new_rule["ip_range"]["cidr"])

    return rally_open.to_dict()


@context.configure(name="allow_ssh", order=320)
class AllowSSH(context.Context):
    """Sets up security groups for all users to access VM via SSH."""

    @logging.log_task_wrapper(LOG.info, _("Enter context: `allow_ssh`"))
    def setup(self):
        admin_or_user = (self.context.get("admin") or
                         self.context.get("users")[0])

        net_wrapper = network.wrap(
            osclients.Clients(admin_or_user["credential"]),
            self, config=self.config)
        use_sg, msg = net_wrapper.supports_extension("security-group")
        if not use_sg:
            LOG.info(_("Security group context is disabled: %s") % msg)
            return

        secgroup_name = self.generate_random_name()
        for user in self.context["users"]:
            user["secgroup"] = _prepare_open_secgroup(user["credential"],
                                                      secgroup_name)

    @logging.log_task_wrapper(LOG.info, _("Exit context: `allow_ssh`"))
    def cleanup(self):
        for user, tenant_id in utils.iterate_per_tenants(
                self.context["users"]):
            with logging.ExceptionLogger(
                    LOG, _("Unable to delete secgroup: %s.") %
                    user["secgroup"]["name"]):
                clients = osclients.Clients(user["credential"])
                clients.nova().security_groups.get(
                    user["secgroup"]["id"]).delete()
