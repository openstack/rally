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
