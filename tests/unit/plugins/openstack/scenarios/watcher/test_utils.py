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
from oslo_config import cfg

from rally.plugins.openstack.scenarios.watcher import utils
from tests.unit import test

CONF = cfg.CONF


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

    def test_list_audit_templates(self):
        audit_templates_list = []
        watcher_scenario = utils.WatcherScenario(self.context)
        self.admin_clients(
            "watcher").audit_template.list.return_value = audit_templates_list
        return_audit_templates_list = watcher_scenario._list_audit_templates()
        self.assertEqual(audit_templates_list, return_audit_templates_list)
        self._test_atomic_action_timer(watcher_scenario.atomic_actions(),
                                       "watcher.list_audit_templates")

    def test_delete_audit_template(self):
        watcher_scenario = utils.WatcherScenario(self.context)
        watcher_scenario._delete_audit_template("fake_audit_template")
        self.admin_clients(
            "watcher").audit_template.delete.assert_called_once_with(
            "fake_audit_template")
        self._test_atomic_action_timer(watcher_scenario.atomic_actions(),
                                       "watcher.delete_audit_template")

    def test_create_audit(self):
        mock_audit_template = mock.Mock()
        watcher_scenario = utils.WatcherScenario(self.context)
        audit = watcher_scenario._create_audit(mock_audit_template)
        self.mock_wait_for_status.mock.assert_called_once_with(
            audit,
            ready_statuses=["SUCCEEDED"],
            failure_statuses=["FAILED"],
            status_attr="state",
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.watcher_audit_launch_poll_interval,
            timeout=CONF.benchmark.watcher_audit_launch_timeout,
            id_attr="uuid")
        self.mock_get_from_manager.mock.assert_called_once_with()
        self.admin_clients("watcher").audit.create.assert_called_once_with(
            audit_template_uuid=mock_audit_template, audit_type="ONESHOT")
        self._test_atomic_action_timer(watcher_scenario.atomic_actions(),
                                       "watcher.create_audit")

    def test_delete_audit(self):
        mock_audit = mock.Mock()
        watcher_scenario = utils.WatcherScenario(self.context)
        watcher_scenario._delete_audit(mock_audit)
        self.admin_clients("watcher").audit.delete.assert_called_once_with(
            mock_audit.uuid)
        self._test_atomic_action_timer(watcher_scenario.atomic_actions(),
                                       "watcher.delete_audit")
