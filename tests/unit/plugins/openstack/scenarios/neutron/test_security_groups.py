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
from rally.plugins.openstack.scenarios.neutron import security_groups
from tests.unit import test


@ddt.ddt
class NeutronSecurityGroup(test.TestCase):

    @ddt.data(
        {},
        {"security_group_create_args": {}},
        {"security_group_create_args": {"description": "fake-description"}},
    )
    @ddt.unpack
    def test_create_and_list_security_groups(
            self, security_group_create_args=None):
        scenario = security_groups.CreateAndListSecurityGroups()

        security_group_data = security_group_create_args or {}
        scenario._create_security_group = mock.Mock()
        scenario._list_security_groups = mock.Mock()
        scenario.run(security_group_create_args=security_group_create_args)
        scenario._create_security_group.assert_called_once_with(
            **security_group_data)
        scenario._list_security_groups.assert_called_once_with()

    @ddt.data(
        {},
        {"security_group_create_args": {}},
        {"security_group_create_args": {"description": "fake-description"}},
    )
    @ddt.unpack
    def test_create_and_show_security_group(
            self, security_group_create_args=None):
        scenario = security_groups.CreateAndShowSecurityGroup()
        security_group = mock.Mock()
        security_group_data = security_group_create_args or {}
        scenario._create_security_group = mock.Mock()
        scenario._show_security_group = mock.Mock()

        # Positive case
        scenario._create_security_group.return_value = security_group
        scenario.run(security_group_create_args=security_group_create_args)
        scenario._create_security_group.assert_called_once_with(
            **security_group_data)
        scenario._show_security_group.assert_called_once_with(
            scenario._create_security_group.return_value)

    @ddt.data(
        {},
        {"security_group_create_args": {}},
        {"security_group_create_args": {"description": "fake-description"}},
    )
    @ddt.unpack
    def test_create_and_show_security_group_with_none_group(
            self, security_group_create_args=None):
        scenario = security_groups.CreateAndShowSecurityGroup()
        security_group_data = security_group_create_args or {}
        scenario._create_security_group = mock.Mock()
        scenario._show_security_group = mock.Mock()

        # Negative case: security_group isn't created
        scenario._create_security_group.return_value = None
        self.assertRaises(rally_exceptions.RallyAssertionError,
                          scenario.run, security_group_create_args)
        scenario._create_security_group.assert_called_with(
            **security_group_data)

    @ddt.data(
        {},
        {"security_group_create_args": {}},
        {"security_group_create_args": {"description": "fake-description"}},
    )
    @ddt.unpack
    def test_create_and_delete_security_groups(
            self, security_group_create_args=None):
        scenario = security_groups.CreateAndDeleteSecurityGroups()
        security_group_data = security_group_create_args or {}
        scenario._create_security_group = mock.Mock()
        scenario._delete_security_group = mock.Mock()
        scenario.run(security_group_create_args=security_group_create_args)
        scenario._create_security_group.assert_called_once_with(
            **security_group_data)
        scenario._delete_security_group.assert_called_once_with(
            scenario._create_security_group.return_value)

    @ddt.data(
        {},
        {"security_group_create_args": {}},
        {"security_group_create_args": {"description": "fake-description"}},
        {"security_group_update_args": {}},
        {"security_group_update_args": {"description": "fake-updated-descr"}},
    )
    @ddt.unpack
    def test_create_and_update_security_groups(
            self, security_group_create_args=None,
            security_group_update_args=None):
        scenario = security_groups.CreateAndUpdateSecurityGroups()
        security_group_data = security_group_create_args or {}
        security_group_update_data = security_group_update_args or {}
        scenario._create_security_group = mock.Mock()
        scenario._update_security_group = mock.Mock()
        scenario.run(security_group_create_args=security_group_create_args,
                     security_group_update_args=security_group_update_args)
        scenario._create_security_group.assert_called_once_with(
            **security_group_data)
        scenario._update_security_group.assert_called_once_with(
            scenario._create_security_group.return_value,
            **security_group_update_data)

    @ddt.data(
        {},
        {"security_group_args": {}},
        {"security_group_args": {"description": "fake-description"}},
        {"security_group_rule_args": {}},
        {"security_group_rule_args": {"description": "fake-rule-descr"}},
    )
    @ddt.unpack
    def test_create_and_list_security_group_rules(
            self, security_group_args=None,
            security_group_rule_args=None):
        scenario = security_groups.CreateAndListSecurityGroupRules()

        security_group_data = security_group_args or {}
        security_group_rule_data = security_group_rule_args or {}

        security_group = mock.MagicMock()
        security_group_rule = {"security_group_rule": {"id": 1, "name": "f1"}}
        scenario._create_security_group = mock.MagicMock()
        scenario._create_security_group_rule = mock.MagicMock()
        scenario._list_security_group_rules = mock.MagicMock()

        # Positive case
        scenario._create_security_group.return_value = security_group
        scenario._create_security_group_rule.return_value = security_group_rule
        scenario._list_security_group_rules.return_value = {
            "security_group_rules": [{"id": 1, "name": "f1"},
                                     {"id": 2, "name": "f2"},
                                     {"id": 3, "name": "f3"}]}
        scenario.run(security_group_args=security_group_data,
                     security_group_rule_args=security_group_rule_data)

        scenario._create_security_group.assert_called_once_with(
            **security_group_data)
        scenario._create_security_group_rule.assert_called_once_with(
            security_group["security_group"]["id"],
            **security_group_rule_data)
        scenario._list_security_group_rules.assert_called_once_with()

    @ddt.data(
        {},
        {"security_group_args": {}},
        {"security_group_args": {"description": "fake-description"}},
        {"security_group_rule_args": {}},
        {"security_group_rule_args": {"description": "fake-rule-descr"}},
    )
    @ddt.unpack
    def test_create_and_list_security_group_rules_with_fails(
            self, security_group_args=None,
            security_group_rule_args=None):
        scenario = security_groups.CreateAndListSecurityGroupRules()

        security_group_data = security_group_args or {}
        security_group_rule_data = security_group_rule_args or {}

        security_group = mock.MagicMock()
        security_group_rule = {"security_group_rule": {"id": 1, "name": "f1"}}
        scenario._create_security_group = mock.MagicMock()
        scenario._create_security_group_rule = mock.MagicMock()
        scenario._list_security_group_rules = mock.MagicMock()
        scenario._create_security_group_rule.return_value = security_group_rule
        scenario._list_security_group_rules.return_value = {
            "security_group_rules": [{"id": 1, "name": "f1"},
                                     {"id": 2, "name": "f2"},
                                     {"id": 3, "name": "f3"}]}

        # Negative case1: security_group isn't created
        scenario._create_security_group.return_value = None
        self.assertRaises(rally_exceptions.RallyAssertionError,
                          scenario.run,
                          security_group_data,
                          security_group_rule_data)
        scenario._create_security_group.assert_called_with(
            **security_group_data)

        # Negative case2: security_group_rule isn't created
        scenario._create_security_group.return_value = security_group
        scenario._create_security_group_rule.return_value = None
        self.assertRaises(rally_exceptions.RallyAssertionError,
                          scenario.run,
                          security_group_data,
                          security_group_rule_data)
        scenario._create_security_group.assert_called_with(
            **security_group_data)
        scenario._create_security_group_rule.assert_called_with(
            security_group["security_group"]["id"],
            **security_group_rule_data)

        # Negative case3: security_group_rule isn't listed
        scenario._create_security_group.return_value = security_group
        scenario._create_security_group_rule.return_value = mock.MagicMock()
        self.assertRaises(rally_exceptions.RallyAssertionError,
                          scenario.run,
                          security_group_data,
                          security_group_rule_data)

        scenario._create_security_group.assert_called_with(
            **security_group_data)
        scenario._create_security_group_rule.assert_called_with(
            security_group["security_group"]["id"],
            **security_group_rule_data)
        scenario._list_security_group_rules.assert_called_with()

    @ddt.data(
        {},
        {"security_group_args": {}},
        {"security_group_args": {"description": "fake-description"}},
        {"security_group_rule_args": {}},
        {"security_group_rule_args": {"description": "fake-rule-descr"}}
    )
    @ddt.unpack
    def test_create_and_show_security_group_rule(
            self, security_group_args=None,
            security_group_rule_args=None):
        scenario = security_groups.CreateAndShowSecurityGroupRule()

        security_group_data = security_group_args or {}
        security_group_rule_data = security_group_rule_args or {}
        security_group = mock.MagicMock()
        security_group_rule = {"security_group_rule": {"id": 1, "name": "f1"}}
        scenario._create_security_group = mock.MagicMock()
        scenario._create_security_group_rule = mock.MagicMock()
        scenario._show_security_group_rule = mock.MagicMock()

        # Positive case
        scenario._create_security_group.return_value = security_group
        scenario._create_security_group_rule.return_value = security_group_rule
        scenario.run(security_group_args=security_group_data,
                     security_group_rule_args=security_group_rule_data)

        scenario._create_security_group.assert_called_once_with(
            **security_group_data)
        scenario._create_security_group_rule.assert_called_once_with(
            security_group["security_group"]["id"],
            **security_group_rule_data)
        scenario._show_security_group_rule.assert_called_once_with(
            security_group_rule["security_group_rule"]["id"])

    @ddt.data(
        {},
        {"security_group_args": {}},
        {"security_group_args": {"description": "fake-description"}},
        {"security_group_rule_args": {}},
        {"security_group_rule_args": {"description": "fake-rule-descr"}}
    )
    @ddt.unpack
    def test_create_and_delete_security_group_rule(
            self, security_group_args=None,
            security_group_rule_args=None):
        scenario = security_groups.CreateAndDeleteSecurityGroupRule()

        security_group_data = security_group_args or {}
        security_group_rule_data = security_group_rule_args or {}
        security_group = mock.MagicMock()
        security_group_rule = {"security_group_rule": {"id": 1, "name": "f1"}}
        scenario._create_security_group = mock.MagicMock()
        scenario._create_security_group_rule = mock.MagicMock()
        scenario._delete_security_group_rule = mock.MagicMock()
        scenario._delete_security_group = mock.MagicMock()

        # Positive case
        scenario._create_security_group.return_value = security_group
        scenario._create_security_group_rule.return_value = security_group_rule
        scenario.run(security_group_args=security_group_data,
                     security_group_rule_args=security_group_rule_data)

        scenario._create_security_group.assert_called_once_with(
            **security_group_data)
        scenario._create_security_group_rule.assert_called_once_with(
            security_group["security_group"]["id"],
            **security_group_rule_data)
        scenario._delete_security_group_rule.assert_called_once_with(
            security_group_rule["security_group_rule"]["id"])
        scenario._delete_security_group.assert_called_once_with(
            security_group)

    @ddt.data(
        {},
        {"security_group_args": {}},
        {"security_group_args": {"description": "fake-description"}},
        {"security_group_rule_args": {}},
        {"security_group_rule_args": {"description": "fake-rule-descr"}},
    )
    @ddt.unpack
    def test_create_and_show_security_group_rule_with_fails(
            self, security_group_args=None,
            security_group_rule_args=None):
        scenario = security_groups.CreateAndShowSecurityGroupRule()

        security_group_data = security_group_args or {}
        security_group_rule_data = security_group_rule_args or {}

        security_group = mock.MagicMock()
        security_group_rule = {"security_group_rule": {"id": 1, "name": "f1"}}
        scenario._create_security_group = mock.MagicMock()
        scenario._create_security_group_rule = mock.MagicMock()
        scenario._show_security_group_rule = mock.MagicMock()
        scenario._create_security_group_rule.return_value = security_group_rule

        # Negative case1: security_group isn't created
        scenario._create_security_group.return_value = None
        self.assertRaises(rally_exceptions.RallyAssertionError,
                          scenario.run,
                          security_group_data,
                          security_group_rule_data)
        scenario._create_security_group.assert_called_with(
            **security_group_data)

        # Negative case2: security_group_rule isn't created
        scenario._create_security_group.return_value = security_group
        scenario._create_security_group_rule.return_value = None
        self.assertRaises(rally_exceptions.RallyAssertionError,
                          scenario.run,
                          security_group_data,
                          security_group_rule_data)
        scenario._create_security_group.assert_called_with(
            **security_group_data)
        scenario._create_security_group_rule.assert_called_with(
            security_group["security_group"]["id"],
            **security_group_rule_data)
