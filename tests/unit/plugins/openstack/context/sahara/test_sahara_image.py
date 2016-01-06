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

import mock

from rally import exceptions
from rally.plugins.openstack.context.sahara import sahara_image
from tests.unit import test


BASE_CTX = "rally.task.context"
CTX = "rally.plugins.openstack.context.sahara.sahara_image"
BASE_SCN = "rally.task.scenarios"
SCN = "rally.plugins.openstack.scenarios"


class SaharaImageTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(SaharaImageTestCase, self).setUp()
        self.tenants_num = 2
        self.users_per_tenant = 2
        self.users = self.tenants_num * self.users_per_tenant
        self.task = mock.MagicMock()

        self.tenants = {}
        self.users_key = []

        for i in range(self.tenants_num):
            self.tenants[str(i)] = {"id": str(i), "name": str(i),
                                    "sahara": {"image": "42"}}
            for j in range(self.users_per_tenant):
                self.users_key.append({"id": "%s_%s" % (str(i), str(j)),
                                       "tenant_id": str(i),
                                       "credential": mock.MagicMock()})

    @property
    def url_image_context(self):
        self.context.update({
            "config": {
                "users": {
                    "tenants": self.tenants_num,
                    "users_per_tenant": self.users_per_tenant,
                },
                "sahara_image": {
                    "image_url": "http://somewhere",
                    "plugin_name": "test_plugin",
                    "hadoop_version": "test_version",
                    "username": "test_user"
                }
            },
            "admin": {"credential": mock.MagicMock()},
            "users": self.users_key,
            "tenants": self.tenants
        })
        return self.context

    @property
    def existing_image_context(self):
        self.context.update({
            "config": {
                "users": {
                    "tenants": self.tenants_num,
                    "users_per_tenant": self.users_per_tenant,
                },
                "sahara_image": {
                    "image_uuid": "some_id"
                }
            },
            "admin": {"credential": mock.MagicMock()},
            "users": self.users_key,
            "tenants": self.tenants,
        })
        return self.context

    @mock.patch("%s.glance.utils.GlanceScenario._create_image" % SCN,
                return_value=mock.MagicMock(id=42))
    @mock.patch("%s.resource_manager.cleanup" % CTX)
    def test_setup_and_cleanup_url_image(self, mock_cleanup,
                                         mock_glance_scenario__create_image):

        ctx = self.url_image_context
        sahara_ctx = sahara_image.SaharaImage(ctx)
        sahara_ctx.generate_random_name = mock.Mock()

        glance_calls = []

        for i in range(self.tenants_num):
            glance_calls.append(
                mock.call(container_format="bare",
                          image_location="http://somewhere",
                          disk_format="qcow2",
                          name=sahara_ctx.generate_random_name.return_value))

        sahara_update_image_calls = []
        sahara_update_tags_calls = []

        for i in range(self.tenants_num):
            sahara_update_image_calls.append(mock.call(image_id=42,
                                                       user_name="test_user",
                                                       desc=""))
            sahara_update_tags_calls.append(mock.call(
                image_id=42,
                new_tags=["test_plugin", "test_version"]))

        sahara_ctx.setup()
        mock_glance_scenario__create_image.assert_has_calls(glance_calls)
        self.clients("sahara").images.update_image.assert_has_calls(
            sahara_update_image_calls)
        self.clients("sahara").images.update_tags.assert_has_calls(
            sahara_update_tags_calls)

        sahara_ctx.cleanup()
        mock_cleanup.assert_called_once_with(names=["glance.images"],
                                             users=ctx["users"])

    @mock.patch("%s.glance.utils.GlanceScenario._create_image" % SCN,
                return_value=mock.MagicMock(id=42))
    @mock.patch("%s.resource_manager.cleanup" % CTX)
    @mock.patch("%s.osclients.Clients" % CTX)
    def test_setup_and_cleanup_existing_image(
            self, mock_clients, mock_cleanup,
            mock_glance_scenario__create_image):

        mock_clients.glance.images.get.return_value = mock.MagicMock(
            is_public=True)

        ctx = self.existing_image_context
        sahara_ctx = sahara_image.SaharaImage(ctx)

        sahara_ctx.setup()
        for tenant_id in sahara_ctx.context["tenants"]:
            image_id = (
                sahara_ctx.context["tenants"][tenant_id]["sahara"]["image"])
            self.assertEqual("some_id", image_id)

        self.assertFalse(mock_glance_scenario__create_image.called)

        sahara_ctx.cleanup()
        self.assertFalse(mock_cleanup.called)

    @mock.patch("%s.osclients.Glance.create_client" % CTX)
    def test_check_existing_image(self, mock_glance_create_client):

        ctx = self.existing_image_context
        sahara_ctx = sahara_image.SaharaImage(ctx)
        sahara_ctx.setup()

        mock_glance_create_client.images.get.asser_called_once_with("some_id")

    @mock.patch("%s.osclients.Glance.create_client" % CTX)
    def test_check_existing_private_image_fail(self,
                                               mock_glance_create_client):

        mock_glance_create_client.return_value.images.get.return_value = (
            mock.MagicMock(is_public=False))

        ctx = self.existing_image_context
        sahara_ctx = sahara_image.SaharaImage(ctx)
        self.assertRaises(exceptions.BenchmarkSetupFailure,
                          sahara_ctx.setup)

        mock_glance_create_client.images.get.asser_called_once_with("some_id")
