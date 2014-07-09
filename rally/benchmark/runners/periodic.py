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

import multiprocessing
import time

from rally.benchmark.runners import base
from rally import consts
from rally import utils as rutils


class PeriodicScenarioRunner(base.ScenarioRunner):
    """Scenario runner that launches benchmark scenarios periodically.

    "Periodically" means that the scenario method is executed with intervals
    between two consecutive runs, specified in seconds in the input config
    (this period time doesn't depend on the scenario execution time).
    Each execution is a single benchmark scenario iteration (i.e. no parallel
    execution of multiple iterations is performed). The scenario will be
    launched for a fixed number of times in total (specified in the config).

    An example of a periodic scenario is booting 1 VM every 2 seconds. This
    execution type is thus very helpful in understanding the maximal load that
    a certain cloud can handle.
    """

    __execution_type__ = consts.RunnerType.PERIODIC

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": rutils.JSON_SCHEMA,
        "properties": {
            "type": {
                "type": "string"
            },
            "times": {
                "type": "integer",
                "minimum": 1
            },
            "period": {
                "type": "number",
                "minimum": 0.000001
            },
            "timeout": {
                "type": "number",
                "minimum": 1
            }
        },
        "additionalProperties": False
    }

    def _run_scenario(self, cls, method_name, context, args):

        times = self.config["times"]
        period = self.config["period"]
        timeout = self.config.get("timeout", 600)

        async_results = []

        pools = []
        for i in range(times):
            pool = multiprocessing.Pool(1)
            scenario_args = ((i, cls, method_name,
                              base._get_scenario_context(context), args),)
            async_result = pool.apply_async(base._run_scenario_once,
                                            scenario_args)
            async_results.append(async_result)

            pool.close()
            pools.append(pool)

            if i < times - 1:
                time.sleep(period)

        for async_result in async_results:
            try:
                result = async_result.get(timeout=timeout)
            except multiprocessing.TimeoutError as e:
                result = base.format_result_on_timeout(e, timeout)

            self._send_result(result)

        for pool in pools:
            pool.join()
