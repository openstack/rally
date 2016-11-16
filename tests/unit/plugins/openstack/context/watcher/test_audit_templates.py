# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock

from rally.plugins.openstack.context.watcher import audit_templates
from tests.unit import fakes
from tests.unit import test


CTX = "rally.plugins.openstack.context.watcher"
SCN = "rally.plugins.openstack.scenarios.watcher"
TYP = "rally.plugins.openstack.types"


class AuditTemplateTestCase(test.ScenarioTestCase):

    @mock.patch("%s.utils.WatcherScenario._create_audit_template" % SCN,
                return_value=mock.MagicMock())
    @mock.patch("%s.WatcherStrategy.transform" % TYP,
                return_value=mock.MagicMock())
    @mock.patch("%s.WatcherGoal.transform" % TYP,
                return_value=mock.MagicMock())
    @mock.patch("%s.audit_templates.osclients" % CTX,
                return_value=fakes.FakeClients())
    def test_setup(self, mock_osclients, mock_watcher_goal_transform,
                   mock_watcher_strategy_transform,
                   mock_watcher_scenario__create_audit_template):

        users = [{"id": 1, "tenant_id": 1, "credential": mock.MagicMock()}]
        self.context.update({
            "config": {
                "audit_templates": {
                    "audit_templates_per_admin": 1,
                    "fill_strategy": "random",
                    "params": [
                        {
                            "goal": {
                                "name": "workload_balancing"
                            },
                            "strategy": {
                                "name": "workload_stabilization"
                            }
                        },
                        {
                            "goal": {
                                "name": "workload_balancing"
                            },
                            "strategy": {
                                "name": "workload_stabilization"
                            }
                        }
                    ]
                },
            },
            "admin": {
                "credential": mock.MagicMock()
            },
            "users": users
        })
        audit_template = audit_templates.AuditTemplateGenerator(self.context)
        audit_template.setup()
        goal_id = mock_watcher_goal_transform.return_value
        strategy_id = mock_watcher_strategy_transform.return_value
        mock_calls = [mock.call(goal_id, strategy_id)]
        mock_watcher_scenario__create_audit_template.assert_has_calls(
            mock_calls)

    @mock.patch("%s.audit_templates.resource_manager.cleanup" % CTX)
    def test_cleanup(self, mock_cleanup):
        audit_templates_mocks = [mock.Mock() for i in range(2)]
        self.context.update({
            "admin": {
                "credential": mock.MagicMock()
            },
            "audit_templates": audit_templates_mocks
        })
        audit_templates_ctx = audit_templates.AuditTemplateGenerator(
            self.context)
        audit_templates_ctx.cleanup()
        mock_cleanup.assert_called_once_with(
            names=["watcher.action_plan", "watcher.audit_template"],
            admin=self.context["admin"])
