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
        fake_server_group = mock.MagicMock()
        all_projects = False
        scenario._create_server_group = mock.MagicMock()
        scenario._list_server_groups = mock.MagicMock()
        scenario._list_server_groups.return_value = [mock.MagicMock(),
                                                     fake_server_group,
                                                     mock.MagicMock()]
        # Positive case and kwargs is None
        scenario._create_server_group.return_value = fake_server_group
        scenario.run(policies="fake_policy", all_projects=False, kwargs=None)
        kwargs = {
            "policies": "fake_policy"
        }
        scenario._create_server_group.assert_called_once_with(**kwargs)
        scenario._list_server_groups.assert_called_once_with(all_projects)

        # Positive case and kwargs is not None
        foo_kwargs = {
            "policies": "fake_policy"
        }
        scenario._create_server_group.return_value = fake_server_group
        scenario.run(policies=None, all_projects=False,
                     kwargs=foo_kwargs)
        scenario._create_server_group.assert_called_with(**foo_kwargs)
        scenario._list_server_groups.assert_called_with(all_projects)

        # Negative case1: server group isn't created
        scenario._create_server_group.return_value = None
        self.assertRaises(rally_exceptions.RallyAssertionError,
                          scenario.run,
                          **kwargs)
        scenario._create_server_group.assert_called_with(**kwargs)

        # Negative case2: server group not in the list of available server
        # groups
        scenario._create_server_group.return_value = mock.MagicMock()
        self.assertRaises(rally_exceptions.RallyAssertionError,
                          scenario.run,
                          **kwargs)
        scenario._create_server_group.assert_called_with(**kwargs)
        scenario._list_server_groups.assert_called_with(all_projects)

    def test_create_and_get_server_group_positive(self):
        scenario = server_groups.CreateAndGetServerGroup(self.context)
        fake_server_group = mock.MagicMock()
        fake_server_group_info = mock.MagicMock()
        fake_server_group.id = 123
        fake_server_group_info.id = 123
        scenario._create_server_group = mock.MagicMock()
        scenario._get_server_group = mock.MagicMock()
        # Positive case and kwargs is None
        kwargs = {
            "policies": "fake_policy"
        }
        scenario._create_server_group.return_value = fake_server_group
        scenario._get_server_group.return_value = fake_server_group_info
        scenario.run(policies="fake_policy", kwargs=None)
        scenario._create_server_group.assert_called_once_with(**kwargs)
        scenario._get_server_group.assert_called_once_with(
            fake_server_group.id)

        # Positive case and kwargs is not None
        scenario._create_server_group.return_value = fake_server_group
        scenario._get_server_group.return_value = fake_server_group_info
        foo_kwargs = {
            "policies": "fake_policy"
        }
        scenario.run(policies=None, kwargs=foo_kwargs)
        scenario._create_server_group.assert_called_with(**foo_kwargs)
        scenario._get_server_group.assert_called_with(
            fake_server_group.id)

    def test_create_and_get_server_group_negative(self):
        scenario = server_groups.CreateAndGetServerGroup(self.context)
        fake_server_group = mock.MagicMock()
        fake_server_group_info = mock.MagicMock()
        fake_server_group.id = 123
        fake_server_group_info.id = 123
        kwargs = {
            "policies": "fake_policy"
        }
        scenario._create_server_group = mock.MagicMock()
        scenario._get_server_group = mock.MagicMock()

        # Negative case1: server group isn't created
        scenario._create_server_group.return_value = None
        self.assertRaises(rally_exceptions.RallyAssertionError,
                          scenario.run,
                          **kwargs)
        scenario._create_server_group.assert_called_with(**kwargs)

        # Negative case2: server group to get information not the created one
        fake_server_group_info.id = 456
        scenario._create_server_group.return_value = fake_server_group
        self.assertRaises(rally_exceptions.RallyAssertionError,
                          scenario.run,
                          **kwargs)
        scenario._create_server_group.assert_called_with(**kwargs)
        scenario._get_server_group.assert_called_with(
            fake_server_group.id)

    def test_create_and_delete_server_group(self):
        scenario = server_groups.CreateAndDeleteServerGroup(self.context)
        fake_server_group = mock.MagicMock()
        scenario._create_server_group = mock.MagicMock()
        scenario._delete_server_group = mock.MagicMock()

        # Positive case and kwargs is None
        kwargs = {
            "policies": "fake_policy"
        }
        scenario._create_server_group.return_value = fake_server_group
        scenario.run(policies="fake_policy", kwargs=None)
        scenario._create_server_group.assert_called_once_with(**kwargs)
        scenario._delete_server_group.assert_called_once_with(
            fake_server_group.id)

        # Positive case and kwargs is not None
        scenario._create_server_group.return_value = fake_server_group
        foo_kwargs = {
            "policies": "fake_policy"
        }
        scenario.run(policies=None, kwargs=foo_kwargs)
        scenario._create_server_group.assert_called_with(**foo_kwargs)
        scenario._delete_server_group.assert_called_with(
            fake_server_group.id)

        # Negative case: server group isn't created
        scenario._create_server_group.return_value = None
        self.assertRaises(rally_exceptions.RallyAssertionError,
                          scenario.run,
                          **kwargs)
        scenario._create_server_group.assert_called_with(**kwargs)
