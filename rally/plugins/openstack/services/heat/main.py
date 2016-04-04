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

from oslo_config import cfg

from rally.common import utils as common_utils
from rally.task import atomic
from rally.task import utils

CONF = cfg.CONF


class Stack(common_utils.RandomNameGeneratorMixin):
    """Represent heat stack.

    Usage:
    >>> stack = Stack(scenario, task, "template.yaml", parameters={"nodes": 3})
    >>> run_benchmark(stack)
    >>> stack.update(nodes=4)
    >>> run_benchmark(stack)
    """

    def __init__(self, scenario, task, template, files, parameters=None):
        """Init heat wrapper.

        :param Scenario scenario: scenario instance
        :param Task task: task instance
        :param str template: template file path
        :param dict files: dict with file name and path
        :param dict parameters: parameters for template

        """
        self.scenario = scenario
        self.task = task
        self.template = open(template).read()
        self.files = {}
        self.parameters = parameters
        for name, path in files.items():
            self.files[name] = open(path).read()

    def _wait(self, ready_statuses, failure_statuses):
        self.stack = utils.wait_for_status(
            self.stack,
            check_interval=CONF.benchmark.heat_stack_create_poll_interval,
            timeout=CONF.benchmark.heat_stack_create_timeout,
            ready_statuses=ready_statuses,
            failure_statuses=failure_statuses,
            update_resource=utils.get_from_manager(),
        )

    def create(self):
        with atomic.ActionTimer(self.scenario, "heat.create"):
            self.stack = self.scenario.clients("heat").stacks.create(
                stack_name=self.scenario.generate_random_name(),
                template=self.template,
                files=self.files,
                parameters=self.parameters)
            self.stack_id = self.stack["stack"]["id"]
            self.stack = self.scenario.clients(
                "heat").stacks.get(self.stack_id)
            self._wait(["CREATE_COMPLETE"], ["CREATE_FAILED"])

    def update(self, data):
        self.parameters.update(data)
        with atomic.ActionTimer(self.scenario, "heat.update"):
            self.scenario.clients("heat").stacks.update(
                self.stack_id, template=self.template,
                files=self.files, parameters=self.parameters)
            self._wait(["UPDATE_COMPLETE"], ["UPDATE_FAILED"])
