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
import copy
import multiprocessing
import time

import six

from rally.common import logging
from rally.common.plugin import plugin
from rally.common import utils as rutils
from rally.common import validation
from rally.task import scenario
from rally.task import types
from rally.task import utils


LOG = logging.getLogger(__name__)
configure = plugin.configure


def format_result_on_timeout(exc, timeout):
    return {
        "duration": timeout,
        "idle_duration": 0,
        "output": {"additive": [], "complete": []},
        "atomic_actions": [],
        "error": utils.format_exc(exc)
    }


def _get_scenario_context(iteration, context_obj):
    context_obj = copy.deepcopy(context_obj)
    context_obj["iteration"] = iteration + 1  # Numeration starts from `1'
    return context_obj


def _run_scenario_once(cls, method_name, context_obj, scenario_kwargs,
                       event_queue):
    iteration = context_obj["iteration"]
    event_queue.put({
        "type": "iteration",
        "value": iteration,
    })

    # provide arguments isolation between iterations
    scenario_kwargs = copy.deepcopy(scenario_kwargs)

    LOG.info("Task %(task)s | ITER: %(iteration)s START" %
             {"task": context_obj["task"]["uuid"], "iteration": iteration})

    scenario_inst = cls(context_obj)
    error = []
    try:
        with rutils.Timer() as timer:
            getattr(scenario_inst, method_name)(**scenario_kwargs)
    except Exception as e:
        error = utils.format_exc(e)
        if logging.is_debug():
            LOG.exception("Iteration %s raised Exception" % iteration)
    finally:
        status = "Error %s: %s" % tuple(error[0:2]) if error else "OK"
        LOG.info("Task %(task)s | ITER: %(iteration)s END: %(status)s" %
                 {"task": context_obj["task"]["uuid"], "iteration": iteration,
                  "status": status})

        return {"duration": timer.duration() - scenario_inst.idle_duration(),
                "timestamp": timer.timestamp(),
                "idle_duration": scenario_inst.idle_duration(),
                "error": error,
                "output": scenario_inst._output,
                "atomic_actions": scenario_inst.atomic_actions()}


def _worker_thread(queue, cls, method_name, context_obj, scenario_kwargs,
                   event_queue):
    queue.put(_run_scenario_once(cls, method_name, context_obj,
                                 scenario_kwargs, event_queue))


def _log_worker_info(**info):
    """Log worker parameters for debugging.

    :param info: key-value pairs to be logged
    """
    info_message = "\n\t".join(["%s: %s" % (k, v)
                                for k, v in info.items()])
    LOG.debug("Starting a worker.\n\t%s" % info_message)


@validation.add_default("jsonschema")
@plugin.base()
@six.add_metaclass(abc.ABCMeta)
class ScenarioRunner(plugin.Plugin, validation.ValidatablePluginMixin):
    """Base class for all scenario runners.

    Scenario runner is an entity that implements a certain strategy of
    launching scenarios plugins, e.g. running them continuously or
    periodically for a given number of times or seconds.
    These strategies should be implemented in subclasses of ScenarioRunner
    in the_run_scenario() method.
    """

    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "type": {"type": "string"},
        },
        "required": ["type"],
        "additionalProperties": True
    }

    def __init__(self, task, config, batch_size=0):
        """Runner constructor.

        It sets task and config to local variables. Also initialize
        result_queue, where results will be put by _send_result method.

        :param task: Instance of objects.Task
        :param config: Dict with runner section of input task
        """
        self.task = task
        self.config = config
        self.result_queue = collections.deque()
        self.event_queue = collections.deque()
        self.aborted = multiprocessing.Event()
        self.run_duration = 0
        self.batch_size = batch_size
        self.result_batch = []

    @abc.abstractmethod
    def _run_scenario(self, cls, method_name, context, args):
        """Runs the specified scenario with given arguments.

        :param cls: The Scenario class where the scenario is implemented
        :param method_name: Name of the method that implements the scenario
        :param context: dict object that contains data created
                        by contexts plugins
        :param args: Arguments to call the scenario plugin with

        :returns: List of results fore each single scenario iteration,
                  where each result is a dictionary
        """

    def run(self, name, context, args):
        scenario_plugin = scenario.Scenario.get(name)

        # NOTE(boris-42): processing @types decorators
        args = types.preprocess(name, context, args)

        with rutils.Timer() as timer:
            # TODO(boris-42): remove method_name argument, now it's always run
            self._run_scenario(scenario_plugin, "run", context, args)

        self.run_duration = timer.duration()

    def abort(self):
        """Abort the execution of further scenario iterations."""
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

    def _join_processes(self, process_pool, result_queue, event_queue):
        """Join the processes in the pool and send their results to the queue.

        :param process_pool: pool of processes to join
        :param result_queue: multiprocessing.Queue that receives the results
        :param event_queue: multiprocessing.Queue that receives the events
        """
        while process_pool:
            while process_pool and not process_pool[0].is_alive():
                process_pool.popleft().join()

            if result_queue.empty() and event_queue.empty():
                # sleep a bit to avoid 100% usage of CPU by this method
                time.sleep(0.01)

            while not event_queue.empty():
                self.send_event(**event_queue.get())

            while not result_queue.empty():
                self._send_result(result_queue.get())

        self._flush_results()
        result_queue.close()
        event_queue.close()

    def _flush_results(self):
        if self.result_batch:
            sorted_batch = sorted(self.result_batch)
            self.result_queue.append(sorted_batch)
            del self.result_batch[:]

    def _send_result(self, result):
        """Store partial result to send it to consumer later.

        :param result: Result dict to be sent. It should match the
                       ScenarioRunnerResult schema, otherwise
                       ValidationError is raised.
        """

        if not self.task.result_has_valid_schema(result):
            LOG.warning(
                "Task %(task)s | Runner `%(runner)s` is trying to send "
                "results in wrong format"
                % {"task": self.task["uuid"], "runner": self.get_name()})
            return

        self.result_batch.append(result)

        if len(self.result_batch) >= self.batch_size:
            sorted_batch = sorted(self.result_batch,
                                  key=lambda r: result["timestamp"])
            self.result_queue.append(sorted_batch)
            del self.result_batch[:]

    def send_event(self, type, value=None):
        """Store event to send it to consumer later.

        :param type: Event type
        :param value: Optional event data
        """
        self.event_queue.append({"type": type,
                                 "value": value})

    def _log_debug_info(self, **info):
        """Log runner parameters for debugging.

        The method logs the runner name, the task id as well as the values
        passed as arguments.

        :param info: key-value pairs to be logged
        """
        info_message = "\n\t".join(["%s: %s" % (k, v)
                                    for k, v in info.items()])
        LOG.debug("Starting the %(name)s runner (task UUID: %(task)s)."
                  "\n\t%(info)s"
                  % {"name": self._meta_get("name"),
                     "task": self.task["uuid"],
                     "info": info_message})
