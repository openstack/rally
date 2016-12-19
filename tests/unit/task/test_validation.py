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
from glanceclient import exc as glance_exc
import mock
from novaclient import exceptions as nova_exc
import six

from rally.common.plugin import plugin
from rally import consts
from rally import exceptions
import rally.osclients
from rally.task import validation
from tests.unit import test


MODULE = "rally.task.validation."


class ValidationUtilsTestCase(test.TestCase):

    def test_validator(self):

        @plugin.from_func()
        def scenario():
            pass

        scenario._meta_init()

        def validator_func(config, clients, deployment, a, b, c, d):
            return (config, clients, deployment, a, b, c, d)

        validator = validation.validator(validator_func)

        self.assertEqual(scenario, validator("a", "b", "c", d=1)(scenario))
        self.assertEqual(1, len(scenario._meta_get("validators")))

        self.assertEqual(
            ("conf", "client", "deploy", "a", "b", "c", 1),
            scenario._meta_get("validators")[0]("conf", "client", "deploy"))


@ddt.ddt
class ValidatorsTestCase(test.TestCase):

    def _unwrap_validator(self, validator, *args, **kwargs):

        @plugin.from_func()
        def func():
            pass

        func._meta_init()
        validator(*args, **kwargs)(func)

        return func._meta_get("validators")[0]

    def test_number_not_nullable(self):
        validator = self._unwrap_validator(validation.number, param_name="n")
        self.assertFalse(validator({}, None, None).is_valid)

    def test_number_nullable(self):
        validator = self._unwrap_validator(validation.number, param_name="n",
                                           nullable=True)
        self.assertTrue(validator({}, None, None).is_valid)

    def test_number_min_max_value(self):
        validator = self._unwrap_validator(validation.number,
                                           param_name="a", minval=4, maxval=10)
        result = validator({"args": {"a": 3.9}}, None, None)
        self.assertFalse(result.is_valid, result.msg)
        result = validator({"args": {"a": 4.1}}, None, None)
        self.assertTrue(result.is_valid, result.msg)
        result = validator({"args": {"a": 11}}, None, None)
        self.assertFalse(result.is_valid, result.msg)

    def test_number_integer_only(self):
        validator = self._unwrap_validator(validation.number,
                                           param_name="b", integer_only=True)
        result = validator({"args": {"b": 3.9}}, None, None)
        self.assertFalse(result.is_valid, result.msg)
        result = validator({"args": {"b": 3}}, None, None)
        self.assertTrue(result.is_valid, result.msg)

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

    @mock.patch(MODULE + "_file_access_ok")
    def test_file_exists(self, mock__file_access_ok):
        mock__file_access_ok.return_value = "foobar"
        validator = self._unwrap_validator(validation.file_exists,
                                           param_name="p",
                                           required=False)
        result = validator({"args": {"p": "test_file"}}, None, None)
        self.assertEqual("foobar", result)
        mock__file_access_ok.assert_called_once_with(
            "test_file", os.R_OK, "p", False)

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

    def test__get_validated_image_no_value_in_config(self):
        result = validation._get_validated_image({}, None, "non_existing")
        self.assertFalse(result[0].is_valid, result[0].msg)

    def test__get_validated_image_from_context(self):
        clients = mock.MagicMock()
        image = {
            "size": 0,
            "min_ram": 0,
            "min_disk": 0
        }
        result = validation._get_validated_image({"args": {
            "image": {"name": "foo"}}, "context": {
            "images": {
                "image_name": "foo"}
        }}, clients, "image")

        self.assertTrue(result[0].is_valid, result[0].msg)
        self.assertEqual(result[1], image)

        result = validation._get_validated_image({"args": {
            "image": {"regex": r"^foo$"}}, "context": {
            "images": {
                "image_name": "foo"}
        }}, clients, "image")

        self.assertTrue(result[0].is_valid, result[0].msg)
        self.assertEqual(result[1], image)

    @mock.patch(MODULE + "openstack_types.GlanceImage.transform",
                return_value="image_id")
    def test__get_validated_image(self, mock_glance_image_transform):
        clients = mock.MagicMock()
        clients.glance().images.get().to_dict.return_value = {
            "image": "image_id"}

        result = validation._get_validated_image({"args": {"a": "test"},
                                                  "context": {
                                                      "image_name": "foo"}},
                                                 clients, "a")
        self.assertTrue(result[0].is_valid, result[0].msg)
        self.assertEqual({"image": "image_id", "min_disk": 0,
                          "min_ram": 0, "size": 0},
                         result[1])
        mock_glance_image_transform.assert_called_once_with(
            clients=clients, resource_config="test")
        clients.glance().images.get.assert_called_with(image="image_id")

    @mock.patch(MODULE + "openstack_types.GlanceImage.transform",
                side_effect=exceptions.InvalidScenarioArgument)
    def test__get_validated_image_transform_error(
            self, mock_glance_image_transform):
        result = validation._get_validated_image({"args": {"a": "test"}},
                                                 None, "a")
        self.assertFalse(result[0].is_valid, result[0].msg)

    @mock.patch(MODULE + "openstack_types.GlanceImage.transform")
    def test__get_validated_image_not_found(
            self, mock_glance_image_transform):
        clients = mock.MagicMock()
        clients.glance().images.get().to_dict.side_effect = (
            glance_exc.HTTPNotFound(""))
        result = validation._get_validated_image({"args": {"a": "test"}},
                                                 clients, "a")
        self.assertFalse(result[0].is_valid, result[0].msg)

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
        self.assertEqual(result[1], "flavor")
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

    @ddt.data("nfS", "Cifs", "GLUSTERFS", "hdfs")
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

    def test_image_exists(self):
        validator = self._unwrap_validator(validation.image_exists, "param")
        result = validator({}, "clients", "deployment")
        self.assertFalse(result.is_valid, result.msg)

    def test_image_exists_nullable(self):
        validator = self._unwrap_validator(validation.image_exists,
                                           "param", nullable=True)
        result = validator({}, "clients", "deployment")
        self.assertTrue(result.is_valid, result.msg)

    def test_flavor_exists(self):
        validator = self._unwrap_validator(validation.flavor_exists, "param")
        result = validator({}, "clients", "deployment")
        self.assertFalse(result.is_valid, result.msg)

    def test_image_valid_on_flavor_flavor_or_image_not_specified(self):
        validator = self._unwrap_validator(validation.image_valid_on_flavor,
                                           "flavor", "image")
        result = validator({}, None, None)
        self.assertFalse(result.is_valid, result.msg)

        result = validator({"args": {"flavor": {"id": 11}}}, mock.MagicMock(),
                           None)
        self.assertFalse(result.is_valid, result.msg)

    @mock.patch(MODULE + "_get_validated_image")
    @mock.patch(MODULE + "_get_validated_flavor")
    def test_image_valid_on_flavor(self, mock__get_validated_flavor,
                                   mock__get_validated_image):
        image = {
            "id": "fake_id",
            "min_ram": None,
            "size": 2,
            "min_disk": 0
        }
        flavor = mock.MagicMock()
        success = validation.ValidationResult(True)
        mock__get_validated_flavor.return_value = (success, flavor)
        mock__get_validated_image.return_value = (success, image)

        # test flavor.disk None
        validator = self._unwrap_validator(validation.image_valid_on_flavor,
                                           "flavor", "image")
        flavor.disk = None
        flavor.ram = 2
        image["min_ram"] = 4
        result = validator(None, None, None)
        self.assertFalse(result.is_valid, result.msg)
        image["min_ram"] = 1
        result = validator(None, None, None)
        self.assertTrue(result.is_valid, result.msg)

        # test validate_disk false
        validator = self._unwrap_validator(validation.image_valid_on_flavor,
                                           "flavor", "image", False)
        flavor.disk = 1
        flavor.ram = 2
        image["min_ram"] = 4
        result = validator(None, None, None)
        self.assertFalse(result.is_valid, result.msg)
        image["min_ram"] = 1
        result = validator(None, None, None)
        self.assertTrue(result.is_valid, result.msg)

        # test validate_disk true and flavor.disk not None
        validator = self._unwrap_validator(validation.image_valid_on_flavor,
                                           "flavor", "image")
        image["size"] = 2
        image["min_disk"] = 0
        flavor.disk = 5.0 / (1024 ** 3)
        result = validator(None, None, None)
        self.assertTrue(result.is_valid, result.msg)
        image["min_disk"] = flavor.disk * 2
        result = validator(None, None, None)
        self.assertFalse(result.is_valid, result.msg)
        image["min_disk"] = flavor.disk / 4
        image["size"] = 1000
        result = validator(None, None, None)
        self.assertFalse(result.is_valid, result.msg)

    @mock.patch(MODULE + "openstack_types.Flavor.transform")
    @mock.patch(MODULE + "_get_validated_image")
    def test_image_valid_on_flavor_context(
            self, mock__get_validated_image,
            mock_flavor_transform):
        clients = mock.MagicMock()
        clients.nova().flavors.get.side_effect = nova_exc.NotFound("")

        image = {"min_ram": 24, "id": "fake_id"}
        success = validation.ValidationResult(True)
        mock__get_validated_image.return_value = (success, image)

        validator = self._unwrap_validator(validation.image_valid_on_flavor,
                                           "flavor", "image")
        config = {
            "args": {"flavor": {"name": "test"}},
            "context": {
                "flavors": [{
                    "name": "test",
                    "ram": 32,
                }]
            }
        }

        # test ram
        image["min_ram"] = 64
        result = validator(config, clients, None)
        self.assertFalse(result.is_valid, result.msg)

    def test_network_exists(self):
        validator = self._unwrap_validator(validation.network_exists, "net")

        net1 = mock.MagicMock()
        net1.label = "private"
        net2 = mock.MagicMock()
        net2.label = "custom"
        clients = mock.MagicMock()
        clients.nova().networks.list.return_value = [net1, net2]

        result = validator({}, clients, None)
        self.assertTrue(result.is_valid, result.msg)
        result = validator({"args": {"net": "custom"}}, clients, None)
        self.assertTrue(result.is_valid, result.msg)
        result = validator({"args": {"net": "custom2"}}, clients, None)
        self.assertFalse(result.is_valid, result.msg)

    def test_external_network_exists(self):
        validator = self._unwrap_validator(
            validation.external_network_exists, "name")
        result = validator({"args": {}}, None, None)
        self.assertTrue(result.is_valid, result.msg)

        clients = mock.MagicMock()
        net1 = mock.MagicMock()
        net2 = mock.MagicMock()
        clients.nova().floating_ip_pools.list.return_value = [net1, net2]

        net1.name = "public"
        net2.name = "custom"
        result = validator({}, clients, None)
        self.assertTrue(result.is_valid, result.msg)

        result = validator({"args": {"name": "custom"}}, clients, None)
        self.assertTrue(result.is_valid, result.msg)
        result = validator({"args": {"name": "non_exist"}}, clients, None)
        self.assertFalse(result.is_valid, result.msg)

        net1.name = {"name": "public"}
        net2.name = {"name": "custom"}
        result = validator({"args": {"name": "custom"}}, clients, None)
        self.assertTrue(result.is_valid, result.msg)

    def test_required_parameters(self):
        validator = self._unwrap_validator(validation.required_parameters,
                                           "a", "b")
        result = validator({"args": {"a": 1, "b": 2, "c": 3}}, None, None)
        self.assertTrue(result.is_valid, result.msg)

        result = validator({"args": {"a": 1, "c": 3}}, None, None)
        self.assertFalse(result.is_valid, result.msg)

    @mock.patch("rally.common.objects.Credential")
    def test_required_service(self, mock_credential):
        validator = self._unwrap_validator(validation.required_services,
                                           consts.Service.KEYSTONE,
                                           consts.Service.NOVA,
                                           consts.Service.NOVA_NET)
        clients = mock.MagicMock()
        clients.services().values.return_value = [consts.Service.KEYSTONE,
                                                  consts.Service.NOVA,
                                                  consts.Service.NOVA_NET]

        fake_service = mock.Mock(binary="nova-network", status="enabled")

        with mock.patch("rally.osclients.Clients") as clients_cls:
            nova_client = clients_cls.return_value.nova.return_value
            nova_client.services.list.return_value = [fake_service]
            result = validator({}, clients, {"admin": {"info": "admin"}})
            clients_cls.assert_called_once_with(mock_credential.return_value)
            mock_credential.assert_called_once_with(info="admin")
        self.assertTrue(result.is_valid, result.msg)

        validator = self._unwrap_validator(validation.required_services,
                                           consts.Service.KEYSTONE,
                                           consts.Service.NOVA)
        clients.services().values.return_value = [consts.Service.KEYSTONE]
        with mock.patch("rally.osclients.Clients") as clients_cls:
            result = validator({}, clients, None)
            self.assertFalse(clients_cls.called)
        self.assertFalse(result.is_valid, result.msg)

    def test_required_service_wrong_service(self):
        validator = self._unwrap_validator(validation.required_services,
                                           consts.Service.KEYSTONE,
                                           consts.Service.NOVA, "lol")
        clients = mock.MagicMock()
        result = validator({}, clients, None)
        self.assertFalse(result.is_valid, result.msg)

    def test_required_contexts(self):
        validator = self._unwrap_validator(validation.required_contexts,
                                           "c1", "c2", "c3")
        result = validator({"context": {"a": 1}}, None, None)
        self.assertFalse(result.is_valid, result.msg)

        result = validator({"context": {"c1": 1, "c2": 2, "c3": 3}},
                           None, None)
        self.assertTrue(result.is_valid, result.msg)

        result = validator({"context": {"c1": 1, "c2": 2, "c3": 3, "a": 1}},
                           None, None)
        self.assertTrue(result.is_valid, result.msg)

    def test_required_openstack_with_admin(self):
        validator = self._unwrap_validator(validation.required_openstack,
                                           admin=True)

        # admin presented in deployment
        fake_deployment = {"admin": "admin_credential", "users": []}
        self.assertTrue(validator(None, None, fake_deployment).is_valid)

        # admin not presented in deployment
        fake_deployment = {"admin": None, "users": ["u1", "h2"]}
        self.assertFalse(validator(None, None, fake_deployment).is_valid)

    def test_required_openstack_with_users(self):
        validator = self._unwrap_validator(validation.required_openstack,
                                           users=True)

        # users presented in deployment
        fake_deployment = {"admin": None, "users": ["u_credential"]}
        self.assertTrue(validator({}, None, fake_deployment).is_valid)

        # admin and users presented in deployment
        fake_deployment = {"admin": "a", "users": ["u1", "h2"]}
        self.assertTrue(validator({}, None, fake_deployment).is_valid)

        # admin and user context
        fake_deployment = {"admin": "a", "users": []}
        context = {"context": {"users": True}}
        self.assertTrue(validator(context, None, fake_deployment).is_valid)

        # just admin presented
        fake_deployment = {"admin": "a", "users": []}
        self.assertFalse(validator({}, None, fake_deployment).is_valid)

    def test_required_openstack_with_admin_and_users(self):
        validator = self._unwrap_validator(validation.required_openstack,
                                           admin=True, users=True)

        fake_deployment = {"admin": "a", "users": []}
        self.assertFalse(validator({}, None, fake_deployment).is_valid)

        fake_deployment = {"admin": "a", "users": ["u"]}
        self.assertTrue(validator({}, None, fake_deployment).is_valid)

        # admin and user context
        fake_deployment = {"admin": "a", "users": []}
        context = {"context": {"users": True}}
        self.assertTrue(validator(context, None, fake_deployment).is_valid)

    def test_required_openstack_invalid(self):
        validator = self._unwrap_validator(validation.required_openstack)
        self.assertFalse(validator(None, None, None).is_valid)

    def test_volume_type_exists(self):
        validator = self._unwrap_validator(validation.volume_type_exists,
                                           param_name="volume_type")

        clients = mock.MagicMock()
        clients.cinder().volume_types.list.return_value = []

        context = {"args": {"volume_type": False}}

        result = validator(context, clients, mock.MagicMock())
        self.assertTrue(result.is_valid, result.msg)

    def test_volume_type_exists_check_types(self):
        validator = self._unwrap_validator(validation.volume_type_exists,
                                           param_name="volume_type")

        clients = mock.MagicMock()
        clients.cinder().volume_types.list.return_value = ["type"]

        context = {"args": {"volume_type": True}}

        result = validator(context, clients, mock.MagicMock())
        self.assertTrue(result.is_valid, result.msg)

    def test_volume_type_exists_check_types_no_types_exist(self):
        validator = self._unwrap_validator(validation.volume_type_exists,
                                           param_name="volume_type")

        clients = mock.MagicMock()
        clients.cinder().volume_types.list.return_value = []

        context = {"args": {"volume_type": True}}

        result = validator(context, clients, mock.MagicMock())
        self.assertFalse(result.is_valid, result.msg)

    @mock.patch(MODULE + "osclients")
    def test_required_clients(self, mock_osclients):
        validator = self._unwrap_validator(validation.required_clients,
                                           "keystone", "nova")
        clients = mock.MagicMock()
        clients.keystone.return_value = "keystone"
        clients.nova.return_value = "nova"
        result = validator({}, clients, {})
        self.assertTrue(result.is_valid, result.msg)
        self.assertFalse(mock_osclients.Clients.called)

        clients.nova.side_effect = ImportError
        result = validator({}, clients, {})
        self.assertFalse(result.is_valid, result.msg)

    @mock.patch(MODULE + "objects")
    @mock.patch(MODULE + "osclients")
    def test_required_clients_with_admin(self, mock_osclients, mock_objects):
        validator = self._unwrap_validator(validation.required_clients,
                                           "keystone", "nova", admin=True)
        clients = mock.Mock()
        clients.keystone.return_value = "keystone"
        clients.nova.return_value = "nova"
        mock_osclients.Clients.return_value = clients
        mock_objects.Credential.return_value = "foo_credential"
        result = validator({}, clients, {"admin": {"foo": "bar"}})
        self.assertTrue(result.is_valid, result.msg)
        mock_objects.Credential.assert_called_once_with(foo="bar")
        mock_osclients.Clients.assert_called_once_with("foo_credential")
        clients.nova.side_effect = ImportError
        result = validator({}, clients, {"admin": {"foo": "bar"}})
        self.assertFalse(result.is_valid, result.msg)

    @ddt.data(
        {"ext_validate": "existing_extension",
         "validation_result": True},
        {"ext_validate": "absent_extension",
         "validation_result": False},
    )
    @ddt.unpack
    def test_required_neutron_extensions(self, ext_validate,
                                         validation_result):
        validator = self._unwrap_validator(
            validation.required_neutron_extensions,
            ext_validate)
        clients = mock.Mock()
        clients.neutron.return_value.list_extensions.return_value = (
            {"extensions": [{"alias": "existing_extension"}]})
        result = validator({}, clients, {})
        self.assertEqual(result.is_valid, validation_result)

    def test_required_cinder_services(self):
        validator = self._unwrap_validator(
            validation.required_cinder_services,
            service_name=six.text_type("cinder-service"))

        with mock.patch.object(rally.osclients.Cinder, "create_client") as c:
            fake_service = mock.Mock(binary="cinder-service", state="up")
            cinder_client = mock.Mock()
            services = mock.Mock()
            services.list.return_value = [fake_service]
            cinder_client.services = services
            c.return_value = cinder_client

            deployment = {"admin": {"auth_url": "fake_credential",
                                    "username": "username",
                                    "password": "password"}}
            result = validator({}, None, deployment)
            self.assertTrue(result.is_valid, result.msg)

            fake_service.state = "down"
            result = validator({}, None, deployment)
            self.assertFalse(result.is_valid, result.msg)

    def test_restricted_parameters(self):
        validator = self._unwrap_validator(
            validation.restricted_parameters, ["param_name"])
        result = validator({"args": {}}, None, None)
        self.assertTrue(result.is_valid, result.msg)

    def test_restricted_parameters_negative(self):
        validator = self._unwrap_validator(
            validation.restricted_parameters, ["param_name"])
        result = validator({"args": {"param_name": "value"}}, None, None)
        self.assertFalse(result.is_valid, result.msg)

    def test_restricted_parameters_in_dict(self):
        validator = self._unwrap_validator(
            validation.restricted_parameters, ["param_name"], "subdict")
        result = validator({"args": {"subdict": {}}}, None, None)
        self.assertTrue(result.is_valid, result.msg)

    def test_restricted_parameters_in_dict_negative(self):
        validator = self._unwrap_validator(
            validation.restricted_parameters, ["param_name"], "subdict")
        result = validator({"args": {"subdict":
                           {"param_name": "value"}}}, None, None)
        self.assertFalse(result.is_valid, result.msg)

    def test_restricted_parameters_string_param_names(self):
        validator = self._unwrap_validator(
            validation.restricted_parameters, "param_name")
        result = validator({"args": {}}, None, None)
        self.assertTrue(result.is_valid, result.msg)

    @ddt.data(
        {"exception_msg": "Heat template validation failed on fake_path1. "
                          "Original error message: fake_msg."},
        {"exception_msg": None}
    )
    @ddt.unpack
    @mock.patch(MODULE + "os.path.exists", return_value=True)
    @mock.patch(MODULE + "open", side_effect=mock.mock_open(), create=True)
    def test_validate_heat_template(self, mock_open, mock_exists,
                                    exception_msg):
        validator = self._unwrap_validator(
            validation.validate_heat_template, "template_path1",
            "template_path2")
        clients = mock.MagicMock()
        mock_open().__enter__().read.side_effect = ["fake_template1",
                                                    "fake_template2"]
        heat_validator = mock.MagicMock()
        if exception_msg:
            heat_validator.side_effect = Exception("fake_msg")
        clients.heat().stacks.validate = heat_validator
        context = {"args": {"template_path1": "fake_path1",
                            "template_path2": "fake_path2"}}
        result = validator(context, clients, mock.MagicMock())

        if not exception_msg:
            heat_validator.assert_has_calls([
                mock.call(template="fake_template1"),
                mock.call(template="fake_template2")
            ])
            mock_open.assert_has_calls([
                mock.call("fake_path1", "r"),
                mock.call("fake_path2", "r")
            ], any_order=True)
            self.assertTrue(result.is_valid, result.msg)
        else:
            heat_validator.assert_called_once_with(template="fake_template1")
            self.assertEqual("Heat template validation failed on fake_path1."
                             " Original error message: fake_msg.", result.msg)
            self.assertFalse(result.is_valid)

    def _get_keystone_v2_mock_client(self):
        keystone = mock.Mock()
        del keystone.projects
        keystone.tenants = mock.Mock()
        return keystone

    def _get_keystone_v3_mock_client(self):
        keystone = mock.Mock()
        del keystone.tenants
        keystone.projects = mock.Mock()
        return keystone

    def test_required_api_versions_keystonev2(self):
        validator = self._unwrap_validator(
            validation.required_api_versions, component="keystone",
            versions=[2.0])
        clients = mock.MagicMock()
        clients.keystone.return_value = self._get_keystone_v3_mock_client()
        self.assertFalse(validator({}, clients, None).is_valid)

        clients.keystone.return_value = self._get_keystone_v2_mock_client()
        self.assertTrue(validator({}, clients, None).is_valid)

    def test_required_api_versions_keystonev3(self):
        validator = self._unwrap_validator(
            validation.required_api_versions, component="keystone",
            versions=[3])
        clients = mock.MagicMock()

        clients.keystone.return_value = self._get_keystone_v2_mock_client()
        self.assertFalse(validator({}, clients, None).is_valid)

        clients.keystone.return_value = self._get_keystone_v3_mock_client()
        self.assertTrue(validator({}, clients, None).is_valid)

    def test_required_api_versions_keystone_all_versions(self):
        validator = self._unwrap_validator(
            validation.required_api_versions, component="keystone",
            versions=[2.0, 3])
        clients = mock.MagicMock()

        clients.keystone.return_value = self._get_keystone_v3_mock_client()
        self.assertTrue(validator({}, clients, None).is_valid)

        clients.keystone.return_value = self._get_keystone_v2_mock_client()
        self.assertTrue(validator({}, clients, None).is_valid)

    @ddt.data({"nova_version": 2, "required_versions": [2], "valid": True},
              {"nova_version": 3, "required_versions": [2], "valid": False},
              {"nova_version": None, "required_versions": [2], "valid": False},
              {"nova_version": 2, "required_versions": [2, 3], "valid": True},
              {"nova_version": 4, "required_versions": [2, 3], "valid": False})
    @ddt.unpack
    def test_required_api_versions_choose_version(self, nova_version=None,
                                                  required_versions=(2,),
                                                  valid=False):
        validator = self._unwrap_validator(
            validation.required_api_versions, component="nova",
            versions=required_versions)
        clients = mock.MagicMock()
        clients.nova.choose_version.return_value = nova_version
        self.assertEqual(validator({}, clients, None).is_valid,
                         valid)

    @ddt.data({"required_version": 2, "valid": True},
              {"required_version": 3, "valid": False})
    @ddt.unpack
    def test_required_api_versions_context(self, required_version=None,
                                           valid=False):
        validator = self._unwrap_validator(
            validation.required_api_versions, component="nova",
            versions=[required_version])
        clients = mock.MagicMock()
        config = {"context": {"api_versions": {"nova": {"version": 2}}}}
        self.assertEqual(validator(config, clients, None).is_valid,
                         valid)

    @mock.patch(
        "yaml.safe_load",
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
