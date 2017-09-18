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
from rally.plugins.openstack.scenarios.neutron import utils
from rally.task import validation


"""Scenarios for Neutron Security Groups."""


@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(
    context={"cleanup@openstack": ["neutron"]},
    name="NeutronSecurityGroup.create_and_list_security_groups",
    platform="openstack")
class CreateAndListSecurityGroups(utils.NeutronScenario):

    def run(self, security_group_create_args=None):
        """Create and list Neutron security-groups.

        Measure the "neutron security-group-create" and "neutron
        security-group-list" command performance.

        :param security_group_create_args: dict, POST /v2.0/security-groups
                                           request options
        """
        security_group_create_args = security_group_create_args or {}
        self._create_security_group(**security_group_create_args)
        self._list_security_groups()


@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(
    context={"cleanup@openstack": ["neutron"]},
    name="NeutronSecurityGroup.create_and_show_security_group",
    platform="openstack")
class CreateAndShowSecurityGroup(utils.NeutronScenario):

    def run(self, security_group_create_args=None):
        """Create and show Neutron security-group.

        Measure the "neutron security-group-create" and "neutron
        security-group-show" command performance.

        :param security_group_create_args: dict, POST /v2.0/security-groups
                                           request options
        """
        security_group_create_args = security_group_create_args or {}
        security_group = self._create_security_group(
            **security_group_create_args)
        msg = "security_group isn't created"
        self.assertTrue(security_group, err_msg=msg)

        self._show_security_group(security_group)


@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(
    context={"cleanup@openstack": ["neutron"]},
    name="NeutronSecurityGroup.create_and_delete_security_groups",
    platform="openstack")
class CreateAndDeleteSecurityGroups(utils.NeutronScenario):

    def run(self, security_group_create_args=None):
        """Create and delete Neutron security-groups.

        Measure the "neutron security-group-create" and "neutron
        security-group-delete" command performance.

        :param security_group_create_args: dict, POST /v2.0/security-groups
                                           request options
        """
        security_group_create_args = security_group_create_args or {}
        security_group = self._create_security_group(
            **security_group_create_args)
        self._delete_security_group(security_group)


@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(
    context={"cleanup@openstack": ["neutron"]},
    name="NeutronSecurityGroup.create_and_update_security_groups",
    platform="openstack")
class CreateAndUpdateSecurityGroups(utils.NeutronScenario):

    def run(self, security_group_create_args=None,
            security_group_update_args=None):
        """Create and update Neutron security-groups.

        Measure the "neutron security-group-create" and "neutron
        security-group-update" command performance.

        :param security_group_create_args: dict, POST /v2.0/security-groups
                                           request options
        :param security_group_update_args: dict, PUT /v2.0/security-groups
                                           update options
        """
        security_group_create_args = security_group_create_args or {}
        security_group_update_args = security_group_update_args or {}
        security_group = self._create_security_group(
            **security_group_create_args)
        self._update_security_group(security_group,
                                    **security_group_update_args)


@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(
    context={"cleanup@openstack": ["neutron"]},
    name="NeutronSecurityGroup.create_and_list_security_group_rules",
    platform="openstack")
class CreateAndListSecurityGroupRules(utils.NeutronScenario):

    def run(self, security_group_args=None,
            security_group_rule_args=None):
        """Create and list Neutron security-group-rules.

        Measure the "neutron security-group-rule-create" and "neutron
        security-group-rule-list" command performance.

        :param security_group_args: dict, POST /v2.0/security-groups
            request options
        :param security_group_rule_args: dict,
            POST /v2.0/security-group-rules request options
        """
        security_group_args = security_group_args or {}
        security_group_rule_args = security_group_rule_args or {}

        security_group = self._create_security_group(**security_group_args)
        msg = "security_group isn't created"
        self.assertTrue(security_group, err_msg=msg)

        security_group_rule = self._create_security_group_rule(
            security_group["security_group"]["id"], **security_group_rule_args)
        msg = "security_group_rule isn't created"
        self.assertTrue(security_group_rule, err_msg=msg)

        security_group_rules = self._list_security_group_rules()
        self.assertIn(security_group_rule["security_group_rule"]["id"],
                      [sgr["id"] for sgr
                       in security_group_rules["security_group_rules"]])


@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(
    context={"cleanup@openstack": ["neutron"]},
    name="NeutronSecurityGroup.create_and_show_security_group_rule",
    platform="openstack")
class CreateAndShowSecurityGroupRule(utils.NeutronScenario):

    def run(self, security_group_args=None,
            security_group_rule_args=None):
        """Create and show Neutron security-group-rule.

        Measure the "neutron security-group-rule-create" and "neutron
        security-group-rule-show" command performance.

        :param security_group_args: dict, POST /v2.0/security-groups
            request options
        :param security_group_rule_args: dict,
            POST /v2.0/security-group-rules request options
        """
        security_group_args = security_group_args or {}
        security_group_rule_args = security_group_rule_args or {}

        security_group = self._create_security_group(**security_group_args)
        msg = "security_group isn't created"
        self.assertTrue(security_group, err_msg=msg)

        security_group_rule = self._create_security_group_rule(
            security_group["security_group"]["id"], **security_group_rule_args)
        msg = "security_group_rule isn't created"
        self.assertTrue(security_group_rule, err_msg=msg)

        self._show_security_group_rule(
            security_group_rule["security_group_rule"]["id"])


@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(
    context={"cleanup@openstack": ["neutron"]},
    name="NeutronSecurityGroup.create_and_delete_security_group_rule",
    platform="openstack")
class CreateAndDeleteSecurityGroupRule(utils.NeutronScenario):

    def run(self, security_group_args=None,
            security_group_rule_args=None):
        """Create and delete Neutron security-group-rule.

        Measure the "neutron security-group-rule-create" and "neutron
        security-group-rule-delete" command performance.

        :param security_group_args: dict, POST /v2.0/security-groups
            request options
        :param security_group_rule_args: dict,
            POST /v2.0/security-group-rules request options
        """
        security_group_args = security_group_args or {}
        security_group_rule_args = security_group_rule_args or {}

        security_group = self._create_security_group(**security_group_args)
        msg = "security_group isn't created"
        self.assertTrue(security_group, err_msg=msg)

        security_group_rule = self._create_security_group_rule(
            security_group["security_group"]["id"], **security_group_rule_args)
        msg = "security_group_rule isn't created"
        self.assertTrue(security_group_rule, err_msg=msg)

        self._delete_security_group_rule(
            security_group_rule["security_group_rule"]["id"])
        self._delete_security_group(security_group)
