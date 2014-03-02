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
from multiprocessing import pool as multiprocessing_pool
import random
import time

from rally.benchmark.runners import base
from rally.benchmark import utils


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

    __execution_type__ = "periodic"

    def _run_scenario(self, cls, method_name, args, config):

        times = config["times"]
        period = config["period"]
        timeout = config.get("timeout", 600)

        async_results = []

        for i in range(times):
            thread = multiprocessing_pool.ThreadPool(processes=1)
            scenario_args = ((i, cls, method_name, self.admin_user,
                             random.choice(self.users), args),)
            async_result = thread.apply_async(base._run_scenario_once,
                                              scenario_args)
            async_results.append(async_result)

            if i != times - 1:
                time.sleep(period * 60)

        results = []
        for async_result in async_results:
            try:
                result = async_result.get()
            except multiprocessing.TimeoutError as e:
                result = {"time": timeout, "idle_time": 0,
                          "error": utils.format_exc(e)}
            results.append(result)

        return results
