# Copyright 2017: Mirantis Inc.
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

import copy
import ddt
import mock

from glanceclient import exc as glance_exc
from novaclient import exceptions as nova_exc
from rally import exceptions
from rally.plugins.openstack import validators
from tests.unit import test


credentials = {
    "openstack": {
        "admin": mock.MagicMock(),
        "users": [mock.MagicMock()],
    }
}

config = dict(args={"image": {"id": "fake_id",
                              "min_ram": 10,
                              "size": 1024 ** 3,
                              "min_disk": 10.0 * (1024 ** 3),
                              "image_name": "foo_image"},
                    "flavor": {"id": "fake_flavor_id",
                               "name": "test"},
                    "foo_image": {"id": "fake_image_id"}
                    },
              context={"images": {"image_name": "foo_image"}}
              )


@ddt.ddt
class ImageExistsValidatorTestCase(test.TestCase):

    def setUp(self):
        super(ImageExistsValidatorTestCase, self).setUp()
        self.validator = validators.ImageExistsValidator("image", True)
        self.config = config
        self.credentials = credentials

    @ddt.unpack
    @ddt.data(
        {"param_name": "fake_param", "nullable": True, "err_msg": None},
        {"param_name": "fake_param", "nullable": False,
         "err_msg": "Parameter fake_param is not specified."},
        {"param_name": "image", "nullable": True, "err_msg": None},
    )
    def test_validator(self, param_name, nullable, err_msg, ex=False):
        validator = validators.ImageExistsValidator(param_name,
                                                    nullable)

        clients = self.credentials[
            "openstack"]["users"][0].clients.return_value

        clients.glance().images.get = mock.Mock()
        if ex:
            clients.glance().images.get.side_effect = ex

        result = validator.validate(self.config, self.credentials, None, None)

        if err_msg:
            print(result)
            self.assertEqual(err_msg, result.msg)
        elif result:
            self.assertIsNone(result, "Unexpected result '%s'" % result.msg)

    def test_validator_image_from_context(self):
        config = {"args": {
            "image": {"regex": r"^foo$"}}, "context": {
            "images": {
                "image_name": "foo"}}}

        result = self.validator.validate(config, self.credentials, None, None)
        self.assertIsNone(result)

    @mock.patch("rally.plugins.openstack.validators"
                ".openstack_types.GlanceImage.transform",
                return_value="image_id")
    def test_validator_image_not_in_context(self, mock_glance_image_transform):
        config = {"args": {
            "image": "fake_image"}, "context": {
            "images": {
                "fake_image_name": "foo"}}}

        clients = self.credentials[
            "openstack"]["users"][0].get.return_value.clients.return_value
        clients.glance().images.get = mock.Mock()

        result = self.validator.validate(config, self.credentials, None, None)
        self.assertIsNone(result)

        mock_glance_image_transform.assert_called_once_with(
            clients=clients, resource_config=config["args"]["image"])
        clients.glance().images.get.assert_called_with("image_id")

        exs = [exceptions.InvalidScenarioArgument(),
               glance_exc.HTTPNotFound()]
        for ex in exs:
            clients.glance().images.get.side_effect = ex

            result = self.validator.validate(config, credentials, None, None)

            self.assertEqual("Image 'fake_image' not found", result.msg)


@ddt.ddt
class ExternalNetworkExistsValidatorTestCase(test.TestCase):

    def setUp(self):
        super(ExternalNetworkExistsValidatorTestCase, self).setUp()
        self.validator = validators.ExternalNetworkExistsValidator("net")
        self.config = copy.deepcopy(config)
        self.credentials = copy.deepcopy(credentials)

    @ddt.unpack
    @ddt.data(
        {"foo_conf": {}},
        {"foo_conf": {"args": {"net": "custom"}}},
        {"foo_conf": {"args": {"net": "non_exist"}},
         "err_msg": "External (floating) network with name non_exist"
                    " not found by user {}. Available networks:"
                    " [{}, {}]"},
        {"foo_conf": {"args": {"net": "custom"}},
         "net1_name": {"name": {"net": "public"}},
         "net2_name": {"name": {"net": "custom"}},
         "err_msg": "External (floating) network with name custom"
                    " not found by user {}. Available networks:"
                    " [{}, {}]"}
    )
    def test_validator(self, foo_conf, net1_name="public", net2_name="custom",
                       err_msg=""):

        user = self.credentials["openstack"]["users"][0]

        net1 = {"name": net1_name, "router:external": True}
        net2 = {"name": net2_name, "router:external": True}

        user["credential"].clients().neutron().list_networks.return_value = {
            "networks": [net1, net2]}

        result = self.validator.validate(foo_conf, self.credentials,
                                         None, None)
        if err_msg:
            self.assertTrue(result)
            self.assertEqual(err_msg.format(user["credential"].username,
                                            net1, net2), result.msg[0])
        elif result:
            self.assertIsNone(result, "Unexpected result '%s'" % result)


