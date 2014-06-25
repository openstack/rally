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
import mock

from rally.benchmark.context import images
from rally import exceptions
from tests import test

CTX = "rally.benchmark.context"
SCN = "rally.benchmark.scenarios"


class ImageGeneratorTestCase(test.TestCase):

    def setUp(self):
        super(ImageGeneratorTestCase, self).setUp()
        self.image = mock.MagicMock()
        self.image1 = mock.MagicMock()
        self.tenants_num = 2
        self.users_per_tenant = 5
        self.users = self.tenants_num * self.users_per_tenant
        self.concurrent = 10
        self.image_type = "qcow2"
        self.image_container = "bare"
        self.images_per_tenant = 5
        self.task = mock.MagicMock()
        self.image_list = ["uuid" for i in range(self.images_per_tenant)]
        self.users_key_with_image_id = [{'image_id': self.image_list,
                                         'endpoint': 'endpoint',
                                         'tenant_id': i}
                                        for i in range(self.tenants_num)]
        self.user_key = [{'id': i, 'tenant_id': j, 'endpoint': 'endpoint'}
                         for j in range(self.tenants_num)
                         for i in range(self.users_per_tenant)]

    @property
    def context_without_images_key(self):
        return {
            "config": {
                "users": {
                    "tenants": self.tenants_num,
                    "users_per_tenant": self.users_per_tenant,
                    "concurrent": self.concurrent,
                },
                "images": {
                    "image_url": "mock_url",
                    "image_type": self.image_type,
                    "image_container": self.image_container,
                    "images_per_tenant": self.images_per_tenant,
                }
            },
            "admin": {"endpoint": mock.MagicMock()},
            "task": mock.MagicMock(),
            "users": self.user_key,
        }

    @mock.patch("%s.glance.utils.GlanceScenario._create_image" % SCN)
    @mock.patch("%s.images.osclients" % CTX)
    @mock.patch("%s.cleanup.utils.delete_glance_resources" % CTX)
    def test_setup_and_cleanup(self, mock_image_remover, mock_osclients,
                               mock_image_generator):

        class FakeImage(object):
            def __init__(self):
                self.id = "uuid"
        fake_image = FakeImage()

        endpoint = mock.MagicMock()
        mock_osclients.Clients(endpoint).glance().images.get.\
            return_value = self.image1
        mock_image_generator.return_value = fake_image

        real_context = self.context_without_images_key
        new_context = copy.deepcopy(real_context)
        new_context["images"] = self.users_key_with_image_id

        images_ctx = images.ImageGenerator(real_context)
        images_ctx.setup()
        self.assertEqual(new_context, real_context)
        images_ctx.cleanup()

        self.assertEqual(self.tenants_num, len(mock_image_remover.mock_calls))

        mock_image_remover.side_effect = Exception('failed_deletion')
        self.assertRaises(exceptions.ImageCleanUpException, images_ctx.cleanup)
