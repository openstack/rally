# Copyright 2017: Inc.
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
from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.nova import utils
from rally.task import validation


LOG = logging.getLogger(__name__)


"""Scenarios for Nova Group servers."""


@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["nova"]},
                    name="NovaServerGroups.create_and_list_server_groups",
                    platform="openstack")
class CreateAndListServerGroups(utils.NovaScenario):

    def run(self, policies=None, all_projects=False, kwargs=None):
        """Create a server group, then list all server groups.

        Measure the "nova server-group-create" and "nova server-group-list"
        command performance.

        :param policies: Server group policy
        :param all_projects: If True, display server groups from all
            projects(Admin only)
        :param kwargs: The server group specifications to add.
                       DEPRECATED, specify arguments explicitly.
        """
        if kwargs is None:
            kwargs = {
                "policies": policies
            }
        else:
            LOG.warning("The argument `kwargs` is deprecated since"
                        " Rally 0.10.0. Specify all arguments from it"
                        " explicitly.")
        server_group = self._create_server_group(**kwargs)
        msg = ("Server Groups isn't created")
        self.assertTrue(server_group, err_msg=msg)

        server_groups_list = self._list_server_groups(all_projects)
        msg = ("Server Group not included into list of server groups\n"
               "Created server group: {}\n"
               "list of server groups: {}").format(server_group,
                                                   server_groups_list)
        self.assertIn(server_group, server_groups_list, err_msg=msg)


@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["nova"]},
                    name="NovaServerGroups.create_and_get_server_group",
                    platform="openstack")
class CreateAndGetServerGroup(utils.NovaScenario):

    def run(self, policies=None, kwargs=None):
        """Create a server group, then get its detailed information.

        Measure the "nova server-group-create" and "nova server-group-get"
        command performance.

        :param policies: Server group policy
        :param kwargs: The server group specifications to add.
                       DEPRECATED, specify arguments explicitly.
        """
        if kwargs is None:
            kwargs = {
                "policies": policies
            }
        else:
            LOG.warning("The argument `kwargs` is deprecated since"
                        " Rally 0.10.0. Specify all arguments from it"
                        " explicitly.")
        server_group = self._create_server_group(**kwargs)
        msg = ("Server Groups isn't created")
        self.assertTrue(server_group, err_msg=msg)

        server_group_info = self._get_server_group(server_group.id)
        self.assertEqual(server_group.id, server_group_info.id)


@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["nova"]},
                    name="NovaServerGroups.create_and_delete_server_group",
                    platform="openstack")
class CreateAndDeleteServerGroup(utils.NovaScenario):

    def run(self, policies=None, kwargs=None):
        """Create a server group, then delete it.

        Measure the "nova server-group-create" and "nova server-group-delete"
        command performance.

        :param policies: Server group policy
        :param kwargs: The server group specifications to add.
                       DEPRECATED, specify arguments explicitly.
        """
        if kwargs is None:
            kwargs = {
                "policies": policies
            }
        else:
            LOG.warning("The argument `kwargs` is deprecated since"
                        " Rally 0.10.0. Specify all arguments from it"
                        " explicitly.")
        server_group = self._create_server_group(**kwargs)
        msg = ("Server Group isn't created")
        self.assertTrue(server_group, err_msg=msg)

        self._delete_server_group(server_group.id)
