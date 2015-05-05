# Copyright 2014: Mirantis Inc.
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

from rally.benchmark.scenarios import base
from rally.benchmark.scenarios.nova import utils
from rally.benchmark import types
from rally.benchmark import validation
from rally.common.i18n import _
from rally import consts
from rally import exceptions


class NovaSecurityGroupException(exceptions.RallyException):
    msg_fmt = _("%(message)s")


class NovaSecGroup(utils.NovaScenario):
    """Benchmark scenarios for Nova security groups."""

    RESOURCE_NAME_PREFIX = "rally_novasecgrp_"

    @validation.required_parameters("security_group_count",
                                    "rules_per_security_group")
    @validation.required_services(consts.Service.NOVA)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["nova"]})
    def create_and_delete_secgroups(self, security_group_count,
                                    rules_per_security_group):
        """Create and delete security groups.

        This scenario creates N security groups with M rules per group and then
        deletes them.

        :param security_group_count: Number of security groups
        :param rules_per_security_group: Number of rules per security group
        """

        security_groups = self._create_security_groups(
            security_group_count)

        self._create_rules_for_security_group(security_groups,
                                              rules_per_security_group)

        self._delete_security_groups(security_groups)

    @validation.required_parameters("security_group_count",
                                    "rules_per_security_group")
    @validation.required_services(consts.Service.NOVA)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["nova"]})
    def create_and_list_secgroups(self, security_group_count,
                                  rules_per_security_group):
        """Create and list security groups.

        This scenario creates N security groups with M rules per group and then
        lists them.

        :param security_group_count: Number of security groups
        :param rules_per_security_group: Number of rules per security group
        """

        security_groups = self._create_security_groups(
            security_group_count)

        self._create_rules_for_security_group(security_groups,
                                              rules_per_security_group)
        self._list_security_groups()

    @types.set(image=types.ImageResourceType,
               flavor=types.FlavorResourceType)
    @validation.image_valid_on_flavor("flavor", "image")
    @validation.required_parameters("security_group_count",
                                    "rules_per_security_group")
    @validation.required_contexts("network")
    @validation.required_services(consts.Service.NOVA)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["nova"]})
    def boot_and_delete_server_with_secgroups(self, image, flavor,
                                              security_group_count,
                                              rules_per_security_group,
                                              **kwargs):
        """Boot and delete server with security groups attached.

        Plan of this scenario:
         - create N security groups with M rules per group
           vm with security groups)
         - boot a VM with created security groups
         - get list of attached security groups to server
         - delete server
         - delete all security groups
         - check that all groups were attached to server

        :param image: ID of the image to be used for server creation
        :param flavor: ID of the flavor to be used for server creation
        :param security_group_count: Number of security groups
        :param rules_per_security_group: Number of rules per security group
        :param **kwargs: Optional arguments for booting the instance
        """

        security_groups = self._create_security_groups(
            security_group_count)
        self._create_rules_for_security_group(security_groups,
                                              rules_per_security_group)

        secgroups_names = [sg.name for sg in security_groups]
        server = self._boot_server(image, flavor,
                                   security_groups=secgroups_names,
                                   **kwargs)

        action_name = "nova.get_attached_security_groups"
        with base.AtomicAction(self, action_name):
            attached_security_groups = server.list_security_group()

        self._delete_server(server)
        try:
            self._delete_security_groups(security_groups)
        except Exception as e:
            if hasattr(e, "http_status") and e.http_status == 400:
                raise NovaSecurityGroupException(e.message)
            raise

        error_message = ("Expected number of attached security groups to "
                         " server %(server)s is '%(all)s', but actual number "
                         "is '%(attached)s'." % {
                             "attached": len(attached_security_groups),
                             "all": len(security_groups),
                             "server": server})

        self.assertEqual(sorted([sg.id for sg in security_groups]),
                         sorted([sg.id for sg in attached_security_groups]),
                         error_message)