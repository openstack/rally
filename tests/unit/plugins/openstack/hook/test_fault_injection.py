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


import ddt
import jsonschema
import mock
from os_faults.api import error

from rally import consts
from rally.plugins.openstack.hook import fault_injection
from tests.unit import fakes
from tests.unit import test


def create_config(**kwargs):
    return {
        "name": "fault_injection",
        "args": kwargs,
        "trigger": {
            "name": "event",
            "args": {
                "unit": "iteration",
                "at": [10]
            }
        }
    }


@ddt.ddt
class FaultInjectionHookTestCase(test.TestCase):

    def setUp(self):
        super(FaultInjectionHookTestCase, self).setUp()
        self.task = {"deployment_uuid": "foo_uuid"}

    @ddt.data((create_config(action="foo"), True),
              (create_config(action="foo", verify=True), True),
              (create_config(action=10), False),
              (create_config(action="foo", verify=10), False),
              (create_config(), False))
    @ddt.unpack
    def test_config_schema(self, config, valid):
        if valid:
            fault_injection.FaultInjectionHook.validate(config)
        else:
            self.assertRaises(jsonschema.ValidationError,
                              fault_injection.FaultInjectionHook.validate,
                              config)

    @mock.patch("rally.common.objects.Deployment.get")
    @mock.patch("os_faults.human_api")
    @mock.patch("os_faults.connect")
    @mock.patch("rally.common.utils.Timer", side_effect=fakes.FakeTimer)
    def test_run(self, mock_timer, mock_connect, mock_human_api,
                 mock_deployment_get):
        injector_inst = mock_connect.return_value
        hook = fault_injection.FaultInjectionHook(
            self.task, {"action": "foo", "verify": True},
            {"iteration": 1})

        hook.run_sync()

        self.assertEqual(
            {"finished_at": fakes.FakeTimer().finish_timestamp(),
             "started_at": fakes.FakeTimer().timestamp(),
             "status": consts.HookStatus.SUCCESS,
             "triggered_by": {"iteration": 1}},
            hook.result())

        mock_connect.assert_called_once_with(None)
        injector_inst.verify.assert_called_once_with()
        mock_human_api.assert_called_once_with(injector_inst, "foo")

    @mock.patch("rally.common.objects.Deployment.get")
    @mock.patch("os_faults.human_api")
    @mock.patch("os_faults.connect")
    @mock.patch("rally.common.utils.Timer", side_effect=fakes.FakeTimer)
    def test_run_extra_config(self, mock_timer, mock_connect, mock_human_api,
                              mock_deployment_get):
        mock_deployment_get.return_value = {
            "config": {"type": "ExistingCloud",
                       "extra": {"cloud_config": {"conf": "foo_config"}}}}
        injector_inst = mock_connect.return_value
        hook = fault_injection.FaultInjectionHook(
            self.task, {"action": "foo"}, {"iteration": 1})

        hook.run_sync()

        self.assertEqual(
            {"finished_at": fakes.FakeTimer().finish_timestamp(),
             "started_at": fakes.FakeTimer().timestamp(),
             "status": consts.HookStatus.SUCCESS,
             "triggered_by": {"iteration": 1}},
            hook.result())

        mock_connect.assert_called_once_with({"conf": "foo_config"})
        mock_human_api.assert_called_once_with(injector_inst, "foo")

    @mock.patch("rally.common.objects.Deployment.get")
    @mock.patch("os_faults.human_api")
    @mock.patch("os_faults.connect")
    @mock.patch("rally.common.utils.Timer", side_effect=fakes.FakeTimer)
    def test_run_error(self, mock_timer, mock_connect, mock_human_api,
                       mock_deployment_get):
        injector_inst = mock_connect.return_value
        mock_human_api.side_effect = error.OSFException("foo error")
        hook = fault_injection.FaultInjectionHook(
            self.task, {"action": "foo", "verify": True},
            {"iteration": 1})

        hook.run_sync()

        self.assertEqual(
            {"finished_at": fakes.FakeTimer().finish_timestamp(),
             "started_at": fakes.FakeTimer().timestamp(),
             "status": consts.HookStatus.FAILED,
             "error": {
                 "details": mock.ANY,
                 "etype": "OSFException",
                 "msg": "foo error"},
             "triggered_by": {"iteration": 1}},
            hook.result())

        mock_connect.assert_called_once_with(None)
        injector_inst.verify.assert_called_once_with()
        mock_human_api.assert_called_once_with(injector_inst, "foo")
