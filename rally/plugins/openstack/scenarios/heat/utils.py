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

import time

from oslo_config import cfg

from rally.benchmark.scenarios import base
from rally.benchmark import utils as bench_utils


HEAT_BENCHMARK_OPTS = [
    cfg.FloatOpt("heat_stack_create_prepoll_delay",
                 default=2.0,
                 help="Time(in sec) to sleep after creating a resource before "
                      "polling for it status."),
    cfg.FloatOpt("heat_stack_create_timeout",
                 default=3600.0,
                 help="Time(in sec) to wait for heat stack to be created."),
    cfg.FloatOpt("heat_stack_create_poll_interval",
                 default=1.0,
                 help="Time interval(in sec) between checks when waiting for "
                      "stack creation."),
    cfg.FloatOpt("heat_stack_delete_timeout",
                 default=3600.0,
                 help="Time(in sec) to wait for heat stack to be deleted."),
    cfg.FloatOpt("heat_stack_delete_poll_interval",
                 default=1.0,
                 help="Time interval(in sec) between checks when waiting for "
                      "stack deletion."),
    cfg.FloatOpt("heat_stack_check_timeout",
                 default=3600.0,
                 help="Time(in sec) to wait for stack to be checked."),
    cfg.FloatOpt("heat_stack_check_poll_interval",
                 default=1.0,
                 help="Time interval(in sec) between checks when waiting for "
                      "stack checking."),
    cfg.FloatOpt("heat_stack_update_prepoll_delay",
                 default=2.0,
                 help="Time(in sec) to sleep after updating a resource before "
                      "polling for it status."),
    cfg.FloatOpt("heat_stack_update_timeout",
                 default=3600.0,
                 help="Time(in sec) to wait for stack to be updated."),
    cfg.FloatOpt("heat_stack_update_poll_interval",
                 default=1.0,
                 help="Time interval(in sec) between checks when waiting for "
                      "stack update."),
    cfg.FloatOpt("heat_stack_suspend_timeout",
                 default=3600.0,
                 help="Time(in sec) to wait for stack to be suspended."),
    cfg.FloatOpt("heat_stack_suspend_poll_interval",
                 default=1.0,
                 help="Time interval(in sec) between checks when waiting for "
                      "stack suspend."),
    cfg.FloatOpt("heat_stack_resume_timeout",
                 default=3600.0,
                 help="Time(in sec) to wait for stack to be resumed."),
    cfg.FloatOpt("heat_stack_resume_poll_interval",
                 default=1.0,
                 help="Time interval(in sec) between checks when waiting for "
                      "stack resume."),
]

CONF = cfg.CONF
benchmark_group = cfg.OptGroup(name="benchmark", title="benchmark options")
CONF.register_opts(HEAT_BENCHMARK_OPTS, group=benchmark_group)


class HeatScenario(base.Scenario):
    """Base class for Heat scenarios with basic atomic actions."""

    @base.atomic_action_timer("heat.list_stacks")
    def _list_stacks(self):
        """Return user stack list."""

        return list(self.clients("heat").stacks.list())

    @base.atomic_action_timer("heat.create_stack")
    def _create_stack(self, template, parameters=None,
                      files=None, environment=None):
        """Create a new stack.

        :param template: template with stack description.
        :param parameters: template parameters used during stack creation
        :param files: additional files used in template
        :param environment: stack environment definition

        :returns: object of stack
        """
        stack_name = self._generate_random_name(prefix="rally_stack_")
        kw = {
            "stack_name": stack_name,
            "disable_rollback": True,
            "parameters": parameters or {},
            "template": template,
            "files": files or {},
            "environment": environment or {}
        }

        # heat client returns body instead manager object, so we should
        # get manager object using stack_id
        stack_id = self.clients("heat").stacks.create(**kw)["stack"]["id"]
        stack = self.clients("heat").stacks.get(stack_id)

        time.sleep(CONF.benchmark.heat_stack_create_prepoll_delay)

        stack = bench_utils.wait_for(
            stack,
            is_ready=bench_utils.resource_is("CREATE_COMPLETE"),
            update_resource=bench_utils.get_from_manager(["CREATE_FAILED"]),
            timeout=CONF.benchmark.heat_stack_create_timeout,
            check_interval=CONF.benchmark.heat_stack_create_poll_interval)

        return stack

    @base.atomic_action_timer("heat.update_stack")
    def _update_stack(self, stack, template, parameters=None,
                      files=None, environment=None):
        """Update an existing stack

        :param stack: stack that need to be updated
        :param template: Updated template
        :param parameters: template parameters for stack update
        :param files: additional files used in template
        :param environment: stack environment definition

        :returns: object of updated stack
        """

        kw = {
            "stack_name": stack.stack_name,
            "disable_rollback": True,
            "parameters": parameters or {},
            "template": template,
            "files": files or {},
            "environment": environment or {}
        }
        self.clients("heat").stacks.update(stack.id, **kw)

        time.sleep(CONF.benchmark.heat_stack_update_prepoll_delay)
        stack = bench_utils.wait_for(
            stack,
            is_ready=bench_utils.resource_is("UPDATE_COMPLETE"),
            update_resource=bench_utils.get_from_manager(["UPDATE_FAILED"]),
            timeout=CONF.benchmark.heat_stack_update_timeout,
            check_interval=CONF.benchmark.heat_stack_update_poll_interval)
        return stack

    @base.atomic_action_timer("heat.check_stack")
    def _check_stack(self, stack):
        """Check given stack.

        Check the stack and stack resources.

        :param stack: stack that needs to be checked
        """
        self.clients("heat").actions.check(stack.id)
        bench_utils.wait_for(
            stack,
            is_ready=bench_utils.resource_is("CHECK_COMPLETE"),
            update_resource=bench_utils.get_from_manager(["CHECK_FAILED"]),
            timeout=CONF.benchmark.heat_stack_check_timeout,
            check_interval=CONF.benchmark.heat_stack_check_poll_interval)

    @base.atomic_action_timer("heat.delete_stack")
    def _delete_stack(self, stack):
        """Delete given stack.

        Returns when the stack is actually deleted.

        :param stack: stack object
        """
        stack.delete()
        bench_utils.wait_for_delete(
            stack,
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.heat_stack_delete_timeout,
            check_interval=CONF.benchmark.heat_stack_delete_poll_interval)

    @base.atomic_action_timer("heat.suspend_stack")
    def _suspend_stack(self, stack):
        """Suspend given stack.

        :param stack: stack that needs to be suspended
        """

        self.clients("heat").actions.suspend(stack.id)
        bench_utils.wait_for(
            stack,
            is_ready=bench_utils.resource_is("SUSPEND_COMPLETE"),
            update_resource=bench_utils.get_from_manager(
                ["SUSPEND_FAILED"]),
            timeout=CONF.benchmark.heat_stack_suspend_timeout,
            check_interval=CONF.benchmark.heat_stack_suspend_poll_interval)

    @base.atomic_action_timer("heat.resume_stack")
    def _resume_stack(self, stack):
        """Resume given stack.

        :param stack: stack that needs to be resumed
        """

        self.clients("heat").actions.resume(stack.id)
        bench_utils.wait_for(
            stack,
            is_ready=bench_utils.resource_is("RESUME_COMPLETE"),
            update_resource=bench_utils.get_from_manager(
                ["RESUME_FAILED"]),
            timeout=CONF.benchmark.heat_stack_resume_timeout,
            check_interval=CONF.benchmark.heat_stack_resume_poll_interval)
