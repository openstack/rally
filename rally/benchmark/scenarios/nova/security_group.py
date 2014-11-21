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
from rally.benchmark import validation
from rally import consts
from rally import log as logging


LOG = logging.getLogger()


class NovaSecGroup(utils.NovaScenario):

    RESOURCE_NAME_PREFIX = "rally_novasecgrp_"

    @validation.required_parameters("security_group_count",
                                    "rules_per_security_group")
    @validation.required_services(consts.Service.NOVA)
    @validation.required_openstack(users=True)
    @base.scenario(context={"cleanup": ["nova"]})
    def create_and_delete_secgroups(self, security_group_count,
                                    rules_per_security_group):
        """Tests creating and deleting security groups.

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
        """Tests creating and listing security groups.

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
