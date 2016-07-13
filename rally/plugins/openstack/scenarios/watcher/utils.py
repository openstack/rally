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

from rally.plugins.openstack import scenario
from rally.task import atomic


class WatcherScenario(scenario.OpenStackScenario):
    """Base class for Watcher scenarios with basic atomic actions."""

    @atomic.action_timer("watcher.create_audit_template")
    def _create_audit_template(self, goal_id, strategy_id, extra):
        """Create Audit Template in DB

        :param goal_id: UUID Goal
        :param strategy_id: UUID Strategy
        :param extra: Audit Template Extra (JSON Dict)
        :return: Audit Template object
        """
        return self.admin_clients("watcher").audit_template.create(
            goal=goal_id,
            strategy=strategy_id,
            name=self.generate_random_name(),
            extra=extra or {})

    @atomic.action_timer("watcher.delete_audit_template")
    def _delete_audit_template(self, audit_template):
        """Delete Audit Template from DB

        :param audit_template: Audit Template object
        """
        self.admin_clients("watcher").audit_template.delete(audit_template)
