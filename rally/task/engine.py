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

import copy
import json
import threading
import time
import traceback

from rally.common import cfg
from rally.common import logging
from rally.common import objects
from rally import consts
from rally import exceptions
from rally.task import context
from rally.task import hook
from rally.task import runner
from rally.task import scenario
from rally.task import sla
from rally.utils import strutils


LOG = logging.getLogger(__name__)

CONF = cfg.CONF

TASK_ENGINE_OPTS = [
    cfg.IntOpt("raw_result_chunk_size", default=1000, min=1,
               help="Size of raw result chunk in iterations"),
]


class ResultConsumer(object):
    """ResultConsumer class stores results from ScenarioRunner, checks SLA.

    Also ResultConsumer listens for runner events and notifies HookExecutor
    about started iterations.
    """

    def __init__(self, workload_cfg, task, subtask, workload, runner,
                 abort_on_sla_failure, ctx_manager):
        """ResultConsumer constructor.

        :param workload_cfg: A configuration of the Workload
        :param task: Instance of Task, task to run
        :param subtask: Instance of Subtask
        :param workload: Instance of Workload
        :param runner: ScenarioRunner instance that produces results to be
                       consumed
        :param abort_on_sla_failure: True if the execution should be stopped
                                     when some SLA check fails
        :param ctx_manager: ContextManager instance
        """

        self.task = task
        self.subtask = subtask
        self.workload = workload
        self.workload_cfg = workload_cfg
        self.runner = runner
        self.load_started_at = float("inf")
        self.load_finished_at = 0
        self.workload_data_count = 0

        self.sla_checker = sla.SLAChecker(self.workload_cfg)
        self.hook_executor = hook.HookExecutor(self.workload_cfg, self.task)
        self.abort_on_sla_failure = abort_on_sla_failure
        self.is_done = threading.Event()
        self.unexpected_failure = {}
        self.results = []
        self.thread = threading.Thread(target=self._consume_results)
        self.aborting_checker = threading.Thread(target=self.wait_and_abort)
        if self.workload_cfg["hooks"]:
            self.event_thread = threading.Thread(target=self._consume_events)
        self._cm = ctx_manager

    def __enter__(self):
        self.thread.start()
        self.aborting_checker.start()
        if self.workload_cfg["hooks"]:
            self.event_thread.start()
        self.start = time.time()
        return self

    def _consume_results(self):
        task_aborted = False
        while True:
            if self.runner.result_queue:
                results = self.runner.result_queue.popleft()
                self.results.extend(results)
                for r in results:
                    self.load_started_at = min(r["timestamp"],
                                               self.load_started_at)
                    self.load_finished_at = max(r["duration"] + r["timestamp"],
                                                self.load_finished_at)
                    success = self.sla_checker.add_iteration(r)
                    if (self.abort_on_sla_failure and
                            not success and
                            not task_aborted):
                        self.sla_checker.set_aborted_on_sla()
                        self.runner.abort()
                        self.task.update_status(
                            consts.TaskStatus.SOFT_ABORTING)
                        task_aborted = True

                # save results chunks
                chunk_size = CONF.raw_result_chunk_size
                while len(self.results) >= chunk_size:
                    results_chunk = self.results[:chunk_size]
                    self.results = self.results[chunk_size:]
                    results_chunk.sort(key=lambda x: x["timestamp"])
                    self.workload.add_workload_data(self.workload_data_count,
                                                    {"raw": results_chunk})
                    self.workload_data_count += 1

            elif self.is_done.isSet():
                break
            else:
                time.sleep(0.1)

    def _consume_events(self):
        while not self.is_done.isSet() or self.runner.event_queue:
            if self.runner.event_queue:
                event = self.runner.event_queue.popleft()
                self.hook_executor.on_event(
                    event_type=event["type"], value=event["value"])
            else:
                time.sleep(0.01)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.finish = time.time()
        self.is_done.set()
        self.aborting_checker.join()
        self.thread.join()

        if exc_type:
            self.sla_checker.set_unexpected_failure(exc_value)

        if objects.Task.get_status(
                self.task["uuid"]) == consts.TaskStatus.ABORTED:
            self.sla_checker.set_aborted_manually()

        load_duration = max(self.load_finished_at - self.load_started_at, 0)

        LOG.info("Load duration is: %s" % strutils.format_float_to_str(
            load_duration))
        LOG.info("Full runner duration is: %s" %
                 strutils.format_float_to_str(self.runner.run_duration))
        LOG.info("Full duration is: %s" % strutils.format_float_to_str(
            self.finish - self.start))

        results = {}
        if self.workload_cfg["hooks"]:
            self.event_thread.join()
            results["hooks_results"] = self.hook_executor.results()

        if self.results:
            # NOTE(boris-42): Sort in order of starting
            #                 instead of order of ending
            self.results.sort(key=lambda x: x["timestamp"])
            self.workload.add_workload_data(self.workload_data_count,
                                            {"raw": self.results})
        start_time = (self.load_started_at
                      if self.load_started_at != float("inf") else None)
        self.workload.set_results(load_duration=load_duration,
                                  full_duration=(self.finish - self.start),
                                  sla_results=self.sla_checker.results(),
                                  start_time=start_time,
                                  contexts_results=self._cm.contexts_results(),
                                  **results)

    @staticmethod
    def is_task_in_aborting_status(task_uuid, check_soft=True):
        """Checks task is in abort stages

        :param task_uuid: UUID of task to check status
        :type task_uuid: str
        :param check_soft: check or not SOFT_ABORTING status
        :type check_soft: bool
        """
        stages = [consts.TaskStatus.ABORTING, consts.TaskStatus.ABORTED]
        if check_soft:
            stages.append(consts.TaskStatus.SOFT_ABORTING)
        return objects.Task.get_status(task_uuid) in stages

    def wait_and_abort(self):
        """Waits until abort signal is received and aborts runner in this case.

        Has to be run from different thread simultaneously with the
        runner.run method.
        """

        while not self.is_done.isSet():
            if self.is_task_in_aborting_status(self.task["uuid"],
                                               check_soft=False):
                self.runner.abort()
                self.task.update_status(consts.TaskStatus.ABORTED)
                break
            time.sleep(2.0)


