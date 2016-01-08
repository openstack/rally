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

import ddt
import jsonschema
import mock

from rally.plugins.openstack.context.glance import images
from tests.unit import test

CTX = "rally.plugins.openstack.context.glance"
SCN = "rally.plugins.openstack.scenarios.glance"


@ddt.ddt
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

    @ddt.data(
        {},
        {"min_disk": 1, "min_ram": 2},
        {"image_name": "foo"},
        {"tenants": 3, "users_per_tenant": 2, "images_per_tenant": 5},
        {"image_args": {"min_disk": 1, "min_ram": 2, "visibility": "public"}})
    @ddt.unpack
    @mock.patch("%s.utils.GlanceScenario._create_image" % SCN)
    def test_setup(self, mock_glance_scenario__create_image,
                   image_container="bare", image_type="qcow2",
                   image_url="http://example.com/fake/url",
                   tenants=1, users_per_tenant=1, images_per_tenant=1,
                   image_name=None, min_ram=None, min_disk=None,
                   image_args=None):
        tenant_data = self._gen_tenants(tenants)
        users = []
        for tenant_id in tenant_data:
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": tenant_id,
                              "credential": mock.MagicMock()})

        self.context.update({
            "config": {
                "users": {
                    "tenants": tenants,
                    "users_per_tenant": users_per_tenant,
                    "concurrent": 10,
                },
                "images": {
                    "image_url": image_url,
                    "image_type": image_type,
                    "image_container": image_container,
                    "images_per_tenant": images_per_tenant,
                }
            },
            "admin": {
                "credential": mock.MagicMock()
            },
            "users": users,
            "tenants": tenant_data
        })

        expected_image_args = {}
        if image_args is not None:
            self.context["config"]["images"]["image_args"] = image_args
            expected_image_args.update(image_args)
        if image_name is not None:
            self.context["config"]["images"]["image_name"] = image_name
        if min_ram is not None:
            self.context["config"]["images"]["min_ram"] = min_ram
            expected_image_args["min_ram"] = min_ram
        if min_disk is not None:
            self.context["config"]["images"]["min_disk"] = min_disk
            expected_image_args["min_disk"] = min_disk

        new_context = copy.deepcopy(self.context)
        for tenant_id in new_context["tenants"].keys():
            new_context["tenants"][tenant_id]["images"] = [
                mock_glance_scenario__create_image.return_value.id
            ] * images_per_tenant

        images_ctx = images.ImageGenerator(self.context)
        images_ctx.setup()
        self.assertEqual(new_context, self.context)
        mock_glance_scenario__create_image.assert_has_calls(
            [mock.call(image_container, image_url, image_type,
                       name=mock.ANY,
                       **expected_image_args)] * tenants * images_per_tenant)
        if image_name:
            for args in mock_glance_scenario__create_image.call_args_list:
                self.assertTrue(args[1]["name"].startswith(image_name))

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
                              "credential": "credential"})
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
                "credential": mock.MagicMock()
            },
            "users": users,
            "tenants": tenants
        })

        images_ctx = images.ImageGenerator(self.context)
        images_ctx.cleanup()
        mock_cleanup.assert_called_once_with(names=["glance.images"],
                                             users=self.context["users"])
