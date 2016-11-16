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

from rally import exceptions
from rally.plugins.openstack.scenarios.ceilometer import events
from tests.unit import test


class CeilometerEventsTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(CeilometerEventsTestCase, self).setUp()
        patch = mock.patch(
            "rally.plugins.openstack.services.identity.identity.Identity")
        self.addCleanup(patch.stop)
        self.mock_identity = patch.start()

    def get_test_context(self):
        context = super(CeilometerEventsTestCase, self).get_test_context()
        context["admin"] = {"id": "fake_user_id",
                            "credential": mock.MagicMock()
                            }
        return context

    def test_list_events(self):
        scenario = events.CeilometerEventsCreateUserAndListEvents(self.context)

        scenario._list_events = mock.MagicMock()

        scenario.run()

        self.mock_identity.return_value.create_user.assert_called_once_with()
        scenario._list_events.assert_called_once_with()

    def test_list_events_fails(self):
        scenario = events.CeilometerEventsCreateUserAndListEvents(self.context)

        scenario._list_events = mock.MagicMock(return_value=[])

        self.assertRaises(exceptions.RallyException, scenario.run)

        self.mock_identity.return_value.create_user.assert_called_once_with()
        scenario._list_events.assert_called_once_with()

    def test_list_event_types(self):
        scenario = events.CeilometerEventsCreateUserAndListEventTypes(
            self.context)

        scenario._list_event_types = mock.MagicMock()

        scenario.run()

        self.mock_identity.return_value.create_user.assert_called_once_with()
        scenario._list_event_types.assert_called_once_with()

    def test_list_event_types_fails(self):
        scenario = events.CeilometerEventsCreateUserAndListEventTypes(
            self.context)

        scenario._list_event_types = mock.MagicMock(return_value=[])

        self.assertRaises(exceptions.RallyException, scenario.run)

        self.mock_identity.return_value.create_user.assert_called_once_with()
        scenario._list_event_types.assert_called_once_with()

    def test_get_event(self):
        scenario = events.CeilometerEventsCreateUserAndGetEvent(self.context)

        scenario._get_event = mock.MagicMock()
        scenario._list_events = mock.MagicMock(
            return_value=[mock.Mock(message_id="fake_id")])

        scenario.run()

        self.mock_identity.return_value.create_user.assert_called_once_with()
        scenario._list_events.assert_called_with()
        scenario._get_event.assert_called_with(event_id="fake_id")

    def test_get_event_fails(self):
        scenario = events.CeilometerEventsCreateUserAndGetEvent(self.context)

        scenario._list_events = mock.MagicMock(return_value=[])
        scenario._get_event = mock.MagicMock()

        self.assertRaises(exceptions.RallyException, scenario.run)

        self.mock_identity.return_value.create_user.assert_called_once_with()
        scenario._list_events.assert_called_with()
        self.assertFalse(scenario._get_event.called)
