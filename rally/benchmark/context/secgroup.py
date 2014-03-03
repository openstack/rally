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

from rally.benchmark.context import base
from rally.openstack.common import log as logging
from rally import osclients


LOG = logging.getLogger(__name__)

SSH_GROUP_NAME = "rally_ssh_open"


def _prepare_for_instance_ssh(endpoint):
    """Generate and store SSH keys, allows all access tcp/udp/icmp access.

    In order to run tests on instances it is necessary to have SSH access.
    This function generates an SSH key pair per user which is stored in the
    clients dictionary. The public key is also submitted to nova via the
    novaclient.

    A security group rule is created to allow access to instances on port 22.
    """
    nova = osclients.Clients(endpoint).get_nova_client()

    keypair = None
    if 'rally_ssh_key' not in [k.name for k in nova.keypairs.list()]:
        keypair = nova.keypairs.create('rally_ssh_key')

    if SSH_GROUP_NAME not in [sg.name for sg in nova.security_groups.list()]:
        descr = "Allow ssh access to VMs created by Rally for benchmarking"
        rally_open = nova.security_groups.create(SSH_GROUP_NAME, descr)

    rally_open = nova.security_groups.find(name=SSH_GROUP_NAME)

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
            "to_port": 1,
            "from_port": -1,
            "ip_range": {"cidr": "0.0.0.0/0"}
        }
    ]

    def rule_match(criteria, existing_rule):
        return all(existing_rule[key] == value
                   for key, value in criteria.iteritems())

    for new_rule in rules_to_add:
        if not any(rule_match(new_rule, existing_rule) for existing_rule
                   in rally_open.rules):
            nova.security_group_rules.create(
                        rally_open.id,
                        from_port=new_rule['from_port'],
                        to_port=new_rule['to_port'],
                        ip_protocol=new_rule['ip_protocol'],
                        cidr=new_rule['ip_range']['cidr'])

    if keypair:
        keypair = {"private": keypair.private_key,
                   "public": keypair.public_key}

    return (rally_open, keypair)


class AllowSSH(base.Context):
    __name__ = "allow_ssh"

    def __init__(self, context):
        super(AllowSSH, self).__init__(context)
        self.secgroup = []

    def setup(self):
        for user in self.context["users"]:
            secgroup, keypair = _prepare_for_instance_ssh(user["endpoint"])
            user["keypair"] = keypair
            self.secgroup.append(secgroup)

    def cleanup(self):
        for secgroup in self.secgroup:
            try:
                secgroup.delete()
            except Exception:
                LOG.warrning("Unable to delete secgroup: %s" % secgroup.id)
