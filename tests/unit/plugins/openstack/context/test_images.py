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

from rally.plugins.openstack.context import images
from tests.unit import fakes
from tests.unit import test

CTX = "rally.plugins.openstack.context"
SCN = "rally.plugins.openstack.scenarios"


class ImageGeneratorTestCase(test.TestCase):

    def _gen_tenants(self, count):
        tenants = {}
        for id_ in range(count):
            tenants[str(id_)] = dict(name=str(id_))
        return tenants

    @mock.patch("%s.images.context.Context.__init__" % CTX)
    def test_init(self, mock_context___init__):
        context = {}
        context["task"] = mock.MagicMock()
        context["config"] = {
            "images": {
                "image_url": "mock_url",
                "image_type": "qcow2",
                "image_container": "bare",
                "images_per_tenant": 4,
                "image_name": "some_name",
                "min_ram": 128,
                "min_disk": 1,
            }
        }

        images.ImageGenerator(context)
        mock_context___init__.assert_called_once_with(context)

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
    def test_setup(self, mock_osclients, mock_glance_scenario__create_image):

        tenants_count = 2
        users_per_tenant = 5
        images_per_tenant = 5

        fc = fakes.FakeClients()
        mock_osclients.Clients.return_value = fc

        tenants = self._gen_tenants(tenants_count)
        users = []
        for id in tenants:
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": id,
                              "endpoint": "endpoint"})

        real_context = {
            "config": {
                "users": {
                    "tenants": tenants_count,
                    "users_per_tenant": users_per_tenant,
                    "concurrent": 10,
                },
                "images": {
                    "image_url": "mock_url",
                    "image_type": "qcow2",
                    "image_container": "bare",
                    "images_per_tenant": images_per_tenant,
                    "image_name": "some_name",
                    "min_ram": 128,
                    "min_disk": 1,
                }
            },
            "admin": {
                "endpoint": mock.MagicMock()
            },
            "task": mock.MagicMock(),
            "users": users,
            "tenants": tenants
        }

        new_context = copy.deepcopy(real_context)
        for id in new_context["tenants"].keys():
            new_context["tenants"][id].setdefault("images", list())
            for j in range(images_per_tenant):
                new_context["tenants"][id]["images"].append("uuid")

        images_ctx = images.ImageGenerator(real_context)
        images_ctx.setup()
        self.assertEqual(new_context, real_context)

    @mock.patch("%s.images.osclients" % CTX)
    @mock.patch("%s.images.resource_manager.cleanup" % CTX)
    def test_cleanup(self, mock_cleanup, mock_osclients):

        tenants_count = 2
        users_per_tenant = 5
        images_per_tenant = 5

        tenants = self._gen_tenants(tenants_count)
        users = []
        for id_ in tenants:
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": id_,
                              "endpoint": "endpoint"})
            tenants[id_].setdefault("images", list())
            for j in range(images_per_tenant):
                tenants[id_]["images"].append("uuid")

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
                    "image_name": "some_name",
                    "min_ram": 128,
                    "min_disk": 1,
                }
            },
            "admin": {
                "endpoint": mock.MagicMock()
            },
            "task": mock.MagicMock(),
            "users": users,
            "tenants": tenants
        }

        images_ctx = images.ImageGenerator(context)
        images_ctx.cleanup()
        mock_cleanup.assert_called_once_with(names=["glance.images"],
                                             users=context["users"])
