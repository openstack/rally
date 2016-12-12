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

from rally import exceptions
from rally.plugins.openstack.scenarios.nova import security_group
from tests.unit import fakes
from tests.unit import test


class FakeNeutronScenario(object):
    def __enter__(self):
        return {}

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class NovaSecurityGroupTestCase(test.ScenarioTestCase):

    def test_create_and_delete_security_groups(self):
        fake_secgroups = [fakes.FakeSecurityGroup(None, None, 1, "uuid1"),
                          fakes.FakeSecurityGroup(None, None, 2, "uuid2")]

        scenario = security_group.CreateAndDeleteSecgroups(self.context)
        scenario._create_security_groups = mock.MagicMock(
            return_value=fake_secgroups)
        scenario._create_rules_for_security_group = mock.MagicMock()
        scenario._delete_security_groups = mock.MagicMock()

        security_group_count = 2
        rules_per_security_group = 10
        scenario.run(security_group_count, rules_per_security_group)

        scenario._create_security_groups.assert_called_once_with(
            security_group_count)
        scenario._create_rules_for_security_group.assert_called_once_with(
            fake_secgroups, rules_per_security_group)
        scenario._delete_security_groups.assert_called_once_with(
            fake_secgroups)

    def test_create_and_update_security_groups(self):
        fake_secgroups = [fakes.FakeSecurityGroup(None, None, 1, "uuid1"),
                          fakes.FakeSecurityGroup(None, None, 2, "uuid2")]
        scenario = security_group.CreateAndUpdateSecgroups(self.context)
        scenario._create_security_groups = mock.MagicMock(
            return_value=fake_secgroups)
        scenario._update_security_groups = mock.MagicMock()
        scenario._generate_random_name = mock.Mock(
            return_value="_updated")
        security_group_count = 2
        scenario.run(security_group_count)
        scenario._create_security_groups.assert_called_once_with(
            security_group_count)
        scenario._update_security_groups.assert_called_once_with(
            fake_secgroups)

    def test_create_and_list_secgroups(self):
        fake_secgroups = [fakes.FakeSecurityGroup(None, None, 1, "uuid1"),
                          fakes.FakeSecurityGroup(None, None, 2, "uuid2")]

        scenario = security_group.CreateAndListSecgroups(self.context)

        scenario._create_security_groups = mock.MagicMock()
        scenario._create_rules_for_security_group = mock.MagicMock()
        scenario._list_security_groups = mock.MagicMock()

        scenario._list_security_groups.return_value = fake_secgroups
        scenario._list_security_groups.return_value.append(
            fakes.FakeSecurityGroup(None, None, 3, "uuid3"))
        scenario._list_security_groups.return_value.append(
            fakes.FakeSecurityGroup(None, None, 4, "uuid4"))

        security_group_count = 2
        rules_per_security_group = 10

        # Positive case:
        scenario._create_security_groups.return_value = fake_secgroups
        scenario.run(
            security_group_count, rules_per_security_group)

        scenario._create_security_groups.assert_called_once_with(
            security_group_count)
        scenario._create_rules_for_security_group.assert_called_once_with(
            fake_secgroups, rules_per_security_group)
        scenario._list_security_groups.assert_called_once_with()

        # Negative case1: groups aren't created
        scenario._create_security_groups.return_value = None
        self.assertRaises(exceptions.RallyAssertionError,
                          scenario.run,
                          security_group_count, rules_per_security_group)
        scenario._create_security_groups.assert_called_with(
            security_group_count)

        # Negative case2: new groups are not present in the list of groups
        fake_secgroups = [fakes.FakeSecurityGroup(None, None, 6, "uuid6")]
        scenario._create_security_groups.return_value = fake_secgroups
        scenario._create_rules_for_security_group = mock.MagicMock()
        self.assertRaises(exceptions.RallyAssertionError,
                          scenario.run,
                          security_group_count, rules_per_security_group)
        scenario._create_security_groups.assert_called_with(
            security_group_count)
        scenario._create_rules_for_security_group.assert_called_with(
            fake_secgroups, rules_per_security_group)
        scenario._list_security_groups.assert_called_with()

    def _generate_fake_server_with_sg(self, number_of_secgroups):
        sg_list = []
        for i in range(number_of_secgroups):
            sg_list.append(
                fakes.FakeSecurityGroup(None, None, i, "uuid%s" % i))

        return mock.MagicMock(
            list_security_group=mock.MagicMock(return_value=sg_list)), sg_list

    def _test_boot_and_delete_server_with_secgroups(self):
        fake_server, sg_list = self._generate_fake_server_with_sg(2)

        scenario = security_group.BootAndDeleteServerWithSecgroups(
            self.context)
        scenario._create_security_groups = mock.MagicMock(
            return_value=sg_list)
        scenario._create_rules_for_security_group = mock.MagicMock()
        scenario._boot_server = mock.MagicMock(return_value=fake_server)
        scenario.generate_random_name = mock.MagicMock(
            return_value="name")
        scenario._delete_server = mock.MagicMock()
        scenario._delete_security_groups = mock.MagicMock()

        image = "img"
        flavor = 1
        security_group_count = 2
        rules_per_security_group = 10

        scenario.run(
            image, flavor, security_group_count, rules_per_security_group,
            fakearg="fakearg")
        scenario._create_security_groups.assert_called_once_with(
            security_group_count)
        scenario.generate_random_name.assert_called_once_with()
        scenario._create_rules_for_security_group.assert_called_once_with(
            sg_list, rules_per_security_group)
        scenario._boot_server.assert_called_once_with(
            "name", image, flavor,
            security_groups=[sg.name for sg in sg_list], fakearg="fakearg")
        fake_server.list_security_group.assert_called_once_with()
        scenario._delete_server.assert_called_once_with(fake_server)
        scenario._delete_security_groups.assert_called_once_with(sg_list)

    def _test_boot_and_delete_server_with_sg_not_attached(self):
        fake_secgroups = [fakes.FakeSecurityGroup(None, None, 1, "uuid1"),
                          fakes.FakeSecurityGroup(None, None, 2, "uuid2")]

        fake_server, sg_list = self._generate_fake_server_with_sg(1)

        scenario = security_group.BootAndDeleteServerWithSecgroups()
        scenario._create_security_groups = mock.MagicMock(
            return_value=fake_secgroups)
        scenario._create_rules_for_security_group = mock.MagicMock()
        scenario._boot_server = mock.MagicMock(return_value=fake_server)
        scenario.generate_random_name = mock.MagicMock(
            return_value="name")
        scenario._delete_server = mock.MagicMock()
        scenario._delete_security_groups = mock.MagicMock()

        image = "img"
        flavor = 1
        security_group_count = 2
        rules_per_security_group = 10

        self.assertRaises(security_group.NovaSecurityGroupException,
                          scenario.run,
                          image, flavor, security_group_count,
                          rules_per_security_group)

        scenario._create_security_groups.assert_called_once_with(
            security_group_count)
        scenario.generate_random_name.assert_called_once_with()
        scenario._create_rules_for_security_group.assert_called_once_with(
            fake_secgroups, rules_per_security_group)
        scenario._boot_server.assert_called_once_with(
            "name", image, flavor,
            security_groups=[sg.name for sg in fake_secgroups])
        fake_server.list_security_group.assert_called_once_with()
        scenario._delete_server.assert_called_once_with(fake_server)
        scenario._delete_security_groups.assert_called_once_with(
            fake_secgroups)

    def test_boot_server_and_add_secgroups(self):
        fake_secgroups = [fakes.FakeSecurityGroup(None, None, 1, "uuid1"),
                          fakes.FakeSecurityGroup(None, None, 2, "uuid2")]

        nova_scenario = security_group.BootServerAndAddSecgroups(self.context)
        nova_scenario._create_security_groups = mock.MagicMock(
            return_value=fake_secgroups)
        nova_scenario._create_rules_for_security_group = mock.MagicMock()
        nova_scenario._boot_server = mock.MagicMock()
        nova_scenario.add_server_secgroup = mock.MagicMock()

        image = "img"
        flavor = 1
        security_group_count = 2
        rules_per_security_group = 10

        nova_scenario.run(
            image, flavor, security_group_count, rules_per_security_group,
            fakearg="fakearg")

        nova_scenario._create_security_groups.assert_called_once_with(
            security_group_count)
        nova_scenario._create_rules_for_security_group.assert_called_once_with(
            fake_secgroups, rules_per_security_group)
        nova_scenario._boot_server.assert_called_once_with(image, flavor,
                                                           fakearg="fakearg")
