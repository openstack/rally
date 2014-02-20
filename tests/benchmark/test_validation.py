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

from glanceclient import exc as glance_exc
import mock
from novaclient import exceptions as nova_exc

from rally.benchmark import validation
from rally import consts
from tests import fakes
from tests import test


class ValidationUtilsTestCase(test.TestCase):

    def test_add_validator(self):
        def test_validator():
            pass

        @validation.add_validator(test_validator,
                                  consts.EndpointPermission.ADMIN)
        def test_function():
            pass

        validators = getattr(test_function, "validators")
        self.assertEqual(len(validators), 1)
        self.assertEqual(validators[0], test_validator)
        self.assertEqual(validators[0].permission,
                         consts.EndpointPermission.ADMIN)

    def test_image_exists(self):
        fakegclient = fakes.FakeClients().get_glance_client()
        fakegclient.images.get = mock.MagicMock()
        validator = validation.image_exists("image_id")
        test_img_id = "test_image_id"
        result = validator(clients={"glance": fakegclient},
                           image_id=test_img_id)
        fakegclient.images.get.assert_called_once_with(image=test_img_id)
        self.assertTrue(result.is_valid)
        self.assertIsNone(result.msg)

    def test_image_exists_fail(self):
        fakegclient = fakes.FakeClients().get_glance_client()
        fakegclient.images.get = mock.MagicMock()
        fakegclient.images.get.side_effect = glance_exc.HTTPNotFound
        validator = validation.image_exists("image_id")
        test_img_id = "test_image_id"
        result = validator(clients={"glance": fakegclient},
                           image_id=test_img_id)
        fakegclient.images.get.assert_called_once_with(image=test_img_id)
        self.assertFalse(result.is_valid)
        self.assertIsNotNone(result.msg)

    def test_flavor_exists(self):
        fakenclient = fakes.FakeClients().get_nova_client()
        fakenclient.flavors = mock.MagicMock()
        validator = validation.flavor_exists("flavor_id")
        test_flavor_id = 1
        result = validator(clients={"nova": fakenclient},
                           flavor_id=test_flavor_id)
        fakenclient.flavors.get.assert_called_once_with(flavor=test_flavor_id)
        self.assertTrue(result.is_valid)
        self.assertIsNone(result.msg)

    def test_flavor_exists_fail(self):
        fakenclient = fakes.FakeClients().get_nova_client()
        fakenclient.flavors = mock.MagicMock()
        fakenclient.flavors.get.side_effect = nova_exc.NotFound(code=404)
        validator = validation.flavor_exists("flavor_id")
        test_flavor_id = 101
        result = validator(clients={"nova": fakenclient},
                           flavor_id=test_flavor_id)
        fakenclient.flavors.get.assert_called_once_with(flavor=test_flavor_id)
        self.assertFalse(result.is_valid)
        self.assertIsNotNone(result.msg)
