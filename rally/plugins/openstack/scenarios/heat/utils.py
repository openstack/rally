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


from oslo_config import cfg
import requests

from rally.common import logging
from rally import exceptions
from rally.plugins.openstack import scenario
from rally.task import atomic
from rally.task import utils

LOG = logging.getLogger(__name__)

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
    cfg.FloatOpt("heat_stack_snapshot_timeout",
                 default=3600.0,
                 help="Time(in sec) to wait for stack snapshot to "
                      "be created."),
    cfg.FloatOpt("heat_stack_snapshot_poll_interval",
                 default=1.0,
                 help="Time interval(in sec) between checks when waiting for "
                      "stack snapshot to be created."),
    cfg.FloatOpt("heat_stack_restore_timeout",
                 default=3600.0,
                 help="Time(in sec) to wait for stack to be restored from "
                      "snapshot."),
    cfg.FloatOpt("heat_stack_restore_poll_interval",
                 default=1.0,
                 help="Time interval(in sec) between checks when waiting for "
                      "stack to be restored."),
    cfg.FloatOpt("heat_stack_scale_timeout",
                 default=3600.0,
                 help="Time (in sec) to wait for stack to scale up or down."),
    cfg.FloatOpt("heat_stack_scale_poll_interval",
                 default=1.0,
                 help="Time interval (in sec) between checks when waiting for "
                      "a stack to scale up or down."),
]

CONF = cfg.CONF
benchmark_group = cfg.OptGroup(name="benchmark", title="benchmark options")
CONF.register_opts(HEAT_BENCHMARK_OPTS, group=benchmark_group)


