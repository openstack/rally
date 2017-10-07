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
import mock

from rally.plugins.openstack.context.glance import images
from tests.unit import test

CTX = "rally.plugins.openstack.context.glance.images"
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

    @ddt.data(
        {},
        {"min_disk": 1, "min_ram": 2},
        {"image_name": "foo"},
        {"tenants": 3, "users_per_tenant": 2, "images_per_tenant": 5},
        {"api_versions": {"glance": {"version": 2, "service_type": "image"}}})
    @ddt.unpack
    @mock.patch("rally.plugins.openstack.osclients.Clients")
    def test_setup(self, mock_clients,
                   container_format="bare", disk_format="qcow2",
                   image_url="http://example.com/fake/url",
                   tenants=1, users_per_tenant=1, images_per_tenant=1,
                   image_name=None, min_ram=None, min_disk=None,
                   api_versions=None, visibility="public"):
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
                    "disk_format": disk_format,
                    "container_format": container_format,
                    "images_per_tenant": images_per_tenant,
                    "visibility": visibility,
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

    @mock.patch("%s.image.Image" % CTX)
    @mock.patch("%s.LOG" % CTX)
    def test_setup_with_deprecated_args(self, mock_log, mock_image):
        image_type = "itype"
        image_container = "icontainer"
        is_public = True
        d_min_ram = mock.Mock()
        d_min_disk = mock.Mock()
        self.context.update({
            "config": {
                "images": {"image_type": image_type,
                           "image_container": image_container,
                           "image_args": {"is_public": is_public,
                                          "min_ram": d_min_ram,
                                          "min_disk": d_min_disk}}
            },
            "users": [{"tenant_id": "foo-tenant",
                       "credential": mock.MagicMock()}],
            "tenants": {"foo-tenant": {}}
        })
        images_ctx = images.ImageGenerator(self.context)
        images_ctx.setup()

        mock_image.return_value.create_image.assert_called_once_with(
            image_name=None,
            container_format=image_container,
            image_location=None,
            disk_format=image_type,
            visibility="public",
            min_disk=d_min_disk,
            min_ram=d_min_ram
        )
        expected_warns = [
            mock.call("The 'image_type' argument is deprecated since "
                      "Rally 0.10.0, use disk_format argument instead"),
            mock.call("The 'image_container' argument is deprecated since "
                      "Rally 0.10.0; use container_format argument instead"),
            mock.call("The 'image_args' argument is deprecated since "
                      "Rally 0.10.0; specify arguments in a root "
                      "section of context instead")]

        self.assertEqual(expected_warns, mock_log.warning.call_args_list)

        mock_image.return_value.create_image.reset_mock()
        mock_log.warning.reset_mock()

        min_ram = mock.Mock()
        min_disk = mock.Mock()
        visibility = "foo"
        disk_format = "dformat"
        container_format = "cformat"

        self.context["config"]["images"].update({
            "min_ram": min_ram,
            "min_disk": min_disk,
            "visibility": visibility,
            "disk_format": disk_format,
            "container_format": container_format
        })

        images_ctx = images.ImageGenerator(self.context)
        images_ctx.setup()

        # check that deprecated arguments are not used
        mock_image.return_value.create_image.assert_called_once_with(
            image_name=None,
            container_format=container_format,
            image_location=None,
            disk_format=disk_format,
            visibility=visibility,
            min_disk=min_disk,
            min_ram=min_ram
        )
        # No matter will be deprecated arguments used or not, if they are
        # specified, warning message should be printed.
        self.assertEqual(expected_warns, mock_log.warning.call_args_list)

    @ddt.data(
        {"admin": True},
        {"api_versions": {"glance": {"version": 2, "service_type": "image"}}})
    @ddt.unpack
    @mock.patch("%s.resource_manager.cleanup" % CTX)
    def test_cleanup(self, mock_cleanup, admin=None, api_versions=None):
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
                "images": {},
                "api_versions": api_versions
            },
            "users": mock.Mock()
        })

        if admin:
            self.context["admin"] = {"credential": mock.MagicMock()}
        else:
            # ensure that there is no admin
            self.context.pop("admin")

        images_ctx = images.ImageGenerator(self.context)
        images_ctx.cleanup()
        mock_cleanup.assert_called_once_with(
            names=["glance.images", "cinder.image_volumes_cache"],
            admin=self.context.get("admin"),
            admin_required=None if admin else False,
            users=self.context["users"],
            api_versions=api_versions,
            superclass=images_ctx.__class__,
            task_id=self.context["owner_id"])

    @mock.patch("%s.rutils.make_name_matcher" % CTX)
    @mock.patch("%s.resource_manager.cleanup" % CTX)
    def test_cleanup_for_predefined_name(self, mock_cleanup,
                                         mock_make_name_matcher):
        self.context.update({
            "config": {
                "images": {"image_name": "foo"}
            },
            "users": mock.Mock()
        })

        images_ctx = images.ImageGenerator(self.context)
        images_ctx.cleanup()
        mock_cleanup.assert_called_once_with(
            names=["glance.images", "cinder.image_volumes_cache"],
            admin=self.context.get("admin"),
            admin_required=None,
            users=self.context["users"],
            api_versions=None,
            superclass=mock_make_name_matcher.return_value,
            task_id=self.context["owner_id"])
