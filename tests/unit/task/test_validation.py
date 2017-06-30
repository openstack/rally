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

import os

import ddt
import mock
from novaclient import exceptions as nova_exc

from rally.common.plugin import plugin
from rally.common import validation as common_validation
from rally import exceptions
from rally.task import validation
from tests.unit import fakes
from tests.unit import test


MODULE = "rally.task.validation."


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
        credentials = {"openstack": {"admin": fake_admin, "users": []}}
        result = validator_inst.validate(credentials, {}, None, None)
        self.assertIsInstance(result, common_validation.ValidationResult)
        self.assertTrue(result.is_valid)

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
        credentials = {"openstack": {"admin": fake_admin, "users": users}}
        result = validator_inst.validate(credentials, {}, None, None)
        self.assertIsInstance(result, common_validation.ValidationResult)
        self.assertTrue(result.is_valid)

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
            self.assertEqual({"admin": fake_admin, "users": users},
                             deployment.get_credentials_for("openstack"))

    def test_old_validator_users_error(self):

        validator_func = mock.Mock()
        validator_func.return_value = common_validation.ValidationResult(False)

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
        credentials = {"openstack": {"admin": fake_admin, "users": users}}
        result = validator_inst.validate(credentials, {}, None, None)
        self.assertIsInstance(result, common_validation.ValidationResult)
        self.assertFalse(result.is_valid)

        fake_users1.clients.assert_called_once_with()
        fake_users2.clients.assert_called_once_with()
        validator_func.assert_called_once_with(
            {}, fake_users1.clients.return_value, mock.ANY,
            "a", "b", "c", d=1)
        deployment = validator_func.call_args[0][2]
        self.assertEqual({"admin": fake_admin, "users": users},
                         deployment.get_credentials_for("openstack"))

    @mock.patch("rally.task.validation.LOG.warning")
    def test_deprecated_validator(self, mock_log_warning):

        my_deprecated_validator = validation.deprecated_validator(
            "new_validator", "deprecated_validator", "0.10.0")
        self.Plugin = my_deprecated_validator("foo", bar="baz")(self.Plugin)
        self.assertEqual([("new_validator", ("foo",), {"bar": "baz"})],
                         self.Plugin._meta_get("validators"))
        mock_log_warning.assert_called_once_with(
            "Plugin '%s' uses validator 'rally.task.validation.%s' which is "
            "deprecated in favor of '%s' (it should be used via new decorator "
            "'rally.common.validation.add') in Rally v%s.",
            self.Plugin.get_name(), "deprecated_validator", "new_validator",
            "0.10.0")


