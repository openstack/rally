# Copyright 2017 Red Hat, Inc. <http://www.redhat.com>
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

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.gnocchi import utils as gnocchiutils
from rally.task import validation

"""Scenarios for Gnocchi archive policy rule."""


@validation.add("required_services", services=[consts.Service.GNOCCHI])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="GnocchiArchivePolicyRule.list_archive_policy_rule")
class ListArchivePolicyRule(gnocchiutils.GnocchiBase):

    def run(self):
        """List archive policy rules."""
        self.gnocchi.list_archive_policy_rule()


@validation.add("required_services", services=[consts.Service.GNOCCHI])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup@openstack": ["gnocchi"]},
                    name="GnocchiArchivePolicyRule.create_archive_policy_rule")
class CreateArchivePolicyRule(gnocchiutils.GnocchiBase):

    def run(self, metric_pattern="cpu_*", archive_policy_name="low"):
        """Create archive policy rule.

        :param metric_pattern: Pattern for matching metrics
        :param archive_policy_name: Archive policy name
        """
        name = self.generate_random_name()
        self.admin_gnocchi.create_archive_policy_rule(
            name,
            metric_pattern=metric_pattern,
            archive_policy_name=archive_policy_name)


@validation.add("required_services", services=[consts.Service.GNOCCHI])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(
    context={"admin_cleanup@openstack": ["gnocchi"]},
    name="GnocchiArchivePolicyRule.create_delete_archive_policy_rule")
class CreateDeleteArchivePolicyRule(gnocchiutils.GnocchiBase):

    def run(self, metric_pattern="cpu_*", archive_policy_name="low"):
        """Create archive policy rule and then delete it.

        :param metric_pattern: Pattern for matching metrics
        :param archive_policy_name: Archive policy name
        """
        name = self.generate_random_name()
        self.admin_gnocchi.create_archive_policy_rule(
            name,
            metric_pattern=metric_pattern,
            archive_policy_name=archive_policy_name)
        self.admin_gnocchi.delete_archive_policy_rule(name)
