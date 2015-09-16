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
from oslo_config import cfg

from rally.plugins.openstack.scenarios.glance import utils
from tests.unit import test

GLANCE_UTILS = "rally.plugins.openstack.scenarios.glance.utils"
CONF = cfg.CONF


class GlanceScenarioTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(GlanceScenarioTestCase, self).setUp()
        self.image = mock.Mock()
        self.image1 = mock.Mock()

    def test_list_images(self):
        scenario = utils.GlanceScenario(context=self.context)
        return_images_list = scenario._list_images()
        self.clients("glance").images.list.assert_called_once_with()
        self.assertEqual(list(self.clients("glance").images.list.return_value),
                         return_images_list)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "glance.list_images")

    def test_create_image(self):
        image_location = tempfile.NamedTemporaryFile()
        self.clients("glance").images.create.return_value = self.image
        scenario = utils.GlanceScenario(context=self.context)
        return_image = scenario._create_image("container_format",
                                              image_location.name,
                                              "disk_format")
        self.mock_wait_for.mock.assert_called_once_with(
            self.image,
            update_resource=self.mock_get_from_manager.mock.return_value,
            is_ready=self.mock_resource_is.mock.return_value,
            check_interval=CONF.benchmark.glance_image_create_poll_interval,
            timeout=CONF.benchmark.glance_image_create_timeout)
        self.mock_resource_is.mock.assert_called_once_with("active")
        self.mock_get_from_manager.mock.assert_called_once_with()
        self.assertEqual(self.mock_wait_for.mock.return_value, return_image)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "glance.create_image")

    def test_create_image_with_location(self):
        self.clients("glance").images.create.return_value = self.image
        scenario = utils.GlanceScenario(context=self.context)
        return_image = scenario._create_image("container_format",
                                              "image_location",
                                              "disk_format")
        self.mock_wait_for.mock.assert_called_once_with(
            self.image,
            update_resource=self.mock_get_from_manager.mock.return_value,
            is_ready=self.mock_resource_is.mock.return_value,
            check_interval=CONF.benchmark.glance_image_create_poll_interval,
            timeout=CONF.benchmark.glance_image_create_timeout)
        self.mock_resource_is.mock.assert_called_once_with("active")
        self.mock_get_from_manager.mock.assert_called_once_with()
        self.assertEqual(self.mock_wait_for.mock.return_value, return_image)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "glance.create_image")

    def test_delete_image(self):
        scenario = utils.GlanceScenario(context=self.context)
        scenario._delete_image(self.image)
        self.image.delete.assert_called_once_with()
        self.mock_wait_for_delete.mock.assert_called_once_with(
            self.image,
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.glance_image_delete_poll_interval,
            timeout=CONF.benchmark.glance_image_delete_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "glance.delete_image")