@ddt.ddt
class ValidatorsTestCase(test.TestCase):

    def _unwrap_validator(self, validator, *args, **kwargs):

        class Plugin(plugin.Plugin):
            pass

        Plugin._meta_init()
        self.addCleanup(Plugin.unregister)

        validator(*args, **kwargs)(Plugin)

        fn = Plugin._meta_get("validators")[0][1][0]

        def wrap_validator(config, admin_clients, clients):
            return (fn(config, admin_clients, clients, *args, **kwargs) or
                    common_validation.ValidationResult(True))
        return wrap_validator

    @mock.patch(MODULE + "os.access")
    def test__file_access_ok(self, mock_access):
        mock_access.return_value = True
        result = validation._file_access_ok(
            "foobar", os.R_OK, "p", False)
        self.assertTrue(result.is_valid, result.msg)

    @mock.patch(MODULE + "os.access")
    def test__file_access_not_found(self, mock_access):
        mock_access.return_value = False
        result = validation._file_access_ok(
            "foobar", os.R_OK, "p", False)
        self.assertFalse(result.is_valid, result.msg)

    @ddt.data({"raises_message": "Command must be a dictionary"},
              {"command": "foo",
               "raises_message": "Command must be a dictionary"},
              {"command": {"interpreter": "foobar", "script_file": "foo",
                           "script_inline": "bar"},
               "raises_message": "Exactly one of "},
              {"command": {"script_file": "foobar"},
               "raises_message": "Supplied dict specifies no"},
              {"command": {"script_inline": "foobar",
                           "interpreter": "foo",
                           "local_path": "bar"},
               "raises_message": "When uploading an interpreter its path"},
              {"command": {"interpreter": "/bin/bash",
                           "script_path": "foo"},
               "raises_message": ("Unexpected command parameters: "
                                  "script_path")},
              {"command": {"script_inline": "foobar",
                           "interpreter": ["ENV=bar", "/bin/foo"],
                           "local_path": "bar",
                           "remote_path": "/bin/foo"}},
              {"command": {"script_inline": "foobar", "interpreter": "foo"}})
    @ddt.unpack
    def test_check_command_dict(self, command=None, raises_message=None):
        if raises_message:
            e = self.assertRaises(
                ValueError, validation.check_command_dict, command)
            self.assertIn(raises_message, str(e))
        else:
            self.assertIsNone(validation.check_command_dict(command))

    @mock.patch("rally.task.validation._file_access_ok")
    def test_valid_command(self, mock__file_access_ok):
        validator = self._unwrap_validator(validation.valid_command,
                                           param_name="p")

        mock__file_access_ok.return_value = validation.ValidationResult(True)
        command = {"script_file": "foobar", "interpreter": "foo"}
        result = validator({"args": {"p": command}}, None, None)
        self.assertTrue(result.is_valid, result.msg)
        mock__file_access_ok.assert_called_once_with(
            filename="foobar", mode=os.R_OK, param_name="p.script_file",
            required=True)

    def test_valid_command_not_required(self):
        validator = self._unwrap_validator(validation.valid_command,
                                           param_name="p", required=False)
        result = validator({"args": {"p": None}}, None, None)
        self.assertTrue(result.is_valid)

    def test_valid_command_required(self):
        validator = self._unwrap_validator(validation.valid_command,
                                           param_name="p")

        result = validator({"args": {"p": None}}, None, None)
        self.assertFalse(result.is_valid, result.msg)

    @mock.patch("rally.task.validation._file_access_ok")
    def test_valid_command_unreadable_script_file(self, mock__file_access_ok):
        mock__file_access_ok.return_value = validation.ValidationResult(False)

        validator = self._unwrap_validator(validation.valid_command,
                                           param_name="p")

        command = {"script_file": "foobar", "interpreter": "foo"}
        result = validator({"args": {"p": command}}, None, None)
        self.assertFalse(result.is_valid, result.msg)

    @mock.patch("rally.task.validation.check_command_dict")
    def test_valid_command_fail_check_command_dict(self,
                                                   mock_check_command_dict):
        validator = self._unwrap_validator(validation.valid_command,
                                           param_name="p")

        mock_check_command_dict.side_effect = ValueError("foobar")
        command = {"foo": "bar"}
        result = validator({"args": {"p": command}}, None, None)
        self.assertFalse(result.is_valid, result.msg)
        self.assertEqual("foobar", result.msg)

    def test_valid_command_script_inline(self):
        validator = self._unwrap_validator(validation.valid_command,
                                           param_name="p")

        command = {"script_inline": "bar", "interpreter": "/bin/sh"}
        result = validator({"args": {"p": command}}, None, None)
        self.assertTrue(result.is_valid, result.msg)

    @mock.patch("rally.task.validation._file_access_ok")
    def test_valid_command_local_path(self, mock__file_access_ok):
        mock__file_access_ok.return_value = validation.ValidationResult(False)

        validator = self._unwrap_validator(validation.valid_command,
                                           param_name="p")

        command = {"remote_path": "bar", "local_path": "foobar"}
        result = validator({"args": {"p": command}}, None, None)
        self.assertFalse(result.is_valid, result.msg)
        mock__file_access_ok.assert_called_once_with(
            filename="foobar", mode=os.R_OK, param_name="p.local_path",
            required=True)

    def test__get_validated_flavor_no_value_in_config(self):
        result = validation._get_validated_flavor({}, None, "non_existing")
        self.assertFalse(result[0].is_valid, result[0].msg)

    @mock.patch(MODULE + "openstack_types.Flavor.transform",
                return_value="flavor_id")
    def test__get_validated_flavor(
            self, mock_flavor_transform):
        clients = mock.MagicMock()
        clients.nova().flavors.get.return_value = "flavor"

        result = validation._get_validated_flavor({"args": {"a": "test"}},
                                                  clients, "a")
        self.assertTrue(result[0].is_valid, result[0].msg)
        self.assertEqual("flavor", result[1])
        mock_flavor_transform.assert_called_once_with(
            clients=clients, resource_config="test")
        clients.nova().flavors.get.assert_called_once_with(flavor="flavor_id")

    @mock.patch(MODULE + "openstack_types.Flavor.transform",
                side_effect=exceptions.InvalidScenarioArgument)
    def test__get_validated_flavor_transform_error(
            self, mock_flavor_transform):
        result = validation._get_validated_flavor({"args": {"a": "test"}},
                                                  None, "a")
        self.assertFalse(result[0].is_valid, result[0].msg)

    @mock.patch(MODULE + "openstack_types.Flavor.transform")
    def test__get_validated_flavor_not_found(
            self, mock_flavor_transform):
        clients = mock.MagicMock()
        clients.nova().flavors.get.side_effect = nova_exc.NotFound("")
        result = validation._get_validated_flavor({"args": {"a": "test"}},
                                                  clients, "a")
        self.assertFalse(result[0].is_valid, result[0].msg)

    @mock.patch(MODULE + "openstack_types.Flavor.transform")
    def test__get_validated_flavor_from_context(
            self, mock_flavor_transform):
        clients = mock.MagicMock()
        clients.nova().flavors.get.side_effect = nova_exc.NotFound("")
        config = {
            "args": {"flavor": {"name": "test"}},
            "context": {
                "flavors": [{
                    "name": "test",
                    "ram": 32,
                }]
            }
        }
        result = validation._get_validated_flavor(config, clients, "flavor")
        self.assertTrue(result[0].is_valid, result[0].msg)

    @mock.patch(MODULE + "openstack_types.Flavor.transform")
    def test__get_validated_flavor_from_context_failed(
            self, mock_flavor_transform):
        clients = mock.MagicMock()
        clients.nova().flavors.get.side_effect = nova_exc.NotFound("")
        config = {
            "args": {"flavor": {"name": "test"}},
            "context": {
                "flavors": [{
                    "name": "othername",
                    "ram": 32,
                }]
            }
        }
        result = validation._get_validated_flavor(config, clients, "flavor")
        self.assertFalse(result[0].is_valid, result[0].msg)

        config = {
            "args": {"flavor": {"name": "test"}},
        }
        result = validation._get_validated_flavor(config, clients, "flavor")
        self.assertFalse(result[0].is_valid, result[0].msg)

    @ddt.data("nfS", "Cifs", "GLUSTERFS", "hdfs", "cephfs")
    def test_validate_share_proto_valid(self, share_proto):
        validator = self._unwrap_validator(validation.validate_share_proto)
        result = validator(
            {"args": {"share_proto": share_proto}}, "clients", "deployment")
        self.assertTrue(result.is_valid, result.msg)

    @ddt.data(
        *([{"args": {"share_proto": v}} for v in (
           None, "", "nfsfoo", "foonfs", "nfscifs", )] +
          [{}, {"args": {}}])
    )
    def test_validate_share_proto_invalid(self, config):
        validator = self._unwrap_validator(validation.validate_share_proto)
        result = validator(config, "clients", "deployment")
        self.assertFalse(result.is_valid, result.msg)

    def test_flavor_exists(self):
        validator = self._unwrap_validator(validation.flavor_exists, "param")
        result = validator({}, "clients", "deployment")
        self.assertFalse(result.is_valid, result.msg)

    @mock.patch(
        "rally.common.yamlutils.safe_load",
        return_value={
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
    )
    @mock.patch(MODULE + "os.access")
    @mock.patch(MODULE + "open")
    def test_workbook_contains_workflow(self, mock_open, mock_access,
                                        mock_safe_load):

        validator = self._unwrap_validator(
            validation.workbook_contains_workflow, "definition",
            "workflow_name")
        clients = mock.MagicMock()

        context = {
            "args": {
                "definition": "fake_path1",
                "workflow_name": "wf1"
            }
        }

        result = validator(context, clients, None)
        self.assertTrue(result.is_valid)

        self.assertEqual(1, mock_open.called)
        self.assertEqual(1, mock_access.called)
        self.assertEqual(1, mock_safe_load.called)