class HeatScenario(scenario.OpenStackScenario):
    """Base class for Heat scenarios with basic atomic actions."""

    @atomic.action_timer("heat.list_stacks")
    def _list_stacks(self):
        """Return user stack list."""

        return list(self.clients("heat").stacks.list())

    @atomic.action_timer("heat.create_stack")
    def _create_stack(self, template, parameters=None,
                      files=None, environment=None):
        """Create a new stack.

        :param template: template with stack description.
        :param parameters: template parameters used during stack creation
        :param files: additional files used in template
        :param environment: stack environment definition

        :returns: object of stack
        """
        stack_name = self.generate_random_name()
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

        self.sleep_between(CONF.benchmark.heat_stack_create_prepoll_delay)

        stack = utils.wait_for(
            stack,
            ready_statuses=["CREATE_COMPLETE"],
            failure_statuses=["CREATE_FAILED"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.heat_stack_create_timeout,
            check_interval=CONF.benchmark.heat_stack_create_poll_interval)

        return stack

    @atomic.action_timer("heat.update_stack")
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

        self.sleep_between(CONF.benchmark.heat_stack_update_prepoll_delay)

        stack = utils.wait_for(
            stack,
            ready_statuses=["UPDATE_COMPLETE"],
            failure_statuses=["UPDATE_FAILED"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.heat_stack_update_timeout,
            check_interval=CONF.benchmark.heat_stack_update_poll_interval)
        return stack

    @atomic.action_timer("heat.check_stack")
    def _check_stack(self, stack):
        """Check given stack.

        Check the stack and stack resources.

        :param stack: stack that needs to be checked
        """
        self.clients("heat").actions.check(stack.id)
        utils.wait_for(
            stack,
            ready_statuses=["CHECK_COMPLETE"],
            failure_statuses=["CHECK_FAILED"],
            update_resource=utils.get_from_manager(["CHECK_FAILED"]),
            timeout=CONF.benchmark.heat_stack_check_timeout,
            check_interval=CONF.benchmark.heat_stack_check_poll_interval)

    @atomic.action_timer("heat.delete_stack")
    def _delete_stack(self, stack):
        """Delete given stack.

        Returns when the stack is actually deleted.

        :param stack: stack object
        """
        stack.delete()
        utils.wait_for_status(
            stack,
            ready_statuses=["DELETE_COMPLETE"],
            failure_statuses=["DELETE_FAILED"],
            check_deletion=True,
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.heat_stack_delete_timeout,
            check_interval=CONF.benchmark.heat_stack_delete_poll_interval)

    @atomic.action_timer("heat.suspend_stack")
    def _suspend_stack(self, stack):
        """Suspend given stack.

        :param stack: stack that needs to be suspended
        """

        self.clients("heat").actions.suspend(stack.id)
        utils.wait_for(
            stack,
            ready_statuses=["SUSPEND_COMPLETE"],
            failure_statuses=["SUSPEND_FAILED"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.heat_stack_suspend_timeout,
            check_interval=CONF.benchmark.heat_stack_suspend_poll_interval)

    @atomic.action_timer("heat.resume_stack")
    def _resume_stack(self, stack):
        """Resume given stack.

        :param stack: stack that needs to be resumed
        """

        self.clients("heat").actions.resume(stack.id)
        utils.wait_for(
            stack,
            ready_statuses=["RESUME_COMPLETE"],
            failure_statuses=["RESUME_FAILED"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.heat_stack_resume_timeout,
            check_interval=CONF.benchmark.heat_stack_resume_poll_interval)

    @atomic.action_timer("heat.snapshot_stack")
    def _snapshot_stack(self, stack):
        """Creates a snapshot for given stack.

        :param stack: stack that will be used as base for snapshot
        :returns: snapshot created for given stack
        """
        snapshot = self.clients("heat").stacks.snapshot(
            stack.id)
        utils.wait_for(
            stack,
            ready_statuses=["SNAPSHOT_COMPLETE"],
            failure_statuses=["SNAPSHOT_FAILED"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.heat_stack_snapshot_timeout,
            check_interval=CONF.benchmark.heat_stack_snapshot_poll_interval)
        return snapshot

    @atomic.action_timer("heat.restore_stack")
    def _restore_stack(self, stack, snapshot_id):
        """Restores stack from given snapshot.

        :param stack: stack that will be restored from snapshot
        :param snapshot_id: id of given snapshot
        """
        self.clients("heat").stacks.restore(stack.id, snapshot_id)
        utils.wait_for(
            stack,
            ready_statuses=["RESTORE_COMPLETE"],
            failure_statuses=["RESTORE_FAILED"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.heat_stack_restore_timeout,
            check_interval=CONF.benchmark.heat_stack_restore_poll_interval
        )

    @atomic.action_timer("heat.show_output")
    def _stack_show_output(self, stack, output_key):
        """Execute output_show for specified "output_key".

        This method uses new output API call.
        :param stack: stack with output_key output.
        :param output_key: The name of the output.
        """
        output = self.clients("heat").stacks.output_show(stack.id, output_key)
        return output

    @atomic.action_timer("heat.show_output_via_API")
    def _stack_show_output_via_API(self, stack, output_key):
        """Execute output_show for specified "output_key".

        This method uses old way for getting output value.
        It gets whole stack object and then finds necessary "output_key".
        :param stack: stack with output_key output.
        :param output_key: The name of the output.
        """
        # this code copy-pasted and adopted for rally from old client version
        # https://github.com/openstack/python-heatclient/blob/0.8.0/heatclient/
        # v1/shell.py#L682-L699
        stack = self.clients("heat").stacks.get(stack_id=stack.id)
        for output in stack.to_dict().get("outputs", []):
            if output["output_key"] == output_key:
                return output

    @atomic.action_timer("heat.list_output")
    def _stack_list_output(self, stack):
        """Execute output_list for specified "stack".

        This method uses new output API call.
        :param stack: stack to call output-list.
        """
        output_list = self.clients("heat").stacks.output_list(stack.id)
        return output_list

    @atomic.action_timer("heat.list_output_via_API")
    def _stack_list_output_via_API(self, stack):
        """Execute output_list for specified "stack".

        This method uses old way for getting output value.
        It gets whole stack object and then prints all outputs
        belongs this stack.
        :param stack: stack to call output-list.
        """
        # this code copy-pasted and adopted for rally from old client version
        # https://github.com/openstack/python-heatclient/blob/0.8.0/heatclient/
        # v1/shell.py#L649-L663
        stack = self.clients("heat").stacks.get(stack_id=stack.id)
        output_list = stack.to_dict()["outputs"]
        return output_list

    def _count_instances(self, stack):
        """Count instances in a Heat stack.

        :param stack: stack to count instances in.
        """
        return len([
            r for r in self.clients("heat").resources.list(stack.id,
                                                           nested_depth=1)
            if r.resource_type == "OS::Nova::Server"])

    def _scale_stack(self, stack, output_key, delta):
        """Scale a stack up or down.

        Calls the webhook given in the output value identified by
        'output_key', and waits for the stack size to change by
        'delta'.

        :param stack: stack to scale up or down
        :param output_key: The name of the output to get the URL from
        :param delta: The expected change in number of instances in
                      the stack (signed int)
        """
        num_instances = self._count_instances(stack)
        expected_instances = num_instances + delta
        LOG.debug("Scaling stack %s from %s to %s instances with %s" %
                  (stack.id, num_instances, expected_instances, output_key))
        with atomic.ActionTimer(self, "heat.scale_with_%s" % output_key):
            self._stack_webhook(stack, output_key)
            utils.wait_for(
                stack,
                is_ready=lambda s: (
                    self._count_instances(s) == expected_instances),
                failure_statuses=["UPDATE_FAILED"],
                update_resource=utils.get_from_manager(),
                timeout=CONF.benchmark.heat_stack_scale_timeout,
                check_interval=CONF.benchmark.heat_stack_scale_poll_interval)

    def _stack_webhook(self, stack, output_key):
        """POST to the URL given in the output value identified by output_key.

        This can be used to scale stacks up and down, for instance.

        :param stack: stack to call a webhook on
        :param output_key: The name of the output to get the URL from
        :raises InvalidConfigException: if the output key is not found
        """
        url = None
        for output in stack.outputs:
            if output["output_key"] == output_key:
                url = output["output_value"]
                break
        else:
            raise exceptions.InvalidConfigException(
                "No output key %(key)s found in stack %(id)s" %
                {"key": output_key, "id": stack.id})

        with atomic.ActionTimer(self, "heat.%s_webhook" % output_key):
            requests.post(url).raise_for_status()
