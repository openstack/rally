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
import threading
import time

from rally.benchmark.runners import base
from rally import consts
from rally.openstack.common import log as logging
from rally import utils as rutils


LOG = logging.getLogger(__name__)
SEND_RESULT_DELAY = 1


def _worker_thread(queue, args):
        queue.put(base._run_scenario_once(args))


def _worker_process(rps, times, queue, scenario_context, timeout,
                    worker_id, cls, method_name, args):
    """Start scenario within threads.

    Spawn N threads per second. Each thread runs scenario once, and appends
    result to queue.

    :param rps: runs per second
    :param times: number of threads to be run
    :param queue: queue object to append results
    :param scenario_context: scenario context object
    :param timeout: timeout operation
    :param worker_id: id of worker process
    :param cls: scenario class
    :param method_name: scenario method name
    :param args: scenario args
    """

    pool = []
    i = 0
    start = time.time()
    sleep = 1.0 / rps

    while times > i:
        i += 1
        scenario_args = (queue, ("%d:%d" % (worker_id, i), cls, method_name,
                         scenario_context, args),)
        thread = threading.Thread(target=_worker_thread,
                                  args=scenario_args)
        thread.start()
        pool.append(thread)

        LOG.debug("Worker: %s rps: %s (requested rps: %s)" % (
                  worker_id, i / (time.time() - start), rps))

        # try to join latest thread(s) until it finished, or until time to
        # start new thread
        while i / (time.time() - start) > rps:
            if pool:
                pool[0].join(sleep)
                if not pool[0].isAlive():
                    pool.pop(0)
            else:
                time.sleep(sleep)

    while pool:
        thr = pool.pop(0)
        thr.join()


class RPSScenarioRunner(base.ScenarioRunner):
    """Scenario runner that does the job with with specified frequency.

    Each execution is a single benchmark scenario iteration (i.e. no parallel
    execution of multiple iterations is performed). The scenario will be
    launched for a fixed number of times in total (specified in the config).

    An example of a rps scenario is booting 1 VM onse per second. This
    execution type is thus very helpful in understanding the maximal load that
    a certain cloud can handle.
    """

    __execution_type__ = consts.RunnerType.RPS

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
            "rps": {
                "type": "number",
            },
            "timeout": {
                "type": "number",
            },
        },
        "additionalProperties": False
    }

    def _run_scenario(self, cls, method_name, context, args):
        times = self.config["times"]
        timeout = self.config.get("timeout", 600)
        cpu_count = multiprocessing.cpu_count()
        processes2start = cpu_count if times >= cpu_count else times
        rps_per_worker = float(self.config["rps"]) / processes2start

        queue = multiprocessing.Queue()

        process_pool = []
        scenario_context = base._get_scenario_context(context)

        times_per_worker, rest = divmod(times, processes2start)

        for i in range(processes2start):
            times = times_per_worker + int(rest > 0)
            rest -= 1
            worker_args = (rps_per_worker, times, queue, scenario_context,
                           timeout, i, cls, method_name, args)
            process = multiprocessing.Process(target=_worker_process,
                                              args=worker_args)
            process.start()
            process_pool.append(process)

        while process_pool:
            for process in process_pool:
                process.join(SEND_RESULT_DELAY)
                if not process.is_alive():
                    process.join()
                    process_pool.remove(process)

            while not queue.empty():
                self._send_result(queue.get())

        queue.close()
