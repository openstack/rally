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
import threading
import time

from rally.benchmark.runners import base
from rally.common import log as logging
from rally.common import utils
from rally import consts


LOG = logging.getLogger(__name__)


def _worker_process(queue, iteration_gen, timeout, rps, times,
                    context, cls, method_name, args, aborted):
    """Start scenario within threads.

    Spawn N threads per second. Each thread runs the scenario once, and appends
    the result to the queue.

    :param queue: queue object to append results
    :param iteration_gen: next iteration number generator
    :param timeout: operation's timeout
    :param rps: number of scenario iterations to be run per one second
    :param times: total number of scenario iterations to be run
    :param context: scenario context object
    :param cls: scenario class
    :param method_name: scenario method name
    :param args: scenario args
    :param aborted: multiprocessing.Event that aborts load generation if
                    the flag is set
    """

    pool = collections.deque()
    start = time.time()
    sleep = 1.0 / rps

    base._log_worker_info(times=times, rps=rps, timeout=timeout,
                          cls=cls, method_name=method_name, args=args)

    # Injecting timeout to exclude situations, where start time and
    # actual time are neglible close

    randsleep_delay = random.randint(int(sleep / 2 * 100), int(sleep * 100))
    time.sleep(randsleep_delay / 100.0)

    i = 0
    while i < times and not aborted.is_set():
        scenario_context = base._get_scenario_context(context)
        scenario_args = (next(iteration_gen), cls, method_name,
                         scenario_context, args)
        worker_args = (queue, scenario_args)
        thread = threading.Thread(target=base._worker_thread,
                                  args=worker_args)
        i += 1
        thread.start()
        pool.append(thread)

        time_gap = time.time() - start
        real_rps = i / time_gap if time_gap else "Infinity"

        LOG.debug("Worker: %s rps: %s (requested rps: %s)" %
                  (i, real_rps, rps))

        # try to join latest thread(s) until it finished, or until time to
        # start new thread
        while i / (time.time() - start) > rps:
            if pool:
                pool[0].join(sleep)
                if not pool[0].isAlive():
                    pool.popleft()
            else:
                time.sleep(sleep)

    while pool:
        thr = pool.popleft()
        thr.join()


class RPSScenarioRunner(base.ScenarioRunner):
    """Scenario runner that does the job with specified frequency.

    Every single benchmark scenario iteration is executed with specified
    frequency (runs per second) in a pool of processes. The scenario will be
    launched for a fixed number of times in total (specified in the config).

    An example of a rps scenario is booting 1 VM onse per second. This
    execution type is thus very helpful in understanding the maximal load that
    a certain cloud can handle.
    """

    __execution_type__ = consts.RunnerType.RPS

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
            },
            "rps": {
                "type": "number",
                "minimum": 1
            },
            "timeout": {
                "type": "number",
            },
        },
        "additionalProperties": False
    }

    def _run_scenario(self, cls, method_name, context, args):
        """Runs the specified benchmark scenario with given arguments.

        Every single benchmark scenario iteration is executed with specified
        frequency (runs per second) in a pool of processes. The scenario will
        be launched for a fixed number of times in total (specified in the
        config).

        :param cls: The Scenario class where the scenario is implemented
        :param method_name: Name of the method that implements the scenario
        :param context: Benchmark context that contains users, admin & other
                        information, that was created before benchmark started.
        :param args: Arguments to call the scenario method with

        :returns: List of results fore each single scenario iteration,
                  where each result is a dictionary
        """
        times = self.config["times"]
        timeout = self.config.get("timeout", 0)  # 0 means no timeout
        iteration_gen = utils.RAMInt()
        cpu_count = multiprocessing.cpu_count()
        processes_to_start = min(cpu_count, times)
        rps_per_worker = float(self.config["rps"]) / processes_to_start
        times_per_worker, times_overhead = divmod(times, processes_to_start)

        self._log_debug_info(times=times, timeout=timeout, cpu_count=cpu_count,
                             processes_to_start=processes_to_start,
                             rps_per_worker=rps_per_worker,
                             times_per_worker=times_per_worker,
                             times_overhead=times_overhead)

        result_queue = multiprocessing.Queue()

        def worker_args_gen(times_overhead):
            while True:
                yield (result_queue, iteration_gen, timeout, rps_per_worker,
                       times_per_worker + (times_overhead and 1),
                       context, cls, method_name, args, self.aborted)
                if times_overhead:
                    times_overhead -= 1

        process_pool = self._create_process_pool(
            processes_to_start, _worker_process,
            worker_args_gen(times_overhead))
        self._join_processes(process_pool, result_queue)
