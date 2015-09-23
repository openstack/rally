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

from rally.plugins.openstack.context.glance import images
from tests.unit import fakes
from tests.unit import test

CTX = "rally.plugins.openstack.context.glance"
SCN = "rally.plugins.openstack.scenarios.glance"


class ImageGeneratorTestCase(test.ScenarioTestCase):

    def _gen_tenants(self, count):
        tenants = {}
        for id_ in range(count):
            tenants[str(id_)] = {"name": str(id_)}
        return tenants

    def test_init_validation(self):
        self.context["config"] = {
            "images": {
                "image_url": "mock_url"
            }
        }

        self.assertRaises(jsonschema.ValidationError,
                          images.ImageGenerator.validate, self.context)

    @mock.patch("%s.utils.GlanceScenario._create_image" % SCN,
                return_value=fakes.FakeImage(id="uuid"))
    def test_setup(self, mock_glance_scenario__create_image):

        tenants_count = 2
        users_per_tenant = 5
        images_per_tenant = 5

        tenants = self._gen_tenants(tenants_count)
        users = []
        for id_ in tenants:
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": id_,
                              "endpoint": mock.MagicMock()})

        self.context.update({
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
            "users": users,
            "tenants": tenants
        })

        new_context = copy.deepcopy(self.context)
        for id_ in new_context["tenants"].keys():
            new_context["tenants"][id_].setdefault("images", [])
            for j in range(images_per_tenant):
                new_context["tenants"][id_]["images"].append("uuid")

        images_ctx = images.ImageGenerator(self.context)
        images_ctx.setup()
        self.assertEqual(new_context, self.context)

    @mock.patch("%s.images.resource_manager.cleanup" % CTX)
    def test_cleanup(self, mock_cleanup):

        tenants_count = 2
        users_per_tenant = 5
        images_per_tenant = 5

        tenants = self._gen_tenants(tenants_count)
        users = []
        for id_ in tenants:
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": id_,
                              "endpoint": "endpoint"})
            tenants[id_].setdefault("images", [])
            for j in range(images_per_tenant):
                tenants[id_]["images"].append("uuid")

        self.context.update({
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
            "users": users,
            "tenants": tenants
        })

        images_ctx = images.ImageGenerator(self.context)
        images_ctx.cleanup()
        mock_cleanup.assert_called_once_with(names=["glance.images"],
                                             users=self.context["users"])
