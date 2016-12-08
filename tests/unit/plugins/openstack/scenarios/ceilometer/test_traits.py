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

from rally.plugins.openstack.scenarios.ceilometer import traits
from tests.unit import test


class CeilometerTraitsTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(CeilometerTraitsTestCase, self).setUp()
        patch = mock.patch(
            "rally.plugins.openstack.services.identity.identity.Identity")
        self.addCleanup(patch.stop)
        self.mock_identity = patch.start()

    def get_test_context(self):
        context = super(CeilometerTraitsTestCase, self).get_test_context()
        context["admin"] = {"id": "fake_user_id",
                            "credential": mock.MagicMock()
                            }
        return context

    def test_list_traits(self):
        scenario = traits.CreateUserAndListTraits(self.context)

        scenario._list_event_traits = mock.MagicMock()
        scenario._list_events = mock.MagicMock(
            return_value=[mock.Mock(
                event_type="fake_event_type",
                traits=[{"name": "fake_trait_name"}])
            ])

        scenario.run()

        self.mock_identity.return_value.create_user.assert_called_once_with()
        scenario._list_events.assert_called_with()
        scenario._list_event_traits.assert_called_once_with(
            event_type="fake_event_type", trait_name="fake_trait_name")

    def test_list_trait_descriptions(self):
        scenario = traits.CreateUserAndListTraitDescriptions(
            self.context)

        scenario._list_event_trait_descriptions = mock.MagicMock()
        scenario._list_events = mock.MagicMock(
            return_value=[mock.Mock(
                event_type="fake_event_type")
            ])

        scenario.run()

        self.mock_identity.return_value.create_user.assert_called_once_with()
        scenario._list_events.assert_called_with()
        scenario._list_event_trait_descriptions.assert_called_once_with(
            event_type="fake_event_type")
