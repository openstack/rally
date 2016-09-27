# Copyright 2016: Mirantis Inc.
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

"""Tests for HookExecutor and Hook classes."""

import jsonschema
import mock

from rally import consts
from rally.task import hook
from tests.unit import fakes
from tests.unit import test


@hook.configure(name="dummy_hook")
class DummyHook(hook.Hook):
    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "error": {"type": "array"},
            "output": {"type": "object"},
        },
        "required": ["status"],
        "additionalProperties": False,
    }

    def run(self):
        self.set_status(self.config["status"])

        error = self.config.get("error")
        if error:
            self.set_error(*error)

        output = self.config.get("output")
        if output:
            self.add_output(**output)


class HookExecutorTestCase(test.TestCase):

    def setUp(self):
        super(HookExecutorTestCase, self).setUp()
        self.conf = {
            "hooks": [
                {
                    "name": "dummy_hook",
                    "description": "dummy_action",
                    "args": {
                        "status": consts.HookStatus.SUCCESS,
                    },
                    "trigger": {
                        "name": "event",
                        "args": {
                            "unit": "iteration",
                            "at": [1],
                        }
                    }
                }
            ]
        }
        self.task = mock.MagicMock()

    @mock.patch("rally.task.hook.HookExecutor._timer_method")
    @mock.patch("rally.common.utils.Timer", side_effect=fakes.FakeTimer)
    def test_results(self, mock_timer, mock__timer_method):
        hook_executor = hook.HookExecutor(self.conf, self.task)
        hook_executor.on_event(event_type="iteration", value=1)

        self.assertEqual(
            [{"config": self.conf["hooks"][0],
              "results": [{
                  "triggered_by": {"event_type": "iteration", "value": 1},
                  "started_at": fakes.FakeTimer().timestamp(),
                  "finished_at": fakes.FakeTimer().finish_timestamp(),
                  "status": consts.HookStatus.SUCCESS}],
              "summary": {consts.HookStatus.SUCCESS: 1}}],
            hook_executor.results())

    @mock.patch("rally.task.hook.HookExecutor._timer_method")
    @mock.patch("rally.common.utils.Timer", side_effect=fakes.FakeTimer)
    def test_result_optional(self, mock_timer, mock__timer_method):
        hook_args = self.conf["hooks"][0]["args"]
        hook_args["error"] = ["Exception", "Description", "Traceback"]
        hook_args["output"] = {"additive": None, "complete": None}

        hook_executor = hook.HookExecutor(self.conf, self.task)
        hook_executor.on_event(event_type="iteration", value=1)

        self.assertEqual(
            [{"config": self.conf["hooks"][0],
              "results": [{
                  "triggered_by": {"event_type": "iteration", "value": 1},
                  "started_at": fakes.FakeTimer().timestamp(),
                  "finished_at": fakes.FakeTimer().finish_timestamp(),
                  "error": {"details": "Traceback", "etype": "Exception",
                            "msg": "Description"},
                  "output": {"additive": [], "complete": []},
                  "status": consts.HookStatus.FAILED}],
              "summary": {consts.HookStatus.FAILED: 1}}],
            hook_executor.results())

    def test_empty_result(self):
        hook_executor = hook.HookExecutor(self.conf, self.task)
        self.assertEqual([{"config": self.conf["hooks"][0], "results": [],
                           "summary": {}}],
                         hook_executor.results())

    @mock.patch("rally.task.hook.HookExecutor._timer_method")
    @mock.patch.object(DummyHook, "run", side_effect=Exception("My err msg"))
    @mock.patch("rally.common.utils.Timer", side_effect=fakes.FakeTimer)
    def test_failed_result(self, mock_timer, mock_dummy_hook_run,
                           mock__timer_method):
        hook_executor = hook.HookExecutor(self.conf, self.task)
        hook_executor.on_event(event_type="iteration", value=1)

        self.assertEqual(
            [{"config": self.conf["hooks"][0],
              "results": [{
                  "triggered_by": {"event_type": "iteration", "value": 1},
                  "error": {"etype": "Exception",
                            "msg": mock.ANY, "details": mock.ANY},
                  "started_at": fakes.FakeTimer().timestamp(),
                  "finished_at": fakes.FakeTimer().finish_timestamp(),
                  "status": consts.HookStatus.FAILED}],
              "summary": {consts.HookStatus.FAILED: 1}}],
            hook_executor.results())

    @mock.patch("rally.common.utils.Timer", side_effect=fakes.FakeTimer)
    def test_time_event(self, mock_timer):
        trigger_args = self.conf["hooks"][0]["trigger"]["args"]
        trigger_args["unit"] = "time"

        hook_executor = hook.HookExecutor(self.conf, self.task)
        hook_executor.on_event(event_type="time", value=1)

        self.assertEqual(
            [{"config": self.conf["hooks"][0],
              "results": [{
                  "triggered_by": {"event_type": "time", "value": 1},
                  "started_at": fakes.FakeTimer().timestamp(),
                  "finished_at": fakes.FakeTimer().finish_timestamp(),
                  "status": consts.HookStatus.SUCCESS}],
              "summary": {consts.HookStatus.SUCCESS: 1}}],
            hook_executor.results())

    @mock.patch("rally.common.utils.Timer", side_effect=fakes.FakeTimer)
    def test_time_periodic(self, mock_timer):
        self.conf["hooks"][0]["trigger"] = {
            "name": "periodic", "args": {"unit": "time", "step": 2}}
        hook_executor = hook.HookExecutor(self.conf, self.task)

        for i in range(1, 7):
            hook_executor.on_event(event_type="time", value=i)

        self.assertEqual(
            [{
                "config": self.conf["hooks"][0],
                "results":[
                    {
                        "triggered_by": {"event_type": "time", "value": 2},
                        "started_at": fakes.FakeTimer().timestamp(),
                        "finished_at": fakes.FakeTimer().finish_timestamp(),
                        "status": consts.HookStatus.SUCCESS
                    },
                    {
                        "triggered_by": {"event_type": "time", "value": 4},
                        "started_at": fakes.FakeTimer().timestamp(),
                        "finished_at": fakes.FakeTimer().finish_timestamp(),
                        "status": consts.HookStatus.SUCCESS
                    },
                    {
                        "triggered_by": {"event_type": "time", "value": 6},
                        "started_at": fakes.FakeTimer().timestamp(),
                        "finished_at": fakes.FakeTimer().finish_timestamp(),
                        "status": consts.HookStatus.SUCCESS
                    }
                ],
                "summary": {consts.HookStatus.SUCCESS: 3}
            }],
            hook_executor.results())

    @mock.patch("rally.common.utils.Stopwatch", autospec=True)
    @mock.patch("rally.common.utils.Timer", side_effect=fakes.FakeTimer)
    def test_timer_thread(self, mock_timer, mock_stopwatch):
        trigger_args = self.conf["hooks"][0]["trigger"]["args"]
        trigger_args["unit"] = "time"
        hook_executor = hook.HookExecutor(self.conf, self.task)

        def stop_timer(sec):
            if sec == 3:
                hook_executor._timer_stop_event.set()

        stopwatch_inst = mock_stopwatch.return_value
        stopwatch_inst.sleep.side_effect = stop_timer

        hook_executor.on_event(event_type="iteration", value=1)
        self.assertTrue(hook_executor._timer_stop_event.wait(1))

        self.assertEqual(
            [{"config": self.conf["hooks"][0],
              "results": [{
                  "triggered_by": {"event_type": "time", "value": 1},
                  "started_at": fakes.FakeTimer().timestamp(),
                  "finished_at": fakes.FakeTimer().finish_timestamp(),
                  "status": consts.HookStatus.SUCCESS}],
              "summary": {consts.HookStatus.SUCCESS: 1}
              }],
            hook_executor.results())

        stopwatch_inst.start.assert_called_once_with()
        stopwatch_inst.sleep.assert_has_calls([
            mock.call(1),
            mock.call(2),
            mock.call(3),
        ])


