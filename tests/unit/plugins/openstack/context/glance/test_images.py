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

    tenants_num = 1
    users_per_tenant = 5
    users_num = tenants_num * users_per_tenant
    threads = 10

    def setUp(self):
        super(ImageGeneratorTestCase, self).setUp()
        self.context.update({
            "config": {
                "users": {
                    "tenants": self.tenants_num,
                    "users_per_tenant": self.users_per_tenant,
                    "resource_management_workers": self.threads,
                }
            },
            "admin": {"credential": mock.MagicMock()},
            "users": [],
            "task": {"uuid": "task_id"}
        })
        patch = mock.patch(
            "rally.plugins.openstack.services.image.image.Image")
        self.addCleanup(patch.stop)
        self.mock_image = patch.start()

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
        {"api_versions": {"glance": {"version": 2, "service_type": "image"}}})
    @ddt.unpack
    @mock.patch("rally.osclients.Clients")
    def test_setup(self, mock_clients,
                   container_format="bare", disk_format="qcow2",
                   image_url="http://example.com/fake/url",
                   tenants=1, users_per_tenant=1, images_per_tenant=1,
                   image_name=None, min_ram=None, min_disk=None,
                   image_args={"is_public": True}, api_versions=None,
                   visibility="public"):
        image_service = self.mock_image.return_value

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
                    "image_type": disk_format,
                    "disk_format": disk_format,
                    "image_container": container_format,
                    "container_format": container_format,
                    "images_per_tenant": images_per_tenant,
                    "is_public": visibility,
                    "visibility": visibility,
                    "image_args": image_args
                }
            },
            "admin": {
                "credential": mock.MagicMock()
            },
            "users": users,
            "tenants": tenant_data
        })
        if api_versions:
            self.context["config"]["api_versions"] = api_versions

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
                image_service.create_image.return_value.id
            ] * images_per_tenant

        images_ctx = images.ImageGenerator(self.context)
        images_ctx.setup()
        self.assertEqual(new_context, self.context)

        wrapper_calls = []
        wrapper_calls.extend([mock.call(mock_clients.return_value.glance,
                                        images_ctx)] * tenants)
        wrapper_calls.extend(
            [mock.call().create_image(
                container_format, image_url, disk_format,
                name=mock.ANY, **expected_image_args)] *
            tenants * images_per_tenant)

        mock_clients.assert_has_calls(
            [mock.call(mock.ANY, api_info=api_versions)] * tenants)

    @ddt.data(
        {},
        {"api_versions": {"glance": {"version": 2, "service_type": "image"}}})
    @ddt.unpack
    def test_cleanup(self, api_versions=None):
        image_service = self.mock_image.return_value

        images_per_tenant = 5

        tenants = self._gen_tenants(self.tenants_num)
        users = []
        created_images = []
        for tenant_id in tenants:
            for i in range(self.users_per_tenant):
                users.append({"id": i, "tenant_id": tenant_id,
                              "credential": mock.MagicMock()})
            tenants[tenant_id].setdefault("images", [])
            for j in range(images_per_tenant):
                image = mock.Mock()
                created_images.append(image)
                tenants[tenant_id]["images"].append(image)

        self.context.update({
            "config": {
                "users": {
                    "tenants": self.tenants_num,
                    "users_per_tenant": self.users_per_tenant,
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
                "credential": mock.MagicMock()
            },
            "users": users,
            "tenants": tenants
        })
        if api_versions:
            self.context["config"]["api_versions"] = api_versions

        images_ctx = images.ImageGenerator(self.context)
        images_ctx.cleanup()
        image_service.delete_image.assert_has_calls([])