@ddt.ddt
class RequiredNeutronExtensionsValidatorTestCase(test.TestCase):

    def setUp(self):
        super(RequiredNeutronExtensionsValidatorTestCase, self).setUp()
        self.config = copy.deepcopy(config)

    @ddt.unpack
    @ddt.data(
        {"ext_validate": "existing_extension"},
        {"ext_validate": "absent_extension",
         "err_msg": "Neutron extension absent_extension is not configured"}
    )
    def test_validator(self, ext_validate, err_msg=False):
        validator = validators.RequiredNeutronExtensionsValidator(
            ext_validate)
        clients = credentials["openstack"]["users"][0]["credential"].clients()

        clients.neutron().list_extensions.return_value = {
            "extensions": [{"alias": "existing_extension"}]}
        result = validator.validate({}, credentials, {}, None)

        if err_msg:
            self.assertTrue(result)
            self.assertEqual(err_msg, result.msg)
        else:
            self.assertIsNone(result)


@ddt.ddt
class ImageValidOnFlavorValidatorTestCase(test.TestCase):

    def setUp(self):
        super(ImageValidOnFlavorValidatorTestCase, self).setUp()
        self.validator = validators.ImageValidOnFlavorValidator("foo_flavor",
                                                                "image")
        self.config = config
        self.credentials = credentials

    @ddt.unpack
    @ddt.data(
        {"flavor_ram": 15, "flavor_disk": 15.0 * (1024 ** 3), "err_msg": None},
        {"flavor_ram": 5, "flavor_disk": 5.0 * (1024 ** 3),
         "err_msg": "The memory size for flavor '%s' is too small"
                    " for requested image 'fake_id'"},
        {"flavor_ram": 15, "flavor_disk": 5.0 / (1024 ** 3),
         "err_msg": "The disk size for flavor '%s' is too small"
                    " for requested image 'fake_id'"},
        {"flavor_ram": 15, "flavor_disk": 5.0 * (1024 ** 3),
         "err_msg": "The minimal disk size for flavor '%s' is too small"
                    " for requested image 'fake_id'"},
    )
    def test_validator(self, flavor_ram, flavor_disk, err_msg):
        image = config["args"]["image"]
        flavor = mock.Mock(ram=flavor_ram, disk=flavor_disk)

        success = validators.ValidationResult(True)

        user = self.credentials["openstack"]["users"][0]["credential"]
        user.clients().nova().flavors.get.return_value = "foo_flavor"

        self.validator._get_validated_image = mock.Mock()
        self.validator._get_validated_image.return_value = (success, image)

        self.validator._get_validated_flavor = mock.Mock()
        self.validator._get_validated_flavor.return_value = (success, flavor)

        result = self.validator.validate(config, self.credentials, None, None)

        if err_msg:
            self.assertEqual(err_msg % flavor.id, result.msg)
        else:
            self.assertIsNone(result, "Unexpected message")

    @mock.patch(
        "rally.plugins.openstack.validators"
        ".ImageValidOnFlavorValidator._get_validated_flavor")
    @mock.patch(
        "rally.plugins.openstack.validators"
        ".ImageValidOnFlavorValidator._get_validated_image")
    def test_validator_incorrect_result(self, mock__get_validated_image,
                                        mock__get_validated_flavor):

        validator = validators.ImageValidOnFlavorValidator(
            "foo_flavor", "image", fail_on_404_image=False)

        image = self.config["args"]["image"]
        flavor = mock.Mock(ram=15, disk=15.0 * (1024 ** 3))

        success = validators.ValidationResult(True, "Success")
        fail = validators.ValidationResult(False, "Not success")

        user = self.credentials["openstack"]["users"][0]["credential"]
        user.clients().nova().flavors.get.return_value = "foo_flavor"

        # Flavor is incorrect
        mock__get_validated_flavor.return_value = (fail, flavor)
        result = validator.validate(self.config, self.credentials, None, None)

        self.assertIsNotNone(result)
        self.assertEqual("Not success", result.msg)

        # image is incorrect
        user.clients().nova().flavors.get.return_value = "foo_flavor"
        mock__get_validated_flavor.reset_mock()
        mock__get_validated_flavor.return_value = (success, flavor)
        mock__get_validated_image.return_value = (success, None)
        result = validator.validate(self.config, self.credentials, None, None)
        self.assertIsNone(result)
        mock__get_validated_image.reset_mock()
        mock__get_validated_image.return_value = (fail, image)
        result = validator.validate(self.config, self.credentials, None, None)
        self.assertIsNotNone(result)
        self.assertEqual("Not success", result.msg)
        # 'fail_on_404_image' == True
        result = self.validator.validate(self.config, self.credentials,
                                         None, None)
        self.assertIsNotNone(result)
        self.assertEqual("Not success", result.msg)
        # 'validate_disk' = False
        validator = validators.ImageValidOnFlavorValidator(
            "foo_flavor", "image", validate_disk=False)
        mock__get_validated_image.reset_mock()
        mock__get_validated_image.return_value = (success, image)
        result = validator.validate(self.config, self.credentials, None, None)
        self.assertIsNone(result)

    def test__get_validated_flavor_wrong_value_in_config(self):

        result = self.validator._get_validated_flavor(self.config,
                                                      self.credentials,
                                                      "foo_flavor")
        self.assertEqual("Parameter foo_flavor is not specified.",
                         result[0].msg)

    @mock.patch("rally.plugins.openstack.validators"
                ".openstack_types.Flavor.transform",
                return_value="flavor_id")
    def test__get_validated_flavor(self, mock_flavor_transform):

        clients = mock.Mock()
        clients.nova().flavors.get.return_value = "flavor"

        result = self.validator._get_validated_flavor(self.config,
                                                      clients,
                                                      "flavor")
        self.assertTrue(result[0].is_valid, result[0].msg)
        self.assertEqual(result[1], "flavor")

        mock_flavor_transform.assert_called_once_with(
            clients=clients, resource_config=self.config["args"]["flavor"])
        clients.nova().flavors.get.assert_called_once_with(flavor="flavor_id")

        clients.side_effect = exceptions.InvalidScenarioArgument("")
        result = self.validator._get_validated_flavor(self.config,
                                                      clients,
                                                      "flavor")
        self.assertTrue(result[0].is_valid, result[0].msg)
        self.assertEqual(result[1], "flavor")
        mock_flavor_transform.assert_called_with(
            clients=clients, resource_config=self.config["args"]["flavor"])
        clients.nova().flavors.get.assert_called_with(flavor="flavor_id")

    @mock.patch("rally.plugins.openstack.validators"
                ".openstack_types.Flavor.transform")
    def test__get_validated_flavor_not_found(self, mock_flavor_transform):

        clients = mock.MagicMock()
        clients.nova().flavors.get.side_effect = nova_exc.NotFound("")

        result = self.validator._get_validated_flavor(self.config,
                                                      clients,
                                                      "flavor")
        self.assertFalse(result[0].is_valid, result[0].msg)
        self.assertEqual("Flavor '%s' not found" %
                         self.config["args"]["flavor"],
                         result[0].msg)
        mock_flavor_transform.assert_called_once_with(
            clients=clients, resource_config=self.config["args"]["flavor"])

    @mock.patch("rally.plugins.openstack.validators"
                ".openstack_types.GlanceImage.transform",
                return_value="image_id")
    def test__get_validated_image(self, mock_glance_image_transform):
        image = {
            "size": 0,
            "min_ram": 0,
            "min_disk": 0
        }
        # Get image name from context
        result = self.validator._get_validated_image({"args": {
            "image": {"regex": r"^foo$"}}, "context": {
            "images": {
                "image_name": "foo"}
        }}, self.credentials, "image")
        self.assertIsInstance(result[0], validators.ValidationResult)
        self.assertTrue(result[0].is_valid)
        self.assertEqual(result[0].msg, "")
        self.assertEqual(result[1], image)

        clients = mock.Mock()
        clients.glance().images.get().to_dict.return_value = {
            "image": "image_id"}
        image["image"] = "image_id"

        result = self.validator._get_validated_image(self.config,
                                                     clients,
                                                     "image")
        self.assertTrue(result[0].is_valid, result[0].msg)
        self.assertEqual(image, result[1])
        mock_glance_image_transform.assert_called_once_with(
            clients=clients, resource_config=self.config["args"]["image"])
        clients.glance().images.get.assert_called_with("image_id")

    @mock.patch("rally.plugins.openstack.validators"
                ".openstack_types.GlanceImage.transform",
                return_value="image_id")
    def test__get_validated_image_incorrect_param(self,
                                                  mock_glance_image_transform):
        # Wrong 'param_name'
        result = self.validator._get_validated_image(self.config,
                                                     self.credentials,
                                                     "fake_param")
        self.assertIsInstance(result[0], validators.ValidationResult)
        self.assertFalse(result[0].is_valid)
        self.assertEqual(result[0].msg,
                         "Parameter fake_param is not specified.")
        self.assertIsNone(result[1])

        # 'image_name' is not in 'image_context'
        image = {"id": "image_id", "size": 1024,
                 "min_ram": 256, "min_disk": 512}

        clients = mock.Mock()
        clients.glance().images.get().to_dict.return_value = image
        config = {"args": {"image": "foo_image",
                           "context": {"images": {
                               "fake_parameter_name": "foo_image"}
                           }}
                  }
        result = self.validator._get_validated_image(config,
                                                     clients,
                                                     "image")
        self.assertIsNotNone(result)
        self.assertTrue(result[0].is_valid)
        self.assertEqual(result[1], image)

        mock_glance_image_transform.assert_called_once_with(
            clients=clients, resource_config=config["args"]["image"])
        clients.glance().images.get.assert_called_with("image_id")

    @mock.patch("rally.plugins.openstack.validators"
                ".openstack_types.GlanceImage.transform",
                return_value="image_id")
    def test__get_validated_image_exceptions(self,
                                             mock_glance_image_transform):
        clients = mock.Mock()
        clients.glance().images.get.return_value = "image"
        clients.glance().images.get.side_effect = glance_exc.HTTPNotFound("")
        result = self.validator._get_validated_image(config,
                                                     clients,
                                                     "image")
        self.assertIsInstance(result[0], validators.ValidationResult)
        self.assertFalse(result[0].is_valid)
        self.assertEqual(result[0].msg,
                         "Image '%s' not found" % config["args"]["image"])
        self.assertIsNone(result[1])
        mock_glance_image_transform.assert_called_once_with(
            clients=clients, resource_config=config["args"]["image"])
        clients.glance().images.get.assert_called_with("image_id")

        clients.side_effect = exceptions.InvalidScenarioArgument("")
        result = self.validator._get_validated_image(config,
                                                     clients,
                                                     "image")
        self.assertIsInstance(result[0], validators.ValidationResult)
        self.assertFalse(result[0].is_valid)
        self.assertEqual(result[0].msg,
                         "Image '%s' not found" % config["args"]["image"])
        self.assertIsNone(result[1])
        mock_glance_image_transform.assert_called_with(
            clients=clients, resource_config=config["args"]["image"])
        clients.glance().images.get.assert_called_with("image_id")

    @mock.patch("rally.plugins.openstack.validators"
                ".types.obj_from_name")
    @mock.patch("rally.plugins.openstack.validators"
                ".flavors_ctx.FlavorConfig")
    def test__get_flavor_from_context(self, mock_flavor_config,
                                      mock_obj_from_name):
        config = {"context": {"images": {"fake_parameter_name": "foo_image"},
                              }
                  }

        self.assertRaises(exceptions.InvalidScenarioArgument,
                          self.validator._get_flavor_from_context,
                          config, "foo_flavor")

        config = {"context": {"images": {"fake_parameter_name": "foo_image"},
                              "flavors": [{"flavor1": "fake_flavor1"}]}
                  }
        result = self.validator._get_flavor_from_context(config, "foo_flavor")

        self.assertIsInstance(result[0], validators.ValidationResult)
        self.assertTrue(result[0].is_valid)
        self.assertEqual("<context flavor: %s>" % result[1].name, result[1].id)