class HookTestCase(test.TestCase):

    def test_validate(self):
        DummyHook.validate(
            {
                "name": "dummy_hook",
                "description": "dummy_action",
                "args": {
                    "status": consts.HookStatus.SUCCESS,
                },
                "trigger": {
                    "name": "event",
                    "args": {
                        "unit": "iteration",
                        "at": [1],
                    }
                }
            }
        )

    def test_validate_error(self):
        conf = {
            "name": "dummy_hook",
            "description": "dummy_action",
            "args": 3,
            "trigger": {
                "name": "event",
                "args": {
                    "unit": "iteration",
                    "at": [1],
                }
            }
        }
        self.assertRaises(jsonschema.ValidationError, DummyHook.validate, conf)

    @mock.patch("rally.common.utils.Timer", side_effect=fakes.FakeTimer)
    def test_result(self, mock_timer):
        task = mock.MagicMock()
        triggered_by = {"event_type": "iteration", "value": 1}
        dummy_hook = DummyHook(task, {"status": consts.HookStatus.SUCCESS},
                               triggered_by)
        dummy_hook.run_sync()

        self.assertEqual(
            {"started_at": fakes.FakeTimer().timestamp(),
             "finished_at": fakes.FakeTimer().finish_timestamp(),
             "triggered_by": triggered_by,
             "status": consts.HookStatus.SUCCESS}, dummy_hook.result())

    def test_result_not_started(self):
        task = mock.MagicMock()
        triggered_by = {"event_type": "iteration", "value": 1}
        dummy_hook = DummyHook(task, {"status": consts.HookStatus.SUCCESS},
                               triggered_by)

        self.assertEqual(
            {"started_at": 0.0,
             "finished_at": 0.0,
             "triggered_by": triggered_by,
             "status": consts.HookStatus.SUCCESS}, dummy_hook.result())
