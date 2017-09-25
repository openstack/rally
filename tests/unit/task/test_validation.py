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

import mock

from rally.common.plugin import plugin
from rally.common import validation as common_validation
from rally.task import validation
from tests.unit import fakes
from tests.unit import test


class ValidationUtilsTestCase(test.TestCase):

    def setUp(self):
        super(ValidationUtilsTestCase, self).setUp()

        class Plugin(plugin.Plugin):
            pass

        Plugin._meta_init()
        self.addCleanup(Plugin.unregister)
        self.Plugin = Plugin

    def test_old_validator_admin(self):

        validator_func = mock.Mock()
        validator_func.return_value = None

        validator = validation.validator(validator_func)

        self.assertEqual(self.Plugin,
                         validator("a", "b", "c", d=1)(self.Plugin))
        self.assertEqual(1, len(self.Plugin._meta_get("validators")))

        vname, args, kwargs = self.Plugin._meta_get("validators")[0]
        validator_cls = common_validation.Validator.get(vname)
        validator_inst = validator_cls(*args, **kwargs)
        fake_admin = fakes.fake_credential()
        ctx = {"admin": {"credential": fake_admin}, "users": []}
        result = validator_inst.validate(ctx, {}, None, None)
        self.assertIsNone(result)

        validator_func.assert_called_once_with(
            {}, None, mock.ANY, "a", "b", "c", d=1)
        deployment = validator_func.call_args[0][2]
        self.assertEqual({"admin": fake_admin, "users": []},
                         deployment.get_credentials_for("openstack"))

    def test_old_validator_users(self):

        validator_func = mock.Mock()
        validator_func.return_value = None

        validator = validation.validator(validator_func)

        self.assertEqual(self.Plugin,
                         validator("a", "b", "c", d=1)(self.Plugin))
        self.assertEqual(1, len(self.Plugin._meta_get("validators")))

        vname, args, kwargs = self.Plugin._meta_get("validators")[0]
        validator_cls = common_validation.Validator.get(vname)
        validator_inst = validator_cls(*args, **kwargs)
        fake_admin = fakes.fake_credential()
        fake_users1 = fakes.fake_credential()
        fake_users2 = fakes.fake_credential()
        users = [{"credential": fake_users1}, {"credential": fake_users2}]
        ctx = {"admin": {"credential": fake_admin}, "users": users}
        result = validator_inst.validate(ctx, {}, None, None)
        self.assertIsNone(result)

        fake_users1.clients.assert_called_once_with()
        fake_users2.clients.assert_called_once_with()
        validator_func.assert_has_calls((
            mock.call({}, fake_users1.clients.return_value, mock.ANY,
                      "a", "b", "c", d=1),
            mock.call({}, fake_users2.clients.return_value, mock.ANY,
                      "a", "b", "c", d=1)
        ))
        for args in validator_func.call_args:
            deployment = validator_func.call_args[0][2]
            self.assertEqual({"admin": fake_admin,
                              "users": [fake_users1, fake_users2]},
                             deployment.get_credentials_for("openstack"))

    def test_old_validator_users_error(self):

        validator_func = mock.Mock()
        validator_func.return_value = validation.ValidationResult(False)

        validator = validation.validator(validator_func)

        self.assertEqual(self.Plugin,
                         validator("a", "b", "c", d=1)(self.Plugin))
        self.assertEqual(1, len(self.Plugin._meta_get("validators")))

        vname, args, kwargs = self.Plugin._meta_get("validators")[0]
        validator_cls = common_validation.Validator.get(vname)
        validator_inst = validator_cls(*args, **kwargs)
        fake_admin = fakes.fake_credential()
        fake_users1 = fakes.fake_credential()
        fake_users2 = fakes.fake_credential()
        users = [{"credential": fake_users1}, {"credential": fake_users2}]
        ctx = {"admin": {"credential": fake_admin}, "users": users}
        self.assertRaises(
            common_validation.ValidationError,
            validator_inst.validate, ctx, {}, None, None)

        fake_users1.clients.assert_called_once_with()
        fake_users2.clients.assert_called_once_with()
        validator_func.assert_called_once_with(
            {}, fake_users1.clients.return_value, mock.ANY,
            "a", "b", "c", d=1)
        deployment = validator_func.call_args[0][2]
        self.assertEqual({"admin": fake_admin,
                          "users": [fake_users1, fake_users2]},
                         deployment.get_credentials_for("openstack"))

    @mock.patch("rally.task.validation.LOG.warning")
    def test_deprecated_validator(self, mock_log_warning):

        my_deprecated_validator = validation.deprecated_validator(
            "new_validator", "deprecated_validator", "0.10.0")
        self.Plugin = my_deprecated_validator("foo", bar="baz")(self.Plugin)
        self.assertEqual([("new_validator", ("foo",), {"bar": "baz"})],
                         self.Plugin._meta_get("validators"))
        mock_log_warning.assert_called_once_with(mock.ANY)

    def _unwrap_validator(self, validator, *args, **kwargs):
        name = self.id()

        @plugin.base()
        class Foo(plugin.Plugin,
                  validation.validation.ValidatablePluginMixin):
            pass

        @plugin.configure(name)
        class TempPlugin(Foo):
            pass

        self.addCleanup(TempPlugin.unregister)

        validator(*args, **kwargs)(TempPlugin)

        def wrap_validator(config):
            return (Foo.validate(name, {}, config, {}) or [])

        return wrap_validator

    def test_share_proto_compatibility(self):
        validator = self._unwrap_validator(
            validation.validate_share_proto)
        res = validator({"args": {"share_proto": "GLUSTERFS"}})
        self.assertEqual(0, len(res))

        res = validator({"args": {"share_proto": "fake"}})
        self.assertEqual(1, len(res))
        self.assertEqual("share_proto is fake which is not a valid value from "
                         "['nfs', 'cifs', 'glusterfs', 'hdfs', 'cephfs']",
                         res[0])

    @mock.patch("rally.common.yamlutils.safe_load")
    @mock.patch("rally.plugins.openstack.validators.os.access")
    @mock.patch("rally.plugins.openstack.validators.open")
    def test_workbook_contains_workflow_compatibility(
            self, mock_open, mock_access, mock_safe_load):
        mock_safe_load.return_value = {
            "version": "2.0",
            "name": "wb",
            "workflows": {
                "wf1": {
                    "type": "direct",
                    "tasks": {
                        "t1": {
                            "action": "std.noop"
                        }
                    }
                }
            }
        }

        validator = self._unwrap_validator(
            validation.workbook_contains_workflow, "definition",
            "workflow_name")
        context = {
            "args": {
                "definition": "fake_path1",
                "workflow_name": "wf1"
            }
        }

        validator(context)
        self.assertEqual(1, mock_open.called)
        self.assertEqual(1, mock_access.called)
        self.assertEqual(1, mock_safe_load.called)

    def test_validation_result(self):
        self.assertEqual("validation success",
                         str(validation.ValidationResult(True)))
        self.assertEqual("my msg",
                         str(validation.ValidationResult(False, "my msg")))
        self.assertEqual("---------- Exception in validator ----------\ntb\n",
                         str(validation.ValidationResult(False, "my msg",
                                                         etype=Exception,
                                                         etraceback="tb\n")))
