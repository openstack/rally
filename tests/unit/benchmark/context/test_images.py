# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import copy

import jsonschema
import mock

from rally.benchmark.context import images
from rally import exceptions
from tests.unit import fakes
from tests.unit import test

CTX = "rally.benchmark.context"
SCN = "rally.benchmark.scenarios"


class ImageGeneratorTestCase(test.TestCase):

    def test_init(self):
        context = {}
        context["task"] = mock.MagicMock()
        context["config"] = {
            "images": {
                "image_url": "mock_url",
                "image_type": "qcow2",
                "image_container": "bare",
                "images_per_tenant": 4,
            }
        }

        new_context = copy.deepcopy(context)
        new_context["images"] = []
        images.ImageGenerator(context)
        self.assertEqual(new_context, context)

    def test_init_validation(self):
        context = {}
        context["task"] = mock.MagicMock()
        context["config"] = {
            "images": {
                "image_url": "mock_url"
            }
        }

        self.assertRaises(jsonschema.ValidationError,
                          images.ImageGenerator.validate, context)

    @mock.patch("%s.glance.utils.GlanceScenario._create_image" % SCN,
                return_value=fakes.FakeImage(id="uuid"))
    @mock.patch("%s.images.osclients" % CTX)
    def test_setup(self, mock_osclients, mock_image_create):

        fc = fakes.FakeClients()
        mock_osclients.Clients.return_value = fc

        image_list = ["uuid"] * 5
        image_key = [{'image_id': image_list, 'endpoint': 'endpoint',
                      'tenant_id': i} for i in range(2)]
        user_key = [{'id': i, 'tenant_id': j, 'endpoint': 'endpoint'}
                    for j in range(2)
                    for i in range(5)]

        real_context = {
            "config": {
                "users": {
                    "tenants": 2,
                    "users_per_tenant": 5,
                    "concurrent": 10,
                },
                "images": {
                    "image_url": "mock_url",
                    "image_type": "qcow2",
                    "image_container": "bare",
                    "images_per_tenant": 5,
                }
            },
            "admin": {
                "endpoint": mock.MagicMock()
            },
            "task": mock.MagicMock(),
            "users": user_key,
        }

        new_context = copy.deepcopy(real_context)
        new_context["images"] = image_key

        images_ctx = images.ImageGenerator(real_context)
        images_ctx.setup()
        self.assertEqual(new_context, real_context)

    @mock.patch("%s.images.osclients" % CTX)
    @mock.patch("%s.cleanup.utils.delete_glance_resources" % CTX)
    def test_cleanup(self, mock_image_remover, mock_osclients):
        image_list = ["uuid"] * 5
        image_key = [{'image_id': image_list, 'endpoint': 'endpoint',
                      'tenant_id': i} for i in range(2)]
        user_key = [{'id': i, 'tenant_id': j, 'endpoint': 'endpoint'}
                    for j in range(2)
                    for i in range(5)]

        context = {
            "config": {
                "users": {
                    "tenants": 2,
                    "users_per_tenant": 5,
                    "concurrent": 10,
                },
                "images": {
                    "image_url": "mock_url",
                    "image_type": "qcow2",
                    "image_container": "bare",
                    "images_per_tenant": 5,
                }
            },
            "admin": {
                "endpoint": mock.MagicMock()
            },
            "task": mock.MagicMock(),
            "users": user_key,
            "images": image_key,
        }

        images_ctx = images.ImageGenerator(context)
        images_ctx.cleanup()

        self.assertEqual(2, len(mock_image_remover.mock_calls))

        mock_image_remover.side_effect = Exception('failed_deletion')
        self.assertRaises(exceptions.ImageCleanUpException, images_ctx.cleanup)

    def test_validate_semantic(self):
        users = [fakes.FakeClients()]
        images.ImageGenerator.validate_semantic(None, None, users, None)

    @mock.patch("%s.images.osclients.Clients.glance" % CTX)
    def test_validate_semantic_unavailabe(self, mock_glance):
        mock_glance.side_effect = Exception("list error")
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          images.ImageGenerator.validate_semantic, None, None,
                          None, None)