class TaskAborted(Exception):
    """Task aborted exception

    Used by TaskEngine to interrupt task run.
    """


class TaskEngine(object):
    """The Task engine class is used to execute benchmark scenarios.

    An instance of this class is initialized by the API with the task
    configuration and then is used to validate and execute all specified
    in config subtasks.

    .. note::

        Typical usage:
            ...

            engine = TaskEngine(config, task, env)
            engine.validate()   # to test config
            engine.run()        # to run config
    """

    def __init__(self, config, task, env, abort_on_sla_failure=False):
        """TaskEngine constructor.

        :param config: An instance of a rally.task.config.TaskConfig
        :param task: Instance of Task,
                     the current task which is being performed
        :param env: Instance of Environment,
        :param abort_on_sla_failure: True if the execution should be stopped
                                     when some SLA check fails
        """
        self.config = config
        self.task = task
        self.env = env
        self.abort_on_sla_failure = abort_on_sla_failure

    def _validate_workload(self, workload, vcontext=None, vtype=None):
        """Validate a workload.

        :param workload: a workload configuration
        :param vcontext: a validation context
        :param vtype: a type of validation (platform, syntax or semantic)
        """
        scenario_cls = scenario.Scenario.get(workload["name"])
        scenario_context = copy.deepcopy(scenario_cls.get_default_context())
        results = []

        results.extend(scenario.Scenario.validate(
            name=workload["name"],
            context=vcontext,
            config=workload,
            plugin_cfg=None,
            vtype=vtype))

        if workload["runner_type"]:
            results.extend(runner.ScenarioRunner.validate(
                name=workload["runner_type"],
                context=vcontext,
                config=None,
                plugin_cfg=workload["runner"],
                vtype=vtype))

        for context_name, context_conf in workload["contexts"].items():
            results.extend(context.Context.validate(
                name=context_name,
                context=vcontext,
                config=None,
                plugin_cfg=context_conf,
                vtype=vtype))

        for context_name, context_conf in scenario_context.items():
            results.extend(context.Context.validate(
                name=context_name,
                context=vcontext,
                config=None,
                plugin_cfg=context_conf,
                allow_hidden=True,
                vtype=vtype))

        for sla_name, sla_conf in workload["sla"].items():
            results.extend(sla.SLA.validate(
                name=sla_name,
                context=vcontext,
                config=None,
                plugin_cfg=sla_conf,
                vtype=vtype))

        for hook_conf in workload["hooks"]:
            action_name, action_cfg = hook_conf["action"]
            results.extend(hook.HookAction.validate(
                name=action_name,
                context=vcontext,
                config=None,
                plugin_cfg=action_cfg,
                vtype=vtype))

            trigger_name, trigger_cfg = hook_conf["trigger"]
            results.extend(hook.HookTrigger.validate(
                name=trigger_name,
                context=vcontext,
                config=None,
                plugin_cfg=trigger_cfg,
                vtype=vtype))

        if results:
            msg = "\n ".join(results)
            kw = {"name": workload["name"],
                  "pos": workload["position"],
                  "config": json.dumps(
                      objects.Workload.to_task(workload)),
                  "reason": msg}

            raise exceptions.InvalidTaskConfig(**kw)

    @logging.log_task_wrapper(LOG.info, "Task validation of syntax.")
    def _validate_config_syntax(self, config):
        for subtask in config.subtasks:
            for workload in subtask["workloads"]:
                self._validate_workload(workload, vtype="syntax")

    @logging.log_task_wrapper(LOG.info,
                              "Task validation of required platforms.")
    def _validate_config_platforms(self, config):
        # FIXME(andreykurilin): prepare the similar context object to others
        platforms = dict(
            (p["platform_name"], p["platform_data"])
            for p in self.env.data["platforms"].values())
        ctx = {"task": self.task,
               "platforms": platforms}
        for subtask in config.subtasks:
            for workload in subtask["workloads"]:
                self._validate_workload(
                    workload, vcontext=ctx, vtype="platform")

    @logging.log_task_wrapper(LOG.info, "Task validation of semantic.")
    def _validate_config_semantic(self, config):
        LOG.info("Check health of the environment '%s'." % self.env.uuid)
        failed = []
        for p, res in self.env.check_health().items():
            LOG.info("Platform %s (available: %s): %s" %
                     (p, res["available"], res["message"]))
            if not res["available"]:
                failed.append(p)
                if logging.is_debug():
                    LOG.error(res["traceback"])
        if failed:
            raise exceptions.ValidationError(
                "One or several platforms are not available: %s. Check logs "
                "for more details." % ", ".join(failed))
        validation_ctx = self.env.get_validation_context()

        env_data = self.env.data
        env_data["platforms"] = dict(
            (p["platform_name"], p["platform_data"])
            for p in env_data["platforms"].values())

        ctx_obj = {"task": self.task,
                   "config": validation_ctx,
                   "env": env_data}

        with context.ContextManager(ctx_obj):
            for subtask in config.subtasks:
                for workload in subtask["workloads"]:
                    self._validate_workload(
                        workload, vcontext=ctx_obj, vtype="semantic")

    @logging.log_task_wrapper(LOG.info, "Task validation.")
    def validate(self, only_syntax=False):
        """Perform full task configuration validation.

        :param only_syntax: Check only syntax of task configuration
        """
        self.task.update_status(consts.TaskStatus.VALIDATING)
        try:
            self._validate_config_syntax(self.config)
            if only_syntax:
                return
            self._validate_config_platforms(self.config)
            self._validate_config_semantic(self.config)
        except Exception as e:
            exception_info = json.dumps(traceback.format_exc(), indent=2,
                                        separators=(",", ": "))
            self.task.set_failed(type(e).__name__, str(e), exception_info)
            expected_errors = (
                # this error is a wrapper for all error messages from
                # validators.
                exceptions.InvalidTaskConfig,
                # rally.task.task_cfg raises it
                # _validate_config_semantic raises this error in case of
                # failed platform check{s}
                exceptions.ValidationError)
            if logging.is_debug() and not isinstance(e, expected_errors):
                LOG.exception("Unexpected error had happened while validating "
                              "task.")
            raise

    def _prepare_context(self, ctx, scenario_name, owner_id):
        context_config = {}
        # restore full names of plugins
        scenario_plugin = scenario.Scenario.get(scenario_name)
        for k, v in scenario_plugin.get_default_context().items():
            c = context.Context.get(k, allow_hidden=True)
            context_config[c.get_fullname()] = v
        for k, v in ctx.items():
            context_config[context.Context.get(k).get_fullname()] = v

        env_data = self.env.data
        env_data["platforms"] = dict(
            (p["platform_name"], p["platform_data"])
            for p in env_data["platforms"].values())

        context_obj = {
            "task": self.task,
            "owner_id": owner_id,
            "scenario_name": scenario_name,
            "config": context_config,
            "env": env_data
        }
        return context_obj

    @logging.log_task_wrapper(LOG.info, "Running task.")
    def run(self):
        """Run the benchmark according to the test configuration.

        Test configuration is specified on engine initialization.

        :returns: List of dicts, each dict containing the results of all the
                  corresponding benchmark test launches
        """
        self.task.update_status(consts.TaskStatus.RUNNING)

        try:
            for subtask in self.config.subtasks:
                self._run_subtask(subtask)
        except TaskAborted:
            LOG.info("Received aborting signal.")
            self.task.update_status(consts.TaskStatus.ABORTED)
        else:
            if objects.Task.get_status(
                    self.task["uuid"]) != consts.TaskStatus.ABORTED:
                self.task.update_status(consts.TaskStatus.FINISHED)

    def _run_subtask(self, subtask):
        subtask_obj = self.task.add_subtask(title=subtask["title"],
                                            description=subtask["description"],
                                            contexts=subtask["contexts"])

        try:
            # TODO(astudenov): add subtask context here
            for workload in subtask["workloads"]:
                self._run_workload(subtask_obj, workload)
        except TaskAborted:
            subtask_obj.update_status(consts.SubtaskStatus.ABORTED)
            raise
        except Exception:
            subtask_obj.update_status(consts.SubtaskStatus.CRASHED)
            # TODO(astudenov): save error to DB
            LOG.exception("Unexpected exception during the subtask execution")

            # NOTE(astudenov): crash task after exception in subtask
            self.task.update_status(consts.TaskStatus.CRASHED)
            raise
        else:
            subtask_obj.update_status(consts.SubtaskStatus.FINISHED)

    def _run_workload(self, subtask_obj, workload):
        if ResultConsumer.is_task_in_aborting_status(self.task["uuid"]):
            raise TaskAborted()
        workload_obj = subtask_obj.add_workload(
            name=workload["name"],
            description=workload["description"],
            position=workload["position"],
            runner=workload["runner"],
            runner_type=workload["runner_type"],
            hooks=workload["hooks"],
            contexts=workload["contexts"],
            sla=workload["sla"],
            args=workload["args"])
        workload["uuid"] = workload_obj["uuid"]

        workload_cfg = objects.Workload.to_task(workload)
        LOG.info("Running workload: \n"
                 "  position = %(position)s\n"
                 "  config = %(cfg)s"
                 % {"position": workload["position"],
                    "cfg": json.dumps(workload_cfg, indent=3)})

        runner_cls = runner.ScenarioRunner.get(workload["runner_type"])
        runner_obj = runner_cls(self.task, workload["runner"])
        context_obj = self._prepare_context(
            workload["contexts"], workload["name"], workload_obj["uuid"])
        try:
            ctx_manager = context.ContextManager(context_obj)
            with ResultConsumer(workload, task=self.task, subtask=subtask_obj,
                                workload=workload_obj, runner=runner_obj,
                                abort_on_sla_failure=self.abort_on_sla_failure,
                                ctx_manager=ctx_manager):
                with ctx_manager:
                    runner_obj.run(workload["name"], context_obj,
                                   workload["args"])
        except Exception:
            LOG.exception("Unexpected exception during the workload execution")
            # TODO(astudenov): save error to DB
