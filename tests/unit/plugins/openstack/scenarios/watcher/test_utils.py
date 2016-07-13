# Copyright 2016: Servionica LTD.
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

from rally.plugins.openstack.scenarios.watcher import utils
from tests.unit import test


class WatcherScenarioTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(WatcherScenarioTestCase, self).setUp()

    def test_create_audit_template(self):
        watcher_scenario = utils.WatcherScenario(self.context)
        watcher_scenario.generate_random_name = mock.MagicMock(
            return_value="mock_name")
        watcher_scenario._create_audit_template("fake_goal", "fake_strategy",
                                                {})
        self.admin_clients(
            "watcher").audit_template.create.assert_called_once_with(
            goal="fake_goal", strategy="fake_strategy",
            name="mock_name", extra={})
        self._test_atomic_action_timer(watcher_scenario.atomic_actions(),
                                       "watcher.create_audit_template")

    def test_delete_audit_template(self):
        watcher_scenario = utils.WatcherScenario(self.context)
        watcher_scenario._delete_audit_template("fake_audit_template")
        self.admin_clients(
            "watcher").audit_template.delete.assert_called_once_with(
            "fake_audit_template")
        self._test_atomic_action_timer(watcher_scenario.atomic_actions(),
                                       "watcher.delete_audit_template")
