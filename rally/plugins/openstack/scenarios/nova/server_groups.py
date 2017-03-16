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

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.nova import utils
from rally.task import validation


"""Scenarios for Nova Group servers."""


@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["nova"]},
                    name="NovaServerGroups.create_and_list_server_groups")
class CreateAndListServerGroups(utils.NovaScenario):

    def run(self, all_projects=False, kwargs=None):
        """Create a server group, then list all server groups.

        Measure the "nova server-group-create" and "nova server-group-list"
        command performance.

        :param all_projects: If True, display server groups from all
            projects(Admin only)
        :param kwargs: Server group name and policy
        """
        kwargs["name"] = self.generate_random_name()
        server_group = self._create_server_group(**kwargs)
        msg = ("Server Groups isn't created")
        self.assertTrue(server_group, err_msg=msg)

        server_groups_list = self._list_server_groups(all_projects)
        msg = ("Server Group not included into list of server groups\n"
               "Created server group: {}\n"
               "list of server groups: {}").format(server_group,
                                                   server_groups_list)
        self.assertIn(server_group, server_groups_list, err_msg=msg)
