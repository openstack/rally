# Copyright 2013: Mirantis Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import random

from rally.common.plugin import plugin
from rally import consts
from rally.task import runner


@plugin.configure(name="random_times")
class RandomTimesScenarioRunner(runner.ScenarioRunner):
    """Sample of scenario runner plugin.

    Run scenario random number of times, which is chosen between min_times and
    max_times.
    """

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "type": {
                "type": "string"
            },
            "min_times": {
                "type": "integer",
                "minimum": 1
            },
            "max_times": {
                "type": "integer",
                "minimum": 1
            }
        },
        "additionalProperties": True
    }

    def _run_scenario(self, cls, method_name, context, args):
        # runners settings are stored in self.config
        min_times = self.config.get("min_times", 1)
        max_times = self.config.get("max_times", 1)

        for i in range(random.randrange(min_times, max_times)):
            run_args = (i, cls, method_name,
                        runner._get_scenario_context(context), args)
            result = runner._run_scenario_once(run_args)
            # use self.send_result for result of each iteration
            self._send_result(result)
