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
        "users": [mock.Mock()],
    }
}

config = {"args": {
    "image": {
        "id": "fake_id",
        "image_name": "foo_image"
    },
    "flavor": {
        "id": "fake_flavor_id",
    },
    "foo_image": {
        "id": "fake_image_id",
    }},
    "context": {
        "images": {
            "image_name": "foo_image"
        }}}


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
