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

import mock

from rally.benchmark.scenarios.nova import security_group
from tests.unit import fakes
from tests.unit import test


class NovaSecurityGroupTestCase(test.TestCase):

    def test_create_and_delete_security_groups(self):
        fake_secgroups = [fakes.FakeSecurityGroup(None, None, 1, "uuid1"),
                          fakes.FakeSecurityGroup(None, None, 2, "uuid2")]

        nova_scenario = security_group.NovaSecGroup()
        nova_scenario._create_security_groups = mock.MagicMock(
            return_value=fake_secgroups)
        nova_scenario._create_rules_for_security_group = mock.MagicMock()
        nova_scenario._delete_security_groups = mock.MagicMock()

        security_group_count = 2
        rules_per_security_group = 10
        nova_scenario.create_and_delete_secgroups(
            security_group_count, rules_per_security_group)

        nova_scenario._create_security_groups.assert_called_once_with(
            security_group_count)
        nova_scenario._create_rules_for_security_group.assert_called_once_with(
            fake_secgroups, rules_per_security_group)
        nova_scenario._delete_security_groups.assert_called_once_with(
            fake_secgroups)

    def test_create_and_list_secgroups(self):
        fake_secgroups = [fakes.FakeSecurityGroup(None, None, 1, "uuid1"),
                          fakes.FakeSecurityGroup(None, None, 2, "uuid2")]

        nova_scenario = security_group.NovaSecGroup()
        nova_scenario._create_security_groups = mock.MagicMock(
            return_value=fake_secgroups)
        nova_scenario._create_rules_for_security_group = mock.MagicMock()
        nova_scenario._list_security_groups = mock.MagicMock()

        security_group_count = 2
        rules_per_security_group = 10
        nova_scenario.create_and_list_secgroups(
            security_group_count, rules_per_security_group)

        nova_scenario._create_security_groups.assert_called_once_with(
            security_group_count)
        nova_scenario._create_rules_for_security_group.assert_called_once_with(
            fake_secgroups, rules_per_security_group)
        nova_scenario._list_security_groups.assert_called_once_with()