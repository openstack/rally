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

from rally.common import logging
from rally.common import utils
from rally.common import validation
from rally.plugins.openstack import osclients
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
    neutron = osclients.Clients(credential).neutron()
    security_groups = neutron.list_security_groups()["security_groups"]
    rally_open = [sg for sg in security_groups if sg["name"] == secgroup_name]
    if not rally_open:
        descr = "Allow ssh access to VMs created by Rally"
        rally_open = neutron.create_security_group(
            {"security_group": {"name": secgroup_name,
                                "description": descr}})["security_group"]
    else:
        rally_open = rally_open[0]

    rules_to_add = [
        {
            "protocol": "tcp",
            "port_range_max": 65535,
            "port_range_min": 1,
            "remote_ip_prefix": "0.0.0.0/0",
            "direction": "ingress"
        },
        {
            "protocol": "udp",
            "port_range_max": 65535,
            "port_range_min": 1,
            "remote_ip_prefix": "0.0.0.0/0",
            "direction": "ingress"
        },
        {
            "protocol": "icmp",
            "remote_ip_prefix": "0.0.0.0/0",
            "direction": "ingress"
        }
    ]

    def rule_match(criteria, existing_rule):
        return all(existing_rule[key] == value
                   for key, value in criteria.items())

    for new_rule in rules_to_add:
        if not any(rule_match(new_rule, existing_rule) for existing_rule
                   in rally_open.get("security_group_rules", [])):
            new_rule["security_group_id"] = rally_open["id"]
            neutron.create_security_group_rule(
                {"security_group_rule": new_rule})

    return rally_open


@validation.add("required_platform", platform="openstack", users=True)
@context.configure(name="allow_ssh", platform="openstack", order=320)
class AllowSSH(context.Context):
    """Sets up security groups for all users to access VM via SSH."""

    def setup(self):
        admin_or_user = (self.context.get("admin") or
                         self.context.get("users")[0])

        net_wrapper = network.wrap(
            osclients.Clients(admin_or_user["credential"]),
            self, config=self.config)
        use_sg, msg = net_wrapper.supports_extension("security-group")
        if not use_sg:
            LOG.info("Security group context is disabled: %s" % msg)
            return

        secgroup_name = self.generate_random_name()
        for user in self.context["users"]:
            user["secgroup"] = _prepare_open_secgroup(user["credential"],
                                                      secgroup_name)

    def cleanup(self):
        for user, tenant_id in utils.iterate_per_tenants(
                self.context["users"]):
            with logging.ExceptionLogger(
                    LOG,
                    "Unable to delete security group: %s."
                    % user["secgroup"]["name"]):
                clients = osclients.Clients(user["credential"])
                clients.neutron().delete_security_group(user["secgroup"]["id"])
