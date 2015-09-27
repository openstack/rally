# Copyright 2015: Mirantis Inc.
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

"""Tests for the Benchmark VM image context."""

import mock

from rally.plugins.openstack.context.vm import custom_image
from rally.task import context
from tests.unit import test


BASE = "rally.plugins.openstack.context.vm.custom_image"


@context.configure(name="test_custom_image", order=500)
class TestImageGenerator(custom_image.BaseCustomImageGenerator):
    def _customize_image(self, *args):
        pass


class BaseCustomImageContextVMTestCase(test.TestCase):

    def setUp(self):
        super(BaseCustomImageContextVMTestCase, self).setUp()

        self.context = {
            "task": mock.MagicMock(),
            "config": {
                "test_custom_image": {
                    "image": {"name": "image"},
                    "flavor": {"name": "flavor"},
                    "username": "fedora",
                    "floating_network": "floating",
                    "port": 1022,
                }
            },
            "admin": {
                "endpoint": "endpoint",
            },
            "users": [
                {"tenant_id": "tenant_id0"},
                {"tenant_id": "tenant_id1"},
                {"tenant_id": "tenant_id2"}
            ],
            "tenants": {
                "tenant_id0": {},
                "tenant_id1": {},
                "tenant_id2": {}
            }
        }

    @mock.patch("%s.vmtasks.VMTasks" % BASE)
    @mock.patch("%s.osclients.Clients" % BASE)
    @mock.patch("%s.types.ImageResourceType.transform" % BASE,
                return_value="image")
    @mock.patch("%s.types.FlavorResourceType.transform" % BASE,
                return_value="flavor")
    def test_create_one_image(
            self, mock_flavor_resource_type_transform,
            mock_image_resource_type_transform, mock_clients, mock_vm_tasks):
        ip = {"ip": "foo_ip", "id": "foo_id", "is_floating": True}
        fake_server = mock.Mock()

        fake_image = mock.MagicMock(
            to_dict=mock.MagicMock(return_value={"id": "image"}))

        mock_vm_scenario = mock_vm_tasks.return_value = mock.MagicMock(
            _create_image=mock.MagicMock(return_value=fake_image),
            _boot_server_with_fip=mock.MagicMock(
                return_value=(fake_server, ip)),
            _generate_random_name=mock.MagicMock(return_value="foo_name"),
        )

        generator_ctx = TestImageGenerator(self.context)
        generator_ctx._customize_image = mock.MagicMock()

        user = {
            "endpoint": "endpoint",
            "keypair": {"name": "keypair_name"},
            "secgroup": {"name": "secgroup_name"}
        }

        custom_image = generator_ctx.create_one_image(user,
                                                      foo_arg="foo_value")

        mock_flavor_resource_type_transform.assert_called_once_with(
            clients=mock_clients.return_value,
            resource_config={"name": "flavor"})
        mock_image_resource_type_transform.assert_called_once_with(
            clients=mock_clients.return_value,
            resource_config={"name": "image"})
        mock_vm_tasks.assert_called_once_with(
            self.context, clients=mock_clients.return_value)

        mock_vm_scenario._boot_server_with_fip.assert_called_once_with(
            image="image", flavor="flavor",
            name="foo_name", floating_network="floating",
            key_name="keypair_name", security_groups=["secgroup_name"],
            userdata=None, foo_arg="foo_value")

        mock_vm_scenario._stop_server.assert_called_once_with(fake_server)

        generator_ctx._customize_image.assert_called_once_with(
            fake_server, ip, user)

        mock_vm_scenario._create_image.assert_called_once_with(fake_server)

        mock_vm_scenario._delete_server_with_fip.assert_called_once_with(
            fake_server, ip)

        self.assertEqual({"id": "image"}, custom_image)

    @mock.patch("%s.vmtasks.VMTasks" % BASE)
    @mock.patch("%s.osclients.Clients" % BASE)
    @mock.patch("%s.types.ImageResourceType.transform" % BASE,
                return_value="image")
    @mock.patch("%s.types.FlavorResourceType.transform" % BASE,
                return_value="flavor")
    def test_create_one_image_cleanup(
            self, mock_flavor_resource_type_transform,
            mock_image_resource_type_transform, mock_clients, mock_vm_tasks):
        ip = {"ip": "foo_ip", "id": "foo_id", "is_floating": True}
        fake_server = mock.Mock()

        fake_image = mock.MagicMock(
            to_dict=mock.MagicMock(return_value={"id": "image"}))

        mock_vm_scenario = mock_vm_tasks.return_value = mock.MagicMock(
            _create_image=mock.MagicMock(return_value=fake_image),
            _boot_server_with_fip=mock.MagicMock(
                return_value=(fake_server, ip)),
            _generate_random_name=mock.MagicMock(return_value="foo_name"),
        )

        generator_ctx = TestImageGenerator(self.context)
        generator_ctx._customize_image = mock.MagicMock(
            side_effect=ValueError())

        user = {
            "endpoint": "endpoint",
            "keypair": {"name": "keypair_name"},
            "secgroup": {"name": "secgroup_name"}
        }

        self.assertRaises(
            ValueError,
            generator_ctx.create_one_image, user, foo_arg="foo_value")

        generator_ctx._customize_image.assert_called_once_with(
            fake_server, ip, user)

        mock_vm_scenario._delete_server_with_fip.assert_called_once_with(
            fake_server, ip)

    @mock.patch("%s.osclients.Clients" % BASE)
    def test_make_image_public(self, mock_clients):
        fc = mock.MagicMock()
        mock_clients.return_value = fc

        generator_ctx = TestImageGenerator(self.context)
        custom_image = {"id": "image"}

        generator_ctx.make_image_public(custom_image=custom_image)

        mock_clients.assert_called_once_with(
            self.context["admin"]["endpoint"])

        fc.glance.assert_called_once_with()
        fc.glance.return_value.images.get.assert_called_once_with("image")
        (fc.glance.return_value.images.get.
            return_value.update.assert_called_once_with(is_public=True))

    @mock.patch("%s.nova_utils.NovaScenario" % BASE)
    @mock.patch("%s.osclients.Clients" % BASE)
    def test_delete_one_image(self, mock_clients, mock_nova_scenario):
        nova_scenario = mock_nova_scenario.return_value = mock.MagicMock()
        nova_client = nova_scenario.clients.return_value
        nova_client.images.get.return_value = "image_obj"

        generator_ctx = TestImageGenerator(self.context)

        user = {"endpoint": "endpoint", "keypair": {"name": "keypair_name"}}
        custom_image = {"id": "image"}

        generator_ctx.delete_one_image(user, custom_image)

        mock_nova_scenario.assert_called_once_with(
            context=self.context, clients=mock_clients.return_value)

        nova_scenario.clients.assert_called_once_with("nova")
        nova_client.images.get.assert_called_once_with("image")
        nova_scenario._delete_image.assert_called_once_with("image_obj")

    def test_setup_admin(self):
        self.context["tenants"]["tenant_id0"]["networks"] = [
            {"id": "network_id"}]

        generator_ctx = TestImageGenerator(self.context)

        generator_ctx.create_one_image = mock.Mock(
            return_value="custom_image")
        generator_ctx.make_image_public = mock.Mock()

        generator_ctx.setup()

        generator_ctx.create_one_image.assert_called_once_with(
            self.context["users"][0], nics=[{"net-id": "network_id"}])
        generator_ctx.make_image_public.assert_called_once_with(
            "custom_image")

    def test_cleanup_admin(self):
        tenant = self.context["tenants"]["tenant_id0"]
        custom_image = tenant["custom_image"] = {"id": "image"}

        generator_ctx = TestImageGenerator(self.context)

        generator_ctx.delete_one_image = mock.Mock()

        generator_ctx.cleanup()

        generator_ctx.delete_one_image.assert_called_once_with(
            self.context["users"][0], custom_image)

    def test_setup(self):
        self.context.pop("admin")

        generator_ctx = TestImageGenerator(self.context)

        generator_ctx.create_one_image = mock.Mock(
            side_effect=["custom_image0", "custom_image1", "custom_image2"])

        generator_ctx.setup()

        self.assertEqual(
            [mock.call(user) for user in self.context["users"]],
            generator_ctx.create_one_image.mock_calls)

        for i in range(3):
            self.assertEqual(
                "custom_image%d" % i,
                self.context["tenants"]["tenant_id%d" % i]["custom_image"]
            )

    def test_cleanup(self):
        self.context.pop("admin")

        for i in range(3):
            self.context["tenants"]["tenant_id%d" % i]["custom_image"] = {
                "id": "custom_image%d" % i}

        generator_ctx = TestImageGenerator(self.context)
        generator_ctx.delete_one_image = mock.Mock()

        generator_ctx.cleanup()

        self.assertEqual(
            [mock.call(self.context["users"][i],
                       {"id": "custom_image%d" % i}) for i in range(3)],
            generator_ctx.delete_one_image.mock_calls)
