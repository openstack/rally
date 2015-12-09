# Copyright 2013: Mirantis Inc.
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

import abc
import collections
import multiprocessing
import time

import jsonschema

from rally.common import logging
from rally.common import objects
from rally.common.plugin import plugin
from rally.common import utils as rutils
from rally import consts
from rally.task import context
from rally.task import scenario
from rally.task import types
from rally.task import utils


LOG = logging.getLogger(__name__)


def format_result_on_timeout(exc, timeout):
    return {
        "duration": timeout,
        "idle_duration": 0,
        "output": {"additive": [], "complete": []},
        "atomic_actions": {},
        "error": utils.format_exc(exc)
    }


def _get_scenario_context(context_obj):
    return context.ContextManager(context_obj).map_for_scenario()


def _run_scenario_once(args):
    iteration, cls, method_name, context_obj, kwargs = args

    LOG.info("Task %(task)s | ITER: %(iteration)s START" %
             {"task": context_obj["task"]["uuid"], "iteration": iteration})

    context_obj["iteration"] = iteration
    scenario_inst = cls(context_obj)

    error = []
    output = {"additive": [], "complete": []}
    try:
        with rutils.Timer() as timer:
            # NOTE(amaretskiy): Output as return value is deprecated
            #     but supported for backward compatibility
            deprecated_output = getattr(scenario_inst, method_name)(**kwargs)
            warning = ""
            if deprecated_output:
                warning = ("Returning output data by scenario is deprecated "
                           "in favor of calling add_output().")
            if scenario_inst._output != {"complete": [], "additive": []}:
                output = scenario_inst._output
                if deprecated_output:
                    warning += (" Output data both returned and passed to "
                                "add_output() so returned one is ignored!")
            elif deprecated_output:
                output["additive"].append({
                    "title": "Scenario output",
                    "description": "",
                    "chart": "OutputStackedAreaChart",
                    "items": [list(item)
                              for item in deprecated_output["data"].items()]})
            if warning:
                LOG.warning(warning)
    except Exception as e:
        error = utils.format_exc(e)
        if logging.is_debug():
            LOG.exception(e)
    finally:
        status = "Error %s: %s" % tuple(error[0:2]) if error else "OK"
        LOG.info("Task %(task)s | ITER: %(iteration)s END: %(status)s" %
                 {"task": context_obj["task"]["uuid"], "iteration": iteration,
                  "status": status})

        return {"duration": timer.duration() - scenario_inst.idle_duration(),
                "timestamp": timer.timestamp(),
                "idle_duration": scenario_inst.idle_duration(),
                "error": error,
                "output": output,
                "atomic_actions": scenario_inst.atomic_actions()}


def _worker_thread(queue, args):
    queue.put(_run_scenario_once(args))


def _log_worker_info(**info):
    """Log worker parameters for debugging.

    :param info: key-value pairs to be logged
    """
    info_message = "\n\t".join(["%s: %s" % (k, v)
                                for k, v in info.items()])
    LOG.debug("Starting a worker.\n\t%s" % info_message)


class ScenarioRunnerResult(dict):
    """Class for all scenario runners' result."""

    RESULT_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "duration": {
                "type": "number"
            },
            "timestamp": {
                "type": "number"
            },
            "idle_duration": {
                "type": "number"
            },
            "output": objects.task.OUTPUT_SCHEMA,
            "atomic_actions": {
                "type": "object",
                "patternProperties": {
                    ".*": {"type": ["number", "null"]}
                }
            },
            "error": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            }
        },
        "additionalProperties": False
    }

    def __init__(self, result_list):
        super(ScenarioRunnerResult, self).__init__(result_list)
        jsonschema.validate(result_list, self.RESULT_SCHEMA)


def configure(name, namespace="default"):
    return plugin.configure(name=name, namespace=namespace)


