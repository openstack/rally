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
import queue as Queue
import threading
import time

from rally.common import utils
from rally.common import validation
from rally import consts
from rally.task import runner


def _worker_process(queue, iteration_gen, timeout, concurrency, times,
                    duration, context, cls, method_name, args, event_queue,
                    aborted, info):
    """Start the scenario within threads.

    Spawn threads to support scenario execution.
    Scenario is ran for a fixed number of times if times is specified
    Scenario is ran for fixed duration if duration is specified.
    This generates a constant load on the cloud under test by executing each
    scenario iteration without pausing between iterations. Each thread runs
    the scenario method once with passed scenario arguments and context.
    After execution the result is appended to the queue.

    :param queue: queue object to append results
    :param iteration_gen: next iteration number generator
    :param timeout: operation's timeout
    :param concurrency: number of concurrently running scenario iterations
    :param times: total number of scenario iterations to be run
    :param duration: total duration in seconds of the run
    :param context: scenario context object
    :param cls: scenario class
    :param method_name: scenario method name
    :param args: scenario args
    :param event_queue: queue object to append events
    :param aborted: multiprocessing.Event that aborts load generation if
                    the flag is set
    :param info: info about all processes count and counter of launched process
    """
    def _to_be_continued(iteration, current_duration, aborted, times=None,
                         duration=None):
        if times is not None:
            return iteration < times and not aborted.is_set()
        elif duration is not None:
            return current_duration < duration and not aborted.is_set()
        else:
            return False

    if times is None and duration is None:
        raise ValueError("times or duration must be specified")

    pool = collections.deque()
    alive_threads_in_pool = 0
    finished_threads_in_pool = 0

    runner._log_worker_info(times=times, duration=duration,
                            concurrency=concurrency, timeout=timeout, cls=cls,
                            method_name=method_name, args=args)

    if timeout:
        timeout_queue = Queue.Queue()
        collector_thr_by_timeout = threading.Thread(
            target=utils.timeout_thread,
            args=(timeout_queue, )
        )
        collector_thr_by_timeout.start()

    iteration = next(iteration_gen)
    start_time = time.time()
    # NOTE(msimonin): keep the previous behaviour
    # > when duration is 0, scenario executes exactly 1 time
    current_duration = -1
    while _to_be_continued(iteration, current_duration, aborted,
                           times=times, duration=duration):

        scenario_context = runner._get_scenario_context(iteration, context)
        worker_args = (
            queue, cls, method_name, scenario_context, args, event_queue)

        thread = threading.Thread(target=runner._worker_thread,
                                  args=worker_args)

        thread.start()
        if timeout:
            timeout_queue.put((thread, time.time() + timeout))
        pool.append(thread)
        alive_threads_in_pool += 1

        while alive_threads_in_pool == concurrency:
            prev_finished_threads_in_pool = finished_threads_in_pool
            finished_threads_in_pool = 0
            for t in pool:
                if not t.is_alive():
                    finished_threads_in_pool += 1

            alive_threads_in_pool -= finished_threads_in_pool
            alive_threads_in_pool += prev_finished_threads_in_pool

            if alive_threads_in_pool < concurrency:
                # NOTE(boris-42): cleanup pool array. This is required because
                # in other case array length will be equal to times which
                # is unlimited big
                while pool and not pool[0].is_alive():
                    pool.popleft().join()
                    finished_threads_in_pool -= 1
                break

            # we should wait to not create big noise with these checks
            time.sleep(0.001)
        iteration = next(iteration_gen)
        current_duration = time.time() - start_time

    # Wait until all threads are done
    while pool:
        pool.popleft().join()

    if timeout:
        timeout_queue.put((None, None,))
        collector_thr_by_timeout.join()


@validation.configure("check_constant")
class CheckConstantValidator(validation.Validator):
    """Additional schema validation for constant runner"""

    def validate(self, context, config, plugin_cls, plugin_cfg):
        if plugin_cfg.get("concurrency", 1) > plugin_cfg.get("times", 1):
            return self.fail(
                "Parameter 'concurrency' means a number of parallel "
                "executions of iterations. Parameter 'times' means total "
                "number of iteration executions. It is redundant "
                "(and restricted) to have number of parallel iterations "
                "bigger then total number of iterations.")