class RequiredClientsValidatorTestCase(test.TestCase):

    def setUp(self):
        super(RequiredClientsValidatorTestCase, self).setUp()
        self.config = copy.deepcopy(config)
        self.credentials = copy.deepcopy(credentials)

    def test_validate(self):
        validator = validators.RequiredClientsValidator(components=["keystone",
                                                                    "nova"])
        clients = self.credentials[
            "openstack"]["users"][0]["credential"].clients.return_value

        result = validator.validate(self.config, self.credentials, None, None)
        self.assertIsNone(result)

        clients.nova.side_effect = ImportError
        result = validator.validate(self.config, self.credentials, None, None)
        self.assertTrue(result)
        self.assertEqual("Client for nova is not installed. To install it "
                         "run `pip install python-novaclient`", result.msg)

    def test_validate_with_admin(self):
        validator = validators.RequiredClientsValidator(components=["keystone",
                                                                    "nova"],
                                                        admin=True)
        clients = self.credentials[
            "openstack"]["admin"].clients.return_value
        result = validator.validate(self.config, self.credentials, None, None)
        self.assertIsNone(result)

        clients.keystone.side_effect = ImportError
        result = validator.validate(self.config, self.credentials, None, None)
        self.assertTrue(result)
        self.assertEqual("Client for keystone is not installed. To install it "
                         "run `pip install python-keystoneclient`", result.msg)
