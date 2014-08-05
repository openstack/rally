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

from oslo.config import cfg

from rally.benchmark.scenarios import base as scenario_base
from rally.benchmark import utils as bench_utils


heat_benchmark_opts = [
    cfg.FloatOpt('heat_stack_create_prepoll_delay',
                 default=2.0,
                 help='Time to sleep after creating a resource before '
                      'polling for it status'),
    cfg.FloatOpt('heat_stack_create_timeout',
                 default=3600.0,
                 help='Time to wait for heat stack to be created.'),
    cfg.FloatOpt('heat_stack_create_poll_interval',
                 default=1.0,
                 help='Interval between checks when waiting for stack '
                      'creation.'),
    cfg.FloatOpt('heat_stack_delete_timeout',
                 default=3600.0,
                 help='Time to wait for heat stack to be deleted.'),
    cfg.FloatOpt('heat_stack_delete_poll_interval',
                 default=1.0,
                 help='Interval between checks when waiting for stack '
                      'deletion.')
]


CONF = cfg.CONF
benchmark_group = cfg.OptGroup(name='benchmark', title='benchmark options')
CONF.register_opts(heat_benchmark_opts, group=benchmark_group)


def heat_resource_is(status):
    """Check status of stack."""

    return lambda resource: resource.stack_status.upper() == status.upper()


class HeatScenario(scenario_base.Scenario):

    default_template = "HeatTemplateFormatVersion: '2012-12-12'"

    @scenario_base.atomic_action_timer('heat.list_stacks')
    def _list_stacks(self):
        """Return user stack list."""

        return list(self.clients("heat").stacks.list())

    @scenario_base.atomic_action_timer('heat.create_stack')
    def _create_stack(self, stack_name, template=None):
        """Create a new stack.

        :param stack_name: string. Name for created stack.
        :param template: optional parameter. Template with stack description.

        returns: object of stack
        """
        template = template or self.default_template

        kw = {
            "stack_name": stack_name,
            "disable_rollback": True,
            "parameters": {},
            "template": template,
            "files": {},
            "environment": {}
        }

        # heat client returns body instead manager object, so we should
        # get manager object using stack_id
        stack_id = self.clients("heat").stacks.create(**kw)["stack"]["id"]
        stack = self.clients("heat").stacks.get(stack_id)

        time.sleep(CONF.benchmark.heat_stack_create_prepoll_delay)

        stack = bench_utils.wait_for(
            stack,
            is_ready=heat_resource_is("CREATE_COMPLETE"),
            update_resource=bench_utils.get_from_manager("CREATE_FAILED"),
            timeout=CONF.benchmark.heat_stack_create_timeout,
            check_interval=CONF.benchmark.heat_stack_create_poll_interval)

        return stack

    @scenario_base.atomic_action_timer('heat.delete_stack')
    def _delete_stack(self, stack):
        """Delete the given stack.

        Returns when the stack is actually deleted.

        :param stack: stack object
        """
        stack.delete()
        bench_utils.wait_for_delete(
            stack,
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.heat_stack_delete_timeout,
            check_interval=CONF.benchmark.heat_stack_delete_poll_interval)