@validation.add("check_constant")
@runner.configure(name="constant")
class ConstantScenarioRunner(runner.ScenarioRunner):
    """Creates constant load executing a scenario a specified number of times.

    This runner will place a constant load on the cloud under test by
    executing each scenario iteration without pausing between iterations
    up to the number of times specified in the scenario config.

    The concurrency parameter of the scenario config controls the
    number of concurrent iterations which execute during a single
    scenario in order to simulate the activities of multiple users
    placing load on the cloud under test.
    """

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "concurrency": {
                "type": "integer",
                "minimum": 1,
                "description": "The number of parallel iteration executions."
            },
            "times": {
                "type": "integer",
                "minimum": 1,
                "description": "Total number of iteration executions."
            },
            "timeout": {
                "type": "number",
                "description": "Operation's timeout."
            },
            "max_cpu_count": {
                "type": "integer",
                "minimum": 1,
                "description": "The maximum number of processes to create load"
                               " from."
            }
        },
        "additionalProperties": False
    }

    def _run_scenario(self, cls, method_name, context, args):
        """Runs the specified scenario with given arguments.

        This method generates a constant load on the cloud under test by
        executing each scenario iteration using a pool of processes without
        pausing between iterations up to the number of times specified
        in the scenario config.

        :param cls: The Scenario class where the scenario is implemented
        :param method_name: Name of the method that implements the scenario
        :param context: context that contains users, admin & other
                        information, that was created before scenario
                        execution starts.
        :param args: Arguments to call the scenario method with

        :returns: List of results fore each single scenario iteration,
                  where each result is a dictionary
        """
        timeout = self.config.get("timeout", 0)  # 0 means no timeout
        times = self.config.get("times", 1)
        concurrency = self.config.get("concurrency", 1)
        iteration_gen = utils.RAMInt()

        cpu_count = multiprocessing.cpu_count()
        max_cpu_used = min(cpu_count,
                           self.config.get("max_cpu_count", cpu_count))

        processes_to_start = min(max_cpu_used, times, concurrency)
        concurrency_per_worker, concurrency_overhead = divmod(
            concurrency, processes_to_start)

        self._log_debug_info(times=times, concurrency=concurrency,
                             timeout=timeout, max_cpu_used=max_cpu_used,
                             processes_to_start=processes_to_start,
                             concurrency_per_worker=concurrency_per_worker,
                             concurrency_overhead=concurrency_overhead)

        result_queue = multiprocessing.Queue()
        event_queue = multiprocessing.Queue()

        def worker_args_gen(concurrency_overhead):
            while True:
                yield (result_queue, iteration_gen, timeout,
                       concurrency_per_worker + (concurrency_overhead and 1),
                       times, None, context, cls, method_name, args,
                       event_queue, self.aborted)
                if concurrency_overhead:
                    concurrency_overhead -= 1

        process_pool = self._create_process_pool(
            processes_to_start, _worker_process,
            worker_args_gen(concurrency_overhead))
        self._join_processes(process_pool, result_queue, event_queue)


@runner.configure(name="constant_for_duration")
class ConstantForDurationScenarioRunner(runner.ScenarioRunner):
    """Creates constant load executing a scenario for an interval of time.

    This runner will place a constant load on the cloud under test by
    executing each scenario iteration without pausing between iterations
    until a specified interval of time has elapsed.

    The concurrency parameter of the scenario config controls the
    number of concurrent iterations which execute during a single
    sceanario in order to simulate the activities of multiple users
    placing load on the cloud under test.
    """

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "concurrency": {
                "type": "integer",
                "minimum": 1,
                "description": "The number of parallel iteration executions."
            },
            "duration": {
                "type": "number",
                "minimum": 0.0,
                "description": "The number of seconds during which to generate"
                               " a load. If the duration is 0, the scenario"
                               " will run once per parallel execution."
            },
            "timeout": {
                "type": "number",
                "minimum": 1,
                "description": "Operation's timeout."
            }
        },
        "required": ["duration"],
        "additionalProperties": False
    }

    def _run_scenario(self, cls, method_name, context, args):
        """Runs the specified scenario with given arguments.

        This method generates a constant load on the cloud under test by
        executing each scenario iteration using a pool of processes without
        pausing between iterations up to the number of times specified
        in the scenario config.

        :param cls: The Scenario class where the scenario is implemented
        :param method_name: Name of the method that implements the scenario
        :param context: context that contains users, admin & other
                        information, that was created before scenario
                        execution starts.
        :param args: Arguments to call the scenario method with

        :returns: List of results fore each single scenario iteration,
                  where each result is a dictionary
        """
        timeout = self.config.get("timeout", 600)
        duration = self.config.get("duration", 0)
        concurrency = self.config.get("concurrency", 1)
        iteration_gen = utils.RAMInt()

        cpu_count = multiprocessing.cpu_count()
        max_cpu_used = min(cpu_count,
                           self.config.get("max_cpu_count", cpu_count))

        processes_to_start = min(max_cpu_used, concurrency)
        concurrency_per_worker, concurrency_overhead = divmod(
            concurrency, processes_to_start)

        self._log_debug_info(duration=duration, concurrency=concurrency,
                             timeout=timeout, max_cpu_used=max_cpu_used,
                             processes_to_start=processes_to_start,
                             concurrency_per_worker=concurrency_per_worker,
                             concurrency_overhead=concurrency_overhead)

        result_queue = multiprocessing.Queue()
        event_queue = multiprocessing.Queue()

        def worker_args_gen(concurrency_overhead):
            while True:
                yield (result_queue, iteration_gen, timeout,
                       concurrency_per_worker + (concurrency_overhead and 1),
                       None, duration, context, cls, method_name, args,
                       event_queue, self.aborted)
                if concurrency_overhead:
                    concurrency_overhead -= 1

        process_pool = self._create_process_pool(
            processes_to_start, _worker_process,
            worker_args_gen(concurrency_overhead))
        self._join_processes(process_pool, result_queue, event_queue)
