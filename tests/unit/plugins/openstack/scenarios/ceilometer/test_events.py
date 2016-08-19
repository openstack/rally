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

from rally.plugins.openstack.scenarios.ceilometer import events
from tests.unit import test


class CeilometerEventsTestCase(test.ScenarioTestCase):

    def test_list_events(self):
        scenario = events.CeilometerEventsCreateUserAndListEvents(self.context)

        scenario._user_create = mock.MagicMock()
        scenario._list_events = mock.MagicMock()
        scenario.run()
        scenario._user_create.assert_called_once_with()
        scenario._list_events.assert_called_once_with()

    def test_list_event_types(self):
        scenario = events.CeilometerEventsCreateUserAndListEventTypes(
            self.context)

        scenario._list_event_types = mock.MagicMock()
        scenario._user_create = mock.MagicMock()
        scenario.run()
        scenario._user_create.assert_called_once_with()
        scenario._list_event_types.assert_called_once_with()

    def test_get_event(self):
        scenario = events.CeilometerEventsCreateUserAndGetEvent(self.context)

        scenario._user_create = mock.MagicMock()
        scenario._list_events = mock.MagicMock()
        scenario._get_event = mock.MagicMock()
        scenario._list_events.return_value = [mock.Mock(message_id="fake_id")]
        scenario.run()
        scenario._user_create.assert_called_once_with()
        scenario._list_events.assert_called_with()
        scenario._get_event.assert_called_with(event_id="fake_id")
