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


@validation.required_services(consts.Service.NEUTRON)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["neutron"]},
                    name=("NeutronSecurityGroup"
                          ".create_and_list_security_groups"))
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


@validation.required_services(consts.Service.NEUTRON)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["neutron"]},
                    name=("NeutronSecurityGroup"
                          ".create_and_delete_security_groups"))
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


@validation.required_services(consts.Service.NEUTRON)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["neutron"]},
                    name=("NeutronSecurityGroup"
                          ".create_and_update_security_groups"))
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