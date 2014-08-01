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

from rally.benchmark.context import sahara_image
from rally import exceptions
from tests import test

CTX = "rally.benchmark.context"
SCN = "rally.benchmark.scenarios"


class SaharaImageTestCase(test.TestCase):

    def setUp(self):
        super(SaharaImageTestCase, self).setUp()
        self.tenants_num = 2
        self.users_per_tenant = 2
        self.users = self.tenants_num * self.users_per_tenant
        self.task = mock.MagicMock()

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
            "users": self.user_key,
        }

    @mock.patch("%s.base.Scenario._generate_random_name" % SCN,
                return_value="sahara_image_42")
    @mock.patch("%s.glance.utils.GlanceScenario._create_image" % SCN,
                return_value=mock.MagicMock(id=42))
    @mock.patch("%s.sahara_image.osclients" % CTX)
    @mock.patch("%s.cleanup.utils.delete_glance_resources" % CTX)
    def test_setup_and_cleanup(self, mock_image_remover, mock_osclients,
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
        self.assertEqual(self.tenants_num, len(mock_image_remover.mock_calls))

        mock_image_remover.side_effect = Exception('failed_deletion')
        self.assertRaises(exceptions.ImageCleanUpException, sahara_ctx.cleanup)
