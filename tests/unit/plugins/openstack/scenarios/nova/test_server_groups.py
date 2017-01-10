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

import ddt
import mock

from rally import exceptions as rally_exceptions
from rally.plugins.openstack.scenarios.nova import server_groups
from tests.unit import test

SERVER_GROUPS_MODULE = "rally.plugins.openstack.scenarios.nova.server_groups"
NOVA_SERVER_GROUPS = SERVER_GROUPS_MODULE + ".NovaServerGroups"


@ddt.ddt
class NovaServerGroupsTestCase(test.ScenarioTestCase):

    def test_create_and_list_server_groups(self):
        scenario = server_groups.CreateAndListServerGroups(self.context)
        gen_name = mock.MagicMock()
        scenario.generate_random_name = gen_name
        all_projects = False
        create_args = {"policies": ["fake_policy"]}
        fake_server_group = mock.MagicMock()
        scenario._create_server_group = mock.MagicMock()
        scenario._list_server_groups = mock.MagicMock()
        scenario._list_server_groups.return_value = [mock.MagicMock(),
                                                     fake_server_group,
                                                     mock.MagicMock()]
        # Positive case
        scenario._create_server_group.return_value = fake_server_group
        scenario.run(kwargs=create_args)
        scenario._create_server_group.assert_called_once_with(**create_args)
        scenario._list_server_groups.assert_called_once_with(all_projects)

        # Negative case1: server group isn't created
        scenario._create_server_group.return_value = None
        self.assertRaises(rally_exceptions.RallyAssertionError,
                          scenario.run,
                          kwargs=create_args)
        scenario._create_server_group.assert_called_with(**create_args)

        # Negative case2: server group not in the list of available server
        # groups
        scenario._create_server_group.return_value = mock.MagicMock()
        self.assertRaises(rally_exceptions.RallyAssertionError,
                          scenario.run,
                          kwargs=create_args)
        scenario._create_server_group.assert_called_with(**create_args)
        scenario._list_server_groups.assert_called_with(all_projects)
