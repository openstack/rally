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

from rally.benchmark.context.sahara import sahara_image
from tests.unit import test


BASE_CTX = "rally.benchmark.context"
CTX = "rally.benchmark.context.sahara"
SCN = "rally.benchmark.scenarios"


class SaharaImageTestCase(test.TestCase):

    def setUp(self):
        super(SaharaImageTestCase, self).setUp()
        self.tenants_num = 2
        self.users_per_tenant = 2
        self.users = self.tenants_num * self.users_per_tenant
        self.task = mock.MagicMock()

        self.tenants = {}
        self.users_key = []

        for i in range(self.tenants_num):
            self.tenants[str(i)] = {"id": str(i), "name": str(i)}
            for j in range(self.users_per_tenant):
                self.users_key.append({"id": "%s_%s" % (str(i), str(j)),
                                       "tenant_id": str(i),
                                       "endpoint": "endpoint"})

    @property
    def context_without_images_key(self):
        return {
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
            "admin": {"endpoint": mock.MagicMock()},
            "task": mock.MagicMock(),
            "users": self.users_key,
            "tenants": self.tenants
        }

    @mock.patch("%s.base.Scenario._generate_random_name" % SCN,
                return_value="sahara_image_42")
    @mock.patch("%s.glance.utils.GlanceScenario._create_image" % SCN,
                return_value=mock.MagicMock(id=42))
    @mock.patch("%s.sahara_image.osclients" % CTX)
    @mock.patch("%s.sahara_image.resource_manager.cleanup" % CTX)
    def test_setup_and_cleanup(self, mock_cleanup, mock_osclients,
                               mock_image_generator, mock_uuid):

        ctx = self.context_without_images_key
        sahara_ctx = sahara_image.SaharaImage(ctx)

        glance_calls = []

        for i in range(self.tenants_num):
            glance_calls.append(mock.call("sahara_image_42",
                                          "bare",
                                          "http://somewhere",
                                          "qcow2"))

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
        mock_image_generator.assert_has_calls(glance_calls)
        mock_osclients.Clients(
            mock.MagicMock()).sahara().images.update_image.assert_has_calls(
            sahara_update_image_calls)
        mock_osclients.Clients(
            mock.MagicMock()).sahara().images.update_tags.assert_has_calls(
            sahara_update_tags_calls)

        sahara_ctx.cleanup()
        mock_cleanup.assert_called_once_with(names=["glance.images"],
                                             users=ctx["users"])
