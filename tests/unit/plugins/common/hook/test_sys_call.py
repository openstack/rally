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

import subprocess

import jsonschema
import mock

from rally import consts
from rally.plugins.common.hook import sys_call
from rally.task import hook
from tests.unit import fakes
from tests.unit import test


class SysCallHookTestCase(test.TestCase):

    def test_validate(self):
        hook.Hook.validate(
            {
                "name": "sys_call",
                "description": "list folder",
                "args": "ls",
                "trigger": {
                    "name": "event",
                    "args": {
                        "unit": "iteration",
                        "at": [10]
                    }
                }
            }
        )

    def test_validate_error(self):
        conf = {
            "name": "sys_call",
            "description": "list folder",
            "args": {
                "cmd": 50,
            },
            "trigger": {
                "name": "event",
                "args": {
                    "unit": "iteration",
                    "at": [10]
                }
            }
        }
        self.assertRaises(
            jsonschema.ValidationError, hook.Hook.validate, conf)

    @mock.patch("rally.common.utils.Timer", side_effect=fakes.FakeTimer)
    @mock.patch("subprocess.Popen")
    def test_run(self, mock_popen, mock_timer):
        popen_instance = mock_popen.return_value
        popen_instance.returncode = 0

        task = mock.MagicMock()
        sys_call_hook = sys_call.SysCallHook(task, "/bin/bash -c 'ls'",
                                             {"iteration": 1}, "dummy_action")

        sys_call_hook.run_sync()
        sys_call_hook.validate_result_schema()

        self.assertEqual(
            {
                "hook": "sys_call",
                "description": "dummy_action",
                "triggered_by": {"iteration": 1},
                "started_at": fakes.FakeTimer().timestamp(),
                "finished_at": fakes.FakeTimer().finish_timestamp(),
                "status": consts.HookStatus.SUCCESS,
            }, sys_call_hook.result())

        mock_popen.assert_called_once_with(
            ["/bin/bash", "-c", "ls"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)

    @mock.patch("rally.common.utils.Timer", side_effect=fakes.FakeTimer)
    @mock.patch("subprocess.Popen")
    def test_run_error(self, mock_popen, mock_timer):
        popen_instance = mock_popen.return_value
        popen_instance.returncode = 1
        popen_instance.stdout.read.return_value = b"No such file or directory"

        task = mock.MagicMock()
        sys_call_hook = sys_call.SysCallHook(task, "/bin/bash -c 'ls'",
                                             {"iteration": 1}, "dummy_action")

        sys_call_hook.run_sync()
        sys_call_hook.validate_result_schema()

        self.assertEqual(
            {
                "hook": "sys_call",
                "description": "dummy_action",
                "triggered_by": {"iteration": 1},
                "started_at": fakes.FakeTimer().timestamp(),
                "finished_at": fakes.FakeTimer().finish_timestamp(),
                "status": consts.HookStatus.FAILED,
                "error": [
                    "n/a",
                    "Subprocess returned 1",
                    "No such file or directory",
                ]
            }, sys_call_hook.result())

        mock_popen.assert_called_once_with(
            ["/bin/bash", "-c", "ls"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
