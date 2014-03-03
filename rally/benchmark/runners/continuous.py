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


import collections
import multiprocessing
import random
import time

from rally.benchmark.runners import base
from rally.benchmark import utils

from rally.openstack.common import log as logging

LOG = logging.getLogger(__name__)


class ContinuousScenarioRunner(base.ScenarioRunner):
    """Scenario runner that launches benchmark scenarios continuously.

    "Continuously" means here that each iteration of the scenario being
    executed starts just after the previous one has finished, without any
    pauses. The scenario will be run either for a given number of times (if
    the "times" field is specified in the input config) or until it reaches
    the given time limit (if specified in seconds in the "duration" field of
    the config). This scenario can also be configured via the "active_users"
    parameter to run several scenario iterations in parallel (thus simulating
    the activities of multiple users).
    """

    __execution_type__ = "continuous"

    def _run_scenario_continuously_for_times(self, cls, method, context, args,
                                             times, concurrent, timeout):
        test_args = [(i, cls, method, context["admin"],
                      random.choice(context["users"]), args)
                     for i in range(times)]

        pool = multiprocessing.Pool(concurrent)
        iter_result = pool.imap(base._run_scenario_once, test_args)

        results = []

        for i in range(len(test_args)):
            try:
                result = iter_result.next(timeout)
            except multiprocessing.TimeoutError as e:
                result = {"time": timeout, "idle_time": 0,
                          "error": utils.format_exc(e)}
            results.append(result)

        pool.close()
        pool.join()

        return results

    def _run_scenario_continuously_for_duration(self, cls, method, context,
                                                args, duration, concurrent,
                                                timeout):
        pool = multiprocessing.Pool(concurrent)
        run_args = utils.infinite_run_args((cls, method, context["admin"],
                                            random.choice(context["users"]),
                                            args))
        iter_result = pool.imap(base._run_scenario_once, run_args)

        start = time.time()

        results_queue = collections.deque([], maxlen=concurrent)

        while True:
            try:
                result = iter_result.next(timeout)
            except multiprocessing.TimeoutError as e:
                result = {"time": timeout, "idle_time": 0,
                          "error": utils.format_exc(e)}
            results_queue.append(result)

            if time.time() - start > duration * 60:
                break

        results = list(results_queue)

        pool.terminate()
        pool.join()

        return results

    def _run_scenario(self, cls, method_name, context, args, config):

        timeout = config.get("timeout", 600)
        concurrent = config.get("active_users", 1)

        # NOTE(msdubov): If not specified, perform single scenario run.
        if "duration" not in config and "times" not in config:
            config["times"] = 1

        # Continiously run a benchmark scenario the specified
        # amount of times.
        if "times" in config:
            times = config["times"]
            return self._run_scenario_continuously_for_times(
                cls, method_name, context, args, times, concurrent, timeout)
        # Continiously run a scenario as many times as needed
        # to fill up the given period of time.
        elif "duration" in config:
            duration = config["duration"]
            return self._run_scenario_continuously_for_duration(
                cls, method_name, context, args, duration, concurrent, timeout)
