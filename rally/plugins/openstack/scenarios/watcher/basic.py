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

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.watcher import utils
from rally.task import types
from rally.task import validation


class Watcher(utils.WatcherScenario):
    """Benchmark scenarios for Watcher servers."""

    @types.convert(strategy={"type": "watcher_strategy"},
                   goal={"type": "watcher_goal"})
    @validation.required_services(consts.Service.WATCHER)
    @validation.required_openstack(admin=True)
    @scenario.configure(context={"admin_cleanup": ["watcher"]})
    def create_audit_template_and_delete(self, goal, strategy, extra=None):
        """Create audit template and delete it.

        :param goal: The goal audit template is based on
        :param strategy: The strategy used to provide resource optimization
        algorithm
        :param extra: This field is used to specify some audit template
        options
        """

        extra = extra or {}
        audit_template = self._create_audit_template(goal, strategy, extra)
        self._delete_audit_template(audit_template.uuid)

    @validation.required_services(consts.Service.WATCHER)
    @scenario.configure()
    def list_audit_templates(self, name=None, goal=None, strategy=None,
                             limit=None, sort_key=None, sort_dir=None,
                             detail=False):
        """List existing audit templates.

        Audit templates are being created by Audit Template Context.

        :param name: Name of the audit template
        :param goal: Name of the goal
        :param strategy: Name of the strategy
        :param limit: The maximum number of results to return per
                      request, if:
            1) limit > 0, the maximum number of audit templates to return.
            2) limit == 0, return the entire list of audit_templates.
            3) limit param is NOT specified (None), the number of items
               returned respect the maximum imposed by the Watcher API
               (see Watcher's api.max_limit option).
        :param sort_key: Optional, field used for sorting.
        :param sort_dir: Optional, direction of sorting, either 'asc' (the
                         default) or 'desc'.
        :param detail: Optional, boolean whether to return detailed information
                       about audit_templates.
        """

        self._list_audit_templates(name=name, goal=goal, strategy=strategy,
                                   limit=limit, sort_key=sort_key,
                                   sort_dir=sort_dir, detail=detail)

    @validation.required_services(consts.Service.WATCHER)
    @validation.required_contexts("audit_templates")
    @scenario.configure(context={"admin_cleanup": ["watcher"]})
    def create_audit_and_delete(self):
        """Create and delete audit.

        Create Audit, wait until whether Audit is in SUCCEEDED state or in
        FAILED and delete audit.
        """

        audit_template_uuid = self.context["audit_templates"][0]
        audit = self._create_audit(audit_template_uuid)
        self._delete_audit(audit)
