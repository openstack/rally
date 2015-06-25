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

import tempfile

import mock
from oslotest import mockpatch

from rally.plugins.openstack.scenarios.glance import utils
from tests.unit import test

BM_UTILS = "rally.task.utils"
GLANCE_UTILS = "rally.plugins.openstack.scenarios.glance.utils"


class GlanceScenarioTestCase(test.ClientsTestCase):

    def setUp(self):
        super(GlanceScenarioTestCase, self).setUp()
        self.image = mock.Mock()
        self.image1 = mock.Mock()
        self.res_is = mockpatch.Patch(BM_UTILS + ".resource_is")
        self.get_fm = mockpatch.Patch(BM_UTILS + ".get_from_manager")
        self.wait_for = mockpatch.Patch(GLANCE_UTILS + ".utils.wait_for")
        self.wait_for_delete = mockpatch.Patch(
            GLANCE_UTILS + ".utils.wait_for_delete")
        self.useFixture(self.wait_for)
        self.useFixture(self.wait_for_delete)
        self.useFixture(self.res_is)
        self.useFixture(self.get_fm)
        self.gfm = self.get_fm.mock
        self.useFixture(mockpatch.Patch("time.sleep"))
        self.scenario = utils.GlanceScenario()

    def test_list_images(self):
        scenario = utils.GlanceScenario()
        return_images_list = scenario._list_images()
        self.clients("glance").images.list.assert_called_once_with()
        self.assertEqual(list(self.clients("glance").images.list.return_value),
                         return_images_list)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "glance.list_images")

    def test_create_image(self):
        image_location = tempfile.NamedTemporaryFile()
        self.clients("glance").images.create.return_value = self.image
        scenario = utils.GlanceScenario()
        return_image = scenario._create_image("container_format",
                                              image_location.name,
                                              "disk_format")
        self.wait_for.mock.assert_called_once_with(self.image,
                                                   update_resource=self.gfm(),
                                                   is_ready=self.res_is.mock(),
                                                   check_interval=1,
                                                   timeout=120)
        self.res_is.mock.assert_has_calls([mock.call("active")])
        self.assertEqual(self.wait_for.mock(), return_image)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "glance.create_image")

    def test_create_image_with_location(self):
        self.clients("glance").images.create.return_value = self.image
        scenario = utils.GlanceScenario()
        return_image = scenario._create_image("container_format",
                                              "image_location",
                                              "disk_format")
        self.wait_for.mock.assert_called_once_with(self.image,
                                                   update_resource=self.gfm(),
                                                   is_ready=self.res_is.mock(),
                                                   check_interval=1,
                                                   timeout=120)
        self.res_is.mock.assert_has_calls([mock.call("active")])
        self.assertEqual(self.wait_for.mock(), return_image)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "glance.create_image")

    def test_delete_image(self):
        scenario = utils.GlanceScenario()
        scenario._delete_image(self.image)
        self.image.delete.assert_called_once_with()
        self.wait_for_delete.mock.assert_called_once_with(
            self.image,
            update_resource=self.gfm(),
            check_interval=1,
            timeout=120)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "glance.delete_image")
