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
import time

from rally.benchmark.runners import base
from rally.benchmark import utils
from rally import consts
from rally.openstack.common import log as logging
from rally import utils as rutils


LOG = logging.getLogger(__name__)


class ConstantScenarioRunner(base.ScenarioRunner):
    """Creates constant load executing a scenario a specified number of times.

    This runner will place a constant load on the cloud under test by
    executing each scenario iteration without pausing between iterations
    up to the number of times specified in the scenario config.

    The concurrency parameter of the scenario config controls the
    number of concurrent scenarios which execute during a single
    iteration in order to simulate the activities of multiple users
    placing load on the cloud under test.
    """

    __execution_type__ = consts.RunnerType.CONSTANT

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": rutils.JSON_SCHEMA,
        "properties": {
            "type": {
                "type": "string"
            },
            "concurrency": {
                "type": "integer",
                "minimum": 1
            },
            "times": {
                "type": "integer",
                "minimum": 1
            },
            "timeout": {
                "type": "number",
                "minimum": 1
            }
        },
        "required": ["type"],
        "additionalProperties": False
    }

    @staticmethod
    def _iter_scenario_args(cls, method, ctx, args, times):
        for i in xrange(times):
            yield (i, cls, method, base._get_scenario_context(ctx), args)

    def _run_scenario(self, cls, method, context, args):

        timeout = self.config.get("timeout", 600)
        concurrency = self.config.get("concurrency", 1)
        # NOTE(msdubov): If not specified, perform single scenario run.
        times = self.config.get("times", 1)

        pool = multiprocessing.Pool(concurrency)
        iter_result = pool.imap(base._run_scenario_once,
                                self._iter_scenario_args(cls, method, context,
                                                         args, times))

        results = []

        for i in range(times):
            try:
                result = iter_result.next(timeout)
            except multiprocessing.TimeoutError as e:
                result = {"duration": timeout, "idle_duration": 0,
                          "scenario_output": {},
                          "atomic_actions": [],
                          "error": utils.format_exc(e)}
            results.append(result)

        pool.close()
        pool.join()

        return base.ScenarioRunnerResult(results)


class ConstantForDurationScenarioRunner(base.ScenarioRunner):
    """Creates constant load executing a scenario for an interval of time.

    This runner will place a constant load on the cloud under test by
    executing each scenario iteration without pausing between iterations
    until a specified interval of time has elapsed.

    The concurrency parameter of the scenario config controls the
    number of concurrent scenarios which execute during a single
    iteration in order to simulate the activities of multiple users
    placing load on the cloud under test.
    """

    __execution_type__ = consts.RunnerType.CONSTANT_FOR_DURATION

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": rutils.JSON_SCHEMA,
        "properties": {
            "type": {
                "type": "string"
            },
            "concurrency": {
                "type": "integer",
                "minimum": 1
            },
            "duration": {
                "type": "number",
                "minimum": 0.0
            },
            "timeout": {
                "type": "number",
                "minimum": 1
            }
        },
        "required": ["type", "duration"],
        "additionalProperties": False
    }

    @staticmethod
    def _iter_scenario_args(cls, method, ctx, args):
        def _scenario_args(i):
            return (i, cls, method, base._get_scenario_context(ctx), args)
        return _scenario_args

    def _run_scenario(self, cls, method, context, args):

        timeout = self.config.get("timeout", 600)
        concurrency = self.config.get("concurrency", 1)
        duration = self.config.get("duration")

        pool = multiprocessing.Pool(concurrency)

        run_args = utils.infinite_run_args_generator(
                    self._iter_scenario_args(cls, method, context, args))
        iter_result = pool.imap(base._run_scenario_once, run_args)

        results = []
        start = time.time()
        while True:
            try:
                result = iter_result.next(timeout)
            except multiprocessing.TimeoutError as e:
                result = {"duration": timeout, "idle_duration": 0,
                          "scenario_output": {},
                          "atomic_actions": [],
                          "error": utils.format_exc(e)}
            results.append(result)

            if time.time() - start > duration:
                break

        pool.terminate()
        pool.join()

        return base.ScenarioRunnerResult(results)
