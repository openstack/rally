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
import threading
import time

from six.moves import queue as Queue

from rally.common import logging
from rally.common import utils
from rally import consts
from rally.task import runner

LOG = logging.getLogger(__name__)


def _worker_process(queue, iteration_gen, timeout, rps, times,
                    max_concurrent, context, cls, method_name,
                    args, event_queue, aborted, info):
    """Start scenario within threads.

    Spawn N threads per second. Each thread runs the scenario once, and appends
    result to queue. A maximum of max_concurrent threads will be ran
    concurrently.

    :param queue: queue object to append results
    :param iteration_gen: next iteration number generator
    :param timeout: operation's timeout
    :param rps: number of scenario iterations to be run per one second
    :param times: total number of scenario iterations to be run
    :param max_concurrent: maximum worker concurrency
    :param context: scenario context object
    :param cls: scenario class
    :param method_name: scenario method name
    :param args: scenario args
    :param aborted: multiprocessing.Event that aborts load generation if
                    the flag is set
    :param info: info about all processes count and counter of runned process
    """

    pool = collections.deque()
    sleep = 1.0 / rps

    runner._log_worker_info(times=times, rps=rps, timeout=timeout,
                            cls=cls, method_name=method_name, args=args)

    time.sleep(
        (sleep * info["processes_counter"]) / info["processes_to_start"])

    start = time.time()
    timeout_queue = Queue.Queue()

    if timeout:
        collector_thr_by_timeout = threading.Thread(
            target=utils.timeout_thread,
            args=(timeout_queue, )
        )
        collector_thr_by_timeout.start()

    i = 0
    while i < times and not aborted.is_set():
        scenario_context = runner._get_scenario_context(next(iteration_gen),
                                                        context)
        worker_args = (
            queue, cls, method_name, scenario_context, args, event_queue)
        thread = threading.Thread(target=runner._worker_thread,
                                  args=worker_args)

        i += 1
        thread.start()
        if timeout:
            timeout_queue.put((thread, time.time() + timeout))
        pool.append(thread)

        time_gap = time.time() - start
        real_rps = i / time_gap if time_gap else "Infinity"

        LOG.debug("Worker: %s rps: %s (requested rps: %s)" %
                  (i, real_rps, rps))

        # try to join latest thread(s) until it finished, or until time to
        # start new thread (if we have concurrent slots available)
        while i / (time.time() - start) > rps or len(pool) >= max_concurrent:
            if pool:
                pool[0].join(0.001)
                if not pool[0].isAlive():
                    pool.popleft()
            else:
                time.sleep(0.001)

    while pool:
        pool.popleft().join()

    if timeout:
        timeout_queue.put((None, None,))
        collector_thr_by_timeout.join()


@runner.configure(name="rps")
class RPSScenarioRunner(runner.ScenarioRunner):
    """Scenario runner that does the job with specified frequency.

    Every single benchmark scenario iteration is executed with specified
    frequency (runs per second) in a pool of processes. The scenario will be
    launched for a fixed number of times in total (specified in the config).

    An example of a rps scenario is booting 1 VM per second. This
    execution type is thus very helpful in understanding the maximal load that
    a certain cloud can handle.
    """

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
                "exclusiveMinimum": True,
                "minimum": 0
            },
            "timeout": {
                "type": "number",
            },
            "max_concurrency": {
                "type": "integer",
                "minimum": 1
            },
            "max_cpu_count": {
                "type": "integer",
                "minimum": 1
            }
        },
        "required": ["type", "times", "rps"],
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
        max_cpu_used = min(cpu_count,
                           self.config.get("max_cpu_count", cpu_count))

        processes_to_start = min(max_cpu_used, times,
                                 self.config.get("max_concurrency", times))
        rps_per_worker = float(self.config["rps"]) / processes_to_start
        times_per_worker, times_overhead = divmod(times, processes_to_start)

        # Determine concurrency per worker
        concurrency_per_worker, concurrency_overhead = divmod(
            self.config.get("max_concurrency", times), processes_to_start)

        self._log_debug_info(times=times, timeout=timeout,
                             max_cpu_used=max_cpu_used,
                             processes_to_start=processes_to_start,
                             rps_per_worker=rps_per_worker,
                             times_per_worker=times_per_worker,
                             times_overhead=times_overhead,
                             concurrency_per_worker=concurrency_per_worker,
                             concurrency_overhead=concurrency_overhead)

        result_queue = multiprocessing.Queue()
        event_queue = multiprocessing.Queue()

        def worker_args_gen(times_overhead, concurrency_overhead):
            """Generate arguments for process worker.

            Remainder of threads per process division is distributed to
            process workers equally - one thread per each process worker
            until the remainder equals zero. The same logic is applied
            to concurrency overhead.
            :param times_overhead: remaining number of threads to be
                                   distributed to workers
            :param concurrency_overhead: remaining number of maximum
                                         concurrent threads to be distributed
                                         to workers
            """
            while True:
                yield (result_queue, iteration_gen, timeout, rps_per_worker,
                       times_per_worker + (times_overhead and 1),
                       concurrency_per_worker + (concurrency_overhead and 1),
                       context, cls, method_name, args, event_queue,
                       self.aborted)
                if times_overhead:
                    times_overhead -= 1
                if concurrency_overhead:
                    concurrency_overhead -= 1

        process_pool = self._create_process_pool(
            processes_to_start, _worker_process,
            worker_args_gen(times_overhead, concurrency_overhead))
        self._join_processes(process_pool, result_queue, event_queue)
