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

import mock

from rally.plugins.openstack.context.vm import custom_image
from rally.task import context
from tests.unit import test


BASE = "rally.plugins.openstack.context.vm.custom_image"


@context.configure(name="test_custom_image", order=500)
class FakeImageGenerator(custom_image.BaseCustomImageGenerator):
    def _customize_image(self, *args):
        pass


class BaseCustomImageContextVMTestCase(test.TestCase):

    def setUp(self):
        super(BaseCustomImageContextVMTestCase, self).setUp()

        self.context = test.get_test_context()
        self.context.update({
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
                "credential": mock.Mock(),
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
        })

    @mock.patch("%s.osclients.Clients" % BASE)
    @mock.patch("%s.types.GlanceImage" % BASE)
    @mock.patch("%s.types.Flavor" % BASE)
    @mock.patch("%s.vmtasks.BootRuncommandDelete" % BASE)
    def test_create_one_image(
            self, mock_boot_runcommand_delete, mock_flavor,
            mock_glance_image, mock_clients):
        mock_flavor.return_value.pre_process.return_value = "flavor"
        mock_glance_image.return_value.pre_process.return_value = "image"
        ip = {"ip": "foo_ip", "id": "foo_id", "is_floating": True}
        fake_server = mock.Mock()

        fake_image = {"id": "image"}

        scenario = mock_boot_runcommand_delete.return_value = mock.MagicMock(
            _create_image=mock.MagicMock(return_value=fake_image),
            _boot_server_with_fip=mock.MagicMock(
                return_value=(fake_server, ip))
        )
        generator_ctx = FakeImageGenerator(self.context)
        generator_ctx._customize_image = mock.MagicMock()

        user = {
            "credential": "credential",
            "keypair": {"name": "keypair_name"},
            "secgroup": {"name": "secgroup_name"}
        }

        custom_image = generator_ctx.create_one_image(user,
                                                      foo_arg="foo_value")
        self.assertEqual({"id": "image"}, custom_image)

        mock_flavor.assert_called_once_with(self.context)
        mock_flavor.return_value.pre_process.assert_called_once_with(
            resource_spec={"name": "flavor"}, config={})
        mock_glance_image.assert_called_once_with(self.context)
        mock_glance_image.return_value.pre_process.assert_called_once_with(
            resource_spec={"name": "image"}, config={})
        mock_boot_runcommand_delete.assert_called_once_with(
            self.context, clients=mock_clients.return_value)

        scenario._boot_server_with_fip.assert_called_once_with(
            image="image", flavor="flavor",
            floating_network="floating",
            key_name="keypair_name", security_groups=["secgroup_name"],
            userdata=None, foo_arg="foo_value")

        scenario._stop_server.assert_called_once_with(fake_server)

        generator_ctx._customize_image.assert_called_once_with(
            fake_server, ip, user)

        scenario._create_image.assert_called_once_with(fake_server)

        scenario._delete_server_with_fip.assert_called_once_with(
            fake_server, ip)

    @mock.patch("%s.image.Image" % BASE)
    def test_delete_one_image(self, mock_image):
        generator_ctx = FakeImageGenerator(self.context)

        credential = mock.Mock()
        user = {"credential": credential,
                "keypair": {"name": "keypair_name"}}
        custom_image = mock.Mock(id="image")

        generator_ctx.delete_one_image(user, custom_image)

        mock_image.return_value.delete_image.assert_called_once_with("image")

    @mock.patch("%s.image.Image" % BASE)
    def test_setup_admin(self, mock_image):
        self.context["tenants"]["tenant_id0"]["networks"] = [
            {"id": "network_id"}]

        generator_ctx = FakeImageGenerator(self.context)

        image = mock.Mock(id="custom_image")

        generator_ctx.create_one_image = mock.Mock(return_value=image)

        generator_ctx.setup()

        mock_image.return_value.set_visibility.assert_called_once_with(
            image.id)

        generator_ctx.create_one_image.assert_called_once_with(
            self.context["users"][0], nics=[{"net-id": "network_id"}])

    def test_cleanup_admin(self):
        tenant = self.context["tenants"]["tenant_id0"]
        custom_image = tenant["custom_image"] = {"id": "image"}

        generator_ctx = FakeImageGenerator(self.context)

        generator_ctx.delete_one_image = mock.Mock()

        generator_ctx.cleanup()

        generator_ctx.delete_one_image.assert_called_once_with(
            self.context["users"][0], custom_image)

    def test_setup(self):
        self.context.pop("admin")

        generator_ctx = FakeImageGenerator(self.context)

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

        generator_ctx = FakeImageGenerator(self.context)
        generator_ctx.delete_one_image = mock.Mock()

        generator_ctx.cleanup()

        self.assertEqual(
            [mock.call(self.context["users"][i],
                       {"id": "custom_image%d" % i}) for i in range(3)],
            generator_ctx.delete_one_image.mock_calls)
