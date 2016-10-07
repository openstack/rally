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

import ddt
import jsonschema
import mock

from rally import consts
from rally.plugins.common.hook import sys_call
from tests.unit import fakes
from tests.unit import test


@ddt.ddt
class SysCallHookTestCase(test.TestCase):

    def test_validate(self):
        sys_call.SysCallHook.validate(
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
            jsonschema.ValidationError, sys_call.SysCallHook.validate, conf)

    @ddt.data(
        {"stdout": "foo output",
         "expected": {
             "additive": [],
             "complete": [{"chart_plugin": "TextArea",
                           "data": ["RetCode: 0", "StdOut: foo output",
                                    "StdErr: (empty)"],
                           "description": "Args: foo cmd",
                           "title": "System call"}]}},
        {"stdout": """{"additive": [],
                       "complete": [
                         {"chart_plugin": "Pie", "title": "Bar Pie",
                          "data": [["A", 4], ["B", 2]]}]}""",
         "expected": {
             "additive": [],
             "complete": [{"chart_plugin": "Pie", "data": [["A", 4], ["B", 2]],
                           "title": "Bar Pie"}]}})
    @ddt.unpack
    @mock.patch("rally.common.utils.Timer", side_effect=fakes.FakeTimer)
    @mock.patch("rally.plugins.common.hook.sys_call.subprocess.Popen")
    def test_run(self, mock_popen, mock_timer, stdout, expected):
        popen_instance = mock_popen.return_value
        popen_instance.returncode = 0
        popen_instance.communicate.return_value = (stdout, "")
        hook = sys_call.SysCallHook(mock.Mock(), "foo cmd", {"iteration": 1})

        hook.run_sync()

        self.assertEqual(
            {"finished_at": fakes.FakeTimer().finish_timestamp(),
             "output": expected,
             "started_at": fakes.FakeTimer().timestamp(),
             "status": consts.HookStatus.SUCCESS,
             "triggered_by": {"iteration": 1}},
            hook.result())

        mock_popen.assert_called_once_with(["foo", "cmd"],
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE)

    @mock.patch("rally.common.utils.Timer", side_effect=fakes.FakeTimer)
    @mock.patch("rally.plugins.common.hook.sys_call.subprocess.Popen")
    def test_run_error(self, mock_popen, mock_timer):
        popen_instance = mock_popen.return_value
        popen_instance.communicate.return_value = ("foo out", "foo err")
        popen_instance.returncode = 1
        popen_instance.stdout.read.return_value = b"No such file or directory"

        task = mock.MagicMock()
        sys_call_hook = sys_call.SysCallHook(task, "/bin/bash -c 'ls'",
                                             {"iteration": 1})

        sys_call_hook.run_sync()

        self.assertEqual(
            {"error": {"details": "foo err",
                       "etype": "n/a",
                       "msg": "Subprocess returned 1"},
             "finished_at": fakes.FakeTimer().finish_timestamp(),
             "output": {
                 "additive": [],
                 "complete": [{"chart_plugin": "TextArea",
                               "data": ["RetCode: 1",
                                        "StdOut: foo out",
                                        "StdErr: foo err"],
                               "description": "Args: /bin/bash -c 'ls'",
                               "title": "System call"}]},
             "started_at": fakes.FakeTimer().timestamp(),
             "status": "failed",
             "triggered_by": {"iteration": 1}}, sys_call_hook.result())

        mock_popen.assert_called_once_with(
            ["/bin/bash", "-c", "ls"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
