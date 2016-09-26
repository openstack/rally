# Copyright (C) 2014 Yahoo! Inc. All Rights Reserved.
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

from rally.common import utils as rutils
from rally import consts
from rally.task import runner


@runner.configure(name="serial")
class SerialScenarioRunner(runner.ScenarioRunner):
    """Scenario runner that executes benchmark scenarios serially.

    Unlike scenario runners that execute in parallel, the serial scenario
    runner executes scenarios one-by-one in the same python interpreter process
    as Rally. This allows you to benchmark your scenario without introducing
    any concurrent operations as well as interactively debug the scenario
    from the same command that you use to start Rally.
    """

    # NOTE(mmorais): additionalProperties is set True to allow switching
    # between parallel and serial runners by modifying only *type* property
    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "type": {
                "type": "string"
            },
            "times": {
                "type": "integer",
                "minimum": 1
            }
        },
        "additionalProperties": True
    }

    def _run_scenario(self, cls, method_name, context, args):
        """Runs the specified benchmark scenario with given arguments.

        The scenario iterations are executed one-by-one in the same python
        interpreter process as Rally. This allows you to benchmark your
        scenario without introducing any concurrent operations as well as
        interactively debug the scenario from the same command that you use
        to start Rally.

        :param cls: The Scenario class where the scenario is implemented
        :param method_name: Name of the method that implements the scenario
        :param context: Benchmark context that contains users, admin & other
                        information, that was created before benchmark started.
        :param args: Arguments to call the scenario method with

        :returns: List of results fore each single scenario iteration,
                  where each result is a dictionary
        """
        times = self.config.get("times", 1)

        event_queue = rutils.DequeAsQueue(self.event_queue)

        for i in range(times):
            if self.aborted.is_set():
                break
            result = runner._run_scenario_once(
                cls, method_name, runner._get_scenario_context(i, context),
                args, event_queue)
            self._send_result(result)

        self._flush_results()
