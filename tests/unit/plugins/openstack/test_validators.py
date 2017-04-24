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

import ddt
import mock

from glanceclient import exc as glance_exc
from rally import exceptions
from rally.plugins.openstack import validators
from tests.unit import test


credentials = {
    "openstack": {
        "admin": mock.Mock(),
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

        clients = credentials["openstack"]["users"][0].clients.return_value

        clients.glance().images.get = mock.Mock()
        if ex:
            clients.glance().images.get.side_effect = ex

        result = validator.validate(config, credentials, None, None)

        if err_msg:
            print(result)
            self.assertEqual(err_msg, result.msg)
        elif result:
            self.assertIsNone(result, "Unexpected result '%s'" % result.msg)

    def test_validator_image_from_context(self):
        validator = validators.ImageExistsValidator("image", True)
        config = {"args": {
            "image": {"regex": r"^foo$"}}, "context": {
            "images": {
                "image_name": "foo"}}}

        result = validator.validate(config, credentials, None, None)
        self.assertIsNone(result)

    @mock.patch("rally.plugins.openstack.validators"
                ".openstack_types.GlanceImage.transform",
                return_value="image_id")
    def test_validator_image_not_in_context(self, mock_glance_image_transform):
        validator = validators.ImageExistsValidator("image", True)
        config = {"args": {
            "image": "fake_image"}, "context": {
            "images": {
                "fake_image_name": "foo"}}}

        clients = credentials[
            "openstack"]["users"][0].get.return_value.clients.return_value
        clients.glance().images.get = mock.Mock()

        result = validator.validate(config, credentials, None, None)
        self.assertIsNone(result)

        mock_glance_image_transform.assert_called_once_with(
            clients=clients, resource_config=config["args"]["image"])
        clients.glance().images.get.assert_called_with("image_id")

        exs = [exceptions.InvalidScenarioArgument(),
               glance_exc.HTTPNotFound()]
        for ex in exs:
            clients.glance().images.get.side_effect = ex

            result = validator.validate(config, credentials, None, None)

            self.assertEqual("Image 'fake_image' not found", result.msg)


@ddt.ddt
class ExternalNetworkExistsValidatorTestCase(test.TestCase):

    def setUp(self):
        super(ExternalNetworkExistsValidatorTestCase, self).setUp()
        self.validator = validators.ExternalNetworkExistsValidator("net")
        self.config = config
        self.credentials = credentials

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
        self.config = config

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
