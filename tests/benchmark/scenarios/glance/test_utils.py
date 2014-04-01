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

from rally.benchmark.scenarios.glance import utils
from rally.benchmark import utils as butils
from rally import exceptions as rally_exceptions
from rally.openstack.common.fixture import mockpatch
from tests.benchmark.scenarios import test_utils
from tests import fakes
from tests import test

BM_UTILS = 'rally.benchmark.utils'
GLANCE_UTILS = 'rally.benchmark.scenarios.glance.utils'


class GlanceScenarioTestCase(test.TestCase):

    def setUp(self):
        super(GlanceScenarioTestCase, self).setUp()
        self.image = mock.Mock()
        self.image1 = mock.Mock()
        self.res_is = mockpatch.Patch(BM_UTILS + ".resource_is")
        self.get_fm = mockpatch.Patch(BM_UTILS + '.get_from_manager')
        self.wait_for = mockpatch.Patch(GLANCE_UTILS + ".bench_utils.wait_for")
        self.wait_for_delete = mockpatch.Patch(
            GLANCE_UTILS + ".bench_utils.wait_for_delete")
        self.useFixture(self.wait_for)
        self.useFixture(self.wait_for_delete)
        self.useFixture(self.res_is)
        self.useFixture(self.get_fm)
        self.gfm = self.get_fm.mock
        self.useFixture(mockpatch.Patch('time.sleep'))
        self.scenario = utils.GlanceScenario()

    def test_generate_random_name(self):
        for length in [8, 16, 32, 64]:
            name = self.scenario._generate_random_name(length)
            self.assertEqual(len(name), 16 + length)

    def test_failed_image_status(self):
        self.get_fm.cleanUp()
        image_manager = fakes.FakeFailedImageManager()
        self.assertRaises(rally_exceptions.GetResourceFailure,
                          butils.get_from_manager(),
                          image_manager.create('fails', 'url', 'cf', 'df'))

    def _test_atomic_action_timer(self, atomic_actions_time, name):
        action_duration = test_utils.get_atomic_action_timer_value_by_name(
            atomic_actions_time, name)
        self.assertIsNotNone(action_duration)
        self.assertIsInstance(action_duration, float)

    @mock.patch(GLANCE_UTILS + '.GlanceScenario.clients')
    def test_list_images(self, mock_clients):
        images_list = []
        mock_clients("glance").images.list.return_value = images_list
        scenario = utils.GlanceScenario()
        return_images_list = scenario._list_images()
        self.assertEqual(images_list, return_images_list)
        self._test_atomic_action_timer(scenario.atomic_actions_time(),
                                       'glance.list_images')

    @mock.patch(GLANCE_UTILS + '.GlanceScenario.clients')
    def test_create_image(self, mock_clients):
        mock_clients("glance").images.create.return_value = self.image
        scenario = utils.GlanceScenario()
        return_image = scenario._create_image('image_name',
                                              'image_url',
                                              'container_format',
                                              'disk_format')
        self.wait_for.mock.assert_called_once_with(self.image,
                                                   update_resource=self.gfm(),
                                                   is_ready=self.res_is.mock(),
                                                   check_interval=1,
                                                   timeout=120)
        self.res_is.mock.assert_has_calls(mock.call('active'))
        self.assertEqual(self.wait_for.mock(), return_image)
        self._test_atomic_action_timer(scenario.atomic_actions_time(),
                                       'glance.create_image')

    def test_delete_image(self):
        scenario = utils.GlanceScenario()
        scenario._delete_image(self.image)
        self.image.delete.assert_called_once_with()
        self.wait_for_delete.\
            mock.assert_called_once_with(self.image,
                                         update_resource=self.gfm(),
                                         check_interval=1,
                                         timeout=120)
        self._test_atomic_action_timer(scenario.atomic_actions_time(),
                                       'glance.delete_image')
