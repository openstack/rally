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

from oslo_config import cfg

from rally.plugins.openstack import scenario
from rally.task import atomic
from rally.task import utils

CONF = cfg.CONF


WATCHER_BENCHMARK_OPTS = [
    cfg.FloatOpt("watcher_audit_launch_poll_interval", default=2.0,
                 help="Watcher audit launch interval"),
    cfg.IntOpt("watcher_audit_launch_timeout", default=300,
               help="Watcher audit launch timeout")
]

benchmark_group = cfg.OptGroup(name="benchmark", title="benchmark options")
CONF.register_opts(WATCHER_BENCHMARK_OPTS, group=benchmark_group)


class WatcherScenario(scenario.OpenStackScenario):
    """Base class for Watcher scenarios with basic atomic actions."""

    @atomic.action_timer("watcher.create_audit_template")
    def _create_audit_template(self, goal_id, strategy_id):
        """Create Audit Template in DB

        :param goal_id: UUID Goal
        :param strategy_id: UUID Strategy
        :return: Audit Template object
        """
        return self.admin_clients("watcher").audit_template.create(
            goal=goal_id,
            strategy=strategy_id,
            name=self.generate_random_name())

    @atomic.action_timer("watcher.delete_audit_template")
    def _delete_audit_template(self, audit_template):
        """Delete Audit Template from DB

        :param audit_template: Audit Template object
        """
        self.admin_clients("watcher").audit_template.delete(audit_template)

    @atomic.action_timer("watcher.list_audit_templates")
    def _list_audit_templates(self, name=None, goal=None, strategy=None,
                              limit=None, sort_key=None, sort_dir=None,
                              detail=False):
        return self.admin_clients("watcher").audit_template.list(
            name=name, goal=goal, strategy=strategy, limit=limit,
            sort_key=sort_key, sort_dir=sort_dir, detail=detail)

    @atomic.action_timer("watcher.create_audit")
    def _create_audit(self, audit_template_uuid):
        audit = self.admin_clients("watcher").audit.create(
            audit_template_uuid=audit_template_uuid,
            audit_type="ONESHOT")
        utils.wait_for_status(
            audit,
            ready_statuses=["SUCCEEDED"],
            failure_statuses=["FAILED"],
            status_attr="state",
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.watcher_audit_launch_timeout,
            check_interval=CONF.benchmark.watcher_audit_launch_poll_interval,
            id_attr="uuid"
        )
        return audit

    @atomic.action_timer("watcher.delete_audit")
    def _delete_audit(self, audit):
        self.admin_clients("watcher").audit.delete(audit.uuid)