@configure(name="base_runner")
class ScenarioRunner(plugin.Plugin):
    """Base class for all scenario runners.

    Scenario runner is an entity that implements a certain strategy of
    launching benchmark scenarios, e.g. running them continuously or
    periodically for a given number of times or seconds.
    These strategies should be implemented in subclasses of ScenarioRunner
    in the_run_scenario() method.
    """

    CONFIG_SCHEMA = {}

    def __init__(self, task, config, batch_size=0):
        """Runner constructor.

        It sets task and config to local variables. Also initialize
        result_queue, where results will be put by _send_result method.

        :param task: Instance of objects.Task
        :param config: Dict with runner section from benchmark configuration
        """
        self.task = task
        self.config = config
        self.result_queue = collections.deque()
        self.aborted = multiprocessing.Event()
        self.run_duration = 0
        self.batch_size = batch_size
        self.result_batch = []

    @staticmethod
    def validate(config):
        """Validates runner's part of task config."""
        runner = ScenarioRunner.get(config.get("type", "serial"))
        jsonschema.validate(config, runner.CONFIG_SCHEMA)

    @abc.abstractmethod
    def _run_scenario(self, cls, method_name, context, args):
        """Runs the specified benchmark scenario with given arguments.

        :param cls: The Scenario class where the scenario is implemented
        :param method_name: Name of the method that implements the scenario
        :param context: Benchmark context that contains users, admin & other
                        information, that was created before benchmark started.
        :param args: Arguments to call the scenario method with

        :returns: List of results fore each single scenario iteration,
                  where each result is a dictionary
        """

    def run(self, name, context, args):
        cls_name, method_name = name.split(".", 1)
        cls = scenario.Scenario.get(name)._meta_get("cls_ref")

        # NOTE(boris-42): processing @types decorators
        args = types.preprocess(name, context, args)

        with rutils.Timer() as timer:
            self._run_scenario(cls, method_name, context, args)

        self.run_duration = timer.duration()
        return self.run_duration

    def abort(self):
        """Abort the execution of further benchmark scenario iterations."""
        self.aborted.set()

    @staticmethod
    def _create_process_pool(processes_to_start, worker_process,
                             worker_args_gen):
        """Create a pool of processes with some defined target function.

        :param processes_to_start: number of processes to create in the pool
        :param worker_process: target function for all processes in the pool
        :param worker_args_gen: generator of arguments for the target function
        :returns: the process pool as a deque
        """
        process_pool = collections.deque()

        for i in range(processes_to_start):
            kwrgs = {"processes_to_start": processes_to_start,
                     "processes_counter": i}
            process = multiprocessing.Process(target=worker_process,
                                              args=next(worker_args_gen),
                                              kwargs={"info": kwrgs})
            process.start()
            process_pool.append(process)

        return process_pool

    def _join_processes(self, process_pool, result_queue):
        """Join the processes in the pool and send their results to the queue.

        :param process_pool: pool of processes to join
        :result_queue: multiprocessing.Queue that receives the results
        """
        while process_pool:
            while process_pool and not process_pool[0].is_alive():
                process_pool.popleft().join()

            if result_queue.empty():
                # sleep a bit to avoid 100% usage of CPU by this method
                time.sleep(0.001)

            while not result_queue.empty():
                self._send_result(result_queue.get())

        self._flush_results()
        result_queue.close()

    def _flush_results(self):
        if self.result_batch:
            sorted_batch = sorted(self.result_batch)
            self.result_queue.append(sorted_batch)
            self.result_batch = []

    def _send_result(self, result):
        """Store partial result to send it to consumer later.

        :param result: Result dict to be sent. It should match the
                       ScenarioRunnerResult schema, otherwise
                       ValidationError is raised.
        """

        r = ScenarioRunnerResult(result)
        self.result_batch.append(r)

        if len(self.result_batch) >= self.batch_size:
            sorted_batch = sorted(self.result_batch,
                                  key=lambda r: r["timestamp"])
            self.result_queue.append(sorted_batch)
            self.result_batch = []

    def _log_debug_info(self, **info):
        """Log runner parameters for debugging.

        The method logs the runner name, the task id as well as the values
        passed as arguments.

        :param info: key-value pairs to be logged
        """
        info_message = "\n\t".join(["%s: %s" % (k, v)
                                    for k, v in info.items()])
        LOG.debug("Starting the %(name)s runner (task UUID: %(task)s)."
                  "\n\t%(info)s" %
                  {"name": self._meta_get("name"),
                   "task": self.task["uuid"],
                   "info": info_message})
