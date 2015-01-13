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
import random

import jsonschema
import six

from rally.benchmark.scenarios import base as scenario_base
from rally.benchmark import types
from rally.benchmark import utils
from rally.common import log as logging
from rally.common import utils as rutils
from rally import consts
from rally import exceptions
from rally import osclients


LOG = logging.getLogger(__name__)


def format_result_on_timeout(exc, timeout):
    return {
        "duration": timeout,
        "idle_duration": 0,
        "scenario_output": {"errors": "", "data": {}},
        "atomic_actions": {},
        "error": utils.format_exc(exc)
    }


def _get_scenario_context(context):
    scenario_ctx = {}
    for key, value in six.iteritems(context):
        if key not in ["users", "tenants"]:
            scenario_ctx[key] = value

    if "users" in context:
        user = random.choice(context["users"])
        tenant = context["tenants"][user["tenant_id"]]
        scenario_ctx["user"], scenario_ctx["tenant"] = user, tenant

    return scenario_ctx


def _run_scenario_once(args):
    iteration, cls, method_name, context, kwargs = args

    LOG.info("Task %(task)s | ITER: %(iteration)s START" %
             {"task": context["task"]["uuid"], "iteration": iteration})

    context["iteration"] = iteration
    scenario = cls(
            context=context,
            admin_clients=osclients.Clients(context["admin"]["endpoint"]),
            clients=osclients.Clients(context["user"]["endpoint"]))

    error = []
    scenario_output = {"errors": "", "data": {}}
    try:
        with rutils.Timer() as timer:
            scenario_output = getattr(scenario,
                                      method_name)(**kwargs) or scenario_output
    except Exception as e:
        error = utils.format_exc(e)
        if logging.is_debug():
            LOG.exception(e)
    finally:
        status = "Error %s: %s" % tuple(error[0:2]) if error else "OK"
        LOG.info("Task %(task)s | ITER: %(iteration)s END: %(status)s" %
                 {"task": context["task"]["uuid"], "iteration": iteration,
                  "status": status})

        return {"duration": timer.duration() - scenario.idle_duration(),
                "timestamp": str(timer.timestamp()),
                "idle_duration": scenario.idle_duration(),
                "error": error,
                "scenario_output": scenario_output,
                "atomic_actions": scenario.atomic_actions()}


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
                "type": "string",
                "format": "date-time"
            },
            "idle_duration": {
                "type": "number"
            },
            "scenario_output": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "patternProperties": {
                            ".*": {"type": "number"}
                        }
                    },
                    "errors": {
                        "type": "string"
                    },
                },
                "additionalProperties": False
            },
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


class ScenarioRunner(object):
    """Base class for all scenario runners.

    Scenario runner is an entity that implements a certain strategy of
    launching benchmark scenarios, e.g. running them continuously or
    periodically for a given number of times or seconds.
    These strategies should be implemented in subclasses of ScenarioRunner
    in the_run_scenario() method.
    """

    CONFIG_SCHEMA = {}

    def __init__(self, task, config):
        """Runner constructor.

        It sets task and config to local variables. Also initialize
        result_queue, where results will be put by _send_result method.

        :param task: Instance of objects.Task
        :param config: Dict with runner section from benchmark configuration
        """
        self.task = task
        self.config = config
        self.result_queue = collections.deque()

    @staticmethod
    def _get_cls(runner_type):
        for runner in rutils.itersubclasses(ScenarioRunner):
            if runner_type == runner.__execution_type__:
                return runner
        raise exceptions.NoSuchRunner(type=runner_type)

    @staticmethod
    def get_runner(task, config):
        """Returns instance of a scenario runner for execution type.

        :param task: instance of objects.Task corresponding to current task
        :param config: contents of "runner" section from task configuration
                       for specific benchmark
        """
        return ScenarioRunner._get_cls(config["type"])(task, config)

    @staticmethod
    def validate(config):
        """Validates runner's part of task config."""
        runner = ScenarioRunner._get_cls(config.get("type",
                                                    consts.RunnerType.SERIAL))
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
        cls = scenario_base.Scenario.get_by_name(cls_name)

        # NOTE(boris-42): processing @types decorators
        args = types.preprocess(cls, method_name, context, args)

        with rutils.Timer() as timer:
            self._run_scenario(cls, method_name, context, args)
        return timer.duration()

    def _send_result(self, result):
        """Send partial result to consumer.

        :param result: Result dict to be sent. It should match the
                       ScenarioRunnerResult schema, otherwise
                       ValidationError is raised.
        """
        self.result_queue.append(ScenarioRunnerResult(result))
