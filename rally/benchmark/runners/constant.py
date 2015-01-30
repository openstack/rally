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

from six import moves

from rally.benchmark.runners import base
from rally.benchmark import utils
from rally.common import log as logging
from rally import consts


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
        "$schema": consts.JSON_SCHEMA,
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
    def _iter_scenario_args(cls, method, ctx, args, times, aborted):
        for i in moves.range(times):
            if aborted.is_set():
                break
            yield (i, cls, method, base._get_scenario_context(ctx), args)

    def _run_scenario(self, cls, method, context, args):
        timeout = self.config.get("timeout", 600)
        concurrency = self.config.get("concurrency", 1)
        # NOTE(msdubov): If not specified, perform single scenario run.
        times = self.config.get("times", 1)

        pool = multiprocessing.Pool(concurrency)
        iter_result = pool.imap(base._run_scenario_once,
                                self._iter_scenario_args(cls, method, context,
                                                         args, times,
                                                         self.aborted))
        while True:
            try:
                result = iter_result.next(timeout)
            except multiprocessing.TimeoutError as e:
                result = base.format_result_on_timeout(e, timeout)
            except StopIteration:
                break

            self._send_result(result)

        pool.close()
        pool.join()


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
        "$schema": consts.JSON_SCHEMA,
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
    def _iter_scenario_args(cls, method, ctx, args, aborted):
        def _scenario_args(i):
            if aborted.is_set():
                raise StopIteration()
            return (i, cls, method, base._get_scenario_context(ctx), args)
        return _scenario_args

    def _run_scenario(self, cls, method, context, args):
        timeout = self.config.get("timeout", 600)
        concurrency = self.config.get("concurrency", 1)
        duration = self.config.get("duration")

        pool = multiprocessing.Pool(concurrency)

        run_args = utils.infinite_run_args_generator(
                    self._iter_scenario_args(cls, method, context, args,
                                             self.aborted))
        iter_result = pool.imap(base._run_scenario_once, run_args)

        start = time.time()
        while True:
            try:
                result = iter_result.next(timeout)
            except multiprocessing.TimeoutError as e:
                result = base.format_result_on_timeout(e, timeout)
            except StopIteration:
                break

            self._send_result(result)

            if time.time() - start > duration:
                break

        pool.terminate()
        pool.join()
