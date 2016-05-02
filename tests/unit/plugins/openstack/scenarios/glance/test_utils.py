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

import ddt
import mock

from rally.plugins.openstack.scenarios.glance import utils
from tests.unit import test

GLANCE_UTILS = "rally.plugins.openstack.scenarios.glance.utils"


@ddt.ddt
class GlanceScenarioTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(GlanceScenarioTestCase, self).setUp()
        self.image = mock.Mock()
        self.image1 = mock.Mock()
        self.scenario_clients = mock.Mock()
        self.scenario_clients.glance.choose_version.return_value = 1

    def test_list_images(self):
        scenario = utils.GlanceScenario(context=self.context)
        return_images_list = scenario._list_images()
        self.clients("glance").images.list.assert_called_once_with()
        self.assertEqual(list(self.clients("glance").images.list.return_value),
                         return_images_list)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "glance.list_images")

    @ddt.data({},
              {"name": "foo"},
              {"name": None},
              {"name": ""},
              {"name": "bar", "fakearg": "fakearg"},
              {"fakearg": "fakearg"})
    @mock.patch("rally.plugins.openstack.wrappers.glance.wrap")
    def test_create_image(self, create_args, mock_wrap):
        image_location = tempfile.NamedTemporaryFile()
        mock_wrap.return_value.create_image.return_value = self.image
        scenario = utils.GlanceScenario(context=self.context,
                                        clients=self.scenario_clients)
        scenario.generate_random_name = mock.Mock()

        return_image = scenario._create_image("container_format",
                                              image_location.name,
                                              "disk_format",
                                              **create_args)

        expected_args = dict(create_args)
        if not expected_args.get("name"):
            expected_args["name"] = scenario.generate_random_name.return_value

        self.assertEqual(self.image, return_image)
        mock_wrap.assert_called_once_with(scenario._clients.glance, scenario)
        mock_wrap.return_value.create_image.assert_called_once_with(
            "container_format", image_location.name, "disk_format",
            **expected_args)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "glance.create_image")

    @mock.patch("rally.plugins.openstack.wrappers.glance.wrap")
    def test_delete_image(self, mock_wrap):
        deleted_image = mock.Mock(status="DELETED")
        wrapper = mock_wrap.return_value
        wrapper.get_image.side_effect = [self.image, deleted_image]

        scenario = utils.GlanceScenario(context=self.context,
                                        clients=self.scenario_clients)
        scenario._delete_image(self.image)
        self.clients("glance").images.delete.assert_called_once_with(
            self.image.id)

        mock_wrap.assert_called_once_with(scenario._clients.glance, scenario)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "glance.delete_image")
