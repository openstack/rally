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

    def test_list_traits(self):
        scenario = traits.CeilometerTraits(self.context)

        scenario._user_create = mock.MagicMock()
        scenario._list_events = mock.MagicMock()
        scenario._list_event_traits = mock.MagicMock()
        scenario._list_events.return_value = [mock.Mock(
            event_type="fake_event_type",
            traits=[{"name": "fake_trait_name"}])
        ]
        scenario.create_user_and_list_traits()
        scenario._user_create.assert_called_once_with()
        scenario._list_events.assert_called_with()
        scenario._list_event_traits.assert_called_once_with(
            event_type="fake_event_type", trait_name="fake_trait_name")

    def test_list_trait_descriptions(self):
        scenario = traits.CeilometerTraits(self.context)

        scenario._user_create = mock.MagicMock()
        scenario._list_events = mock.MagicMock()
        scenario._list_event_trait_descriptions = mock.MagicMock()
        scenario._list_events.return_value = [mock.Mock(
            event_type="fake_event_type")
        ]
        scenario.create_user_and_list_trait_descriptions()
        scenario._user_create.assert_called_once_with()
        scenario._list_events.assert_called_with()
        scenario._list_event_trait_descriptions.assert_called_once_with(
            event_type="fake_event_type")
