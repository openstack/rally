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

from rally.benchmark.runners import base
from rally import consts
from rally import utils


class SerialScenarioRunner(base.ScenarioRunner):
    """Scenario runner that executes benchmark scenarios in serial.

    Unlike scenario runners that execute in parallel, the SerialScenarioRunner
    executes scenarios one-by-one in the same python interpreter process as
    Rally.  This allows you to benchmark your scenario without introducing
    any concurrent operations as well as interactively debug the scenario
    from the same command that you use to start Rally.
    """

    __execution_type__ = consts.RunnerType.SERIAL

    # NOTE(mmorais): additionalProperties is set True to allow switching
    # between parallel and serial runners by modifying only *type* property
    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": utils.JSON_SCHEMA,
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
        times = self.config.get('times', 1)

        results = []

        for i in range(times):
            run_args = (i, cls, method_name,
                        base._get_scenario_context(context), args)
            result = base._run_scenario_once(run_args)
            results.append(result)

        return base.ScenarioRunnerResult(results)
