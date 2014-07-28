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
from rally import utils as rutils


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
        rps = self.config["rps"]
        timeout = self.config.get("timeout", 600)
        cpu_count = multiprocessing.cpu_count()

        queue = multiprocessing.Queue()
        addition_args = args

        class WorkerProcess(multiprocessing.Process):

            def __init__(self, rps, times, queue, scenario_context, timeout,
                         process_id, args):
                self.rps = rps
                self.times = times
                self.timeout = timeout
                self.pool = []
                self.scenario_context = scenario_context
                self.id = process_id
                self.args = args
                self.queue = queue
                super(WorkerProcess, self).__init__()

            def _th_worker(self, args):
                result = base._run_scenario_once(args)
                self.queue.put(result)

            def run(self):
                for i in range(self.times):
                    scenario_args = (("%d:%d" % (self.id, i), cls, method_name,
                                     self.scenario_context, self.args),)
                    thread = threading.Thread(target=self._th_worker,
                                              args=scenario_args)
                    thread.start()
                    self.pool.append(thread)
                    time.sleep(1.0 / rps)

                while len(self.pool):
                    thr = self.pool.pop()
                    thr.join(self.timeout)

        process_pool = []
        scenario_context = base._get_scenario_context(context)

        if times <= cpu_count:
            processes2start = times
        else:
            processes2start = cpu_count

        for i in range(processes2start):
            process = WorkerProcess(rps / float(processes2start),
                                    times / processes2start,
                                    queue, scenario_context, timeout,
                                    i, addition_args)
            process.start()
            process_pool.append(process)

        while len(process_pool):
            for process in process_pool:
                if not process.is_alive():
                    process.join(timeout)
                    process_pool.remove(process)
            if not queue.empty():
                self._send_result(queue.get(timeout=timeout))
            time.sleep(1.0 / rps)

        while not queue.empty():
            result = queue.get(timeout=timeout)
            self._send_result(result)

        queue.close()
