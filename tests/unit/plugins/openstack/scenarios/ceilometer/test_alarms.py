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

from rally.plugins.openstack.scenarios.ceilometer import alarms
from tests.unit import test


class CeilometerAlarmsTestCase(test.ScenarioTestCase):
    def test_create_alarm(self):
        scenario = alarms.CreateAlarm(self.context)

        scenario._create_alarm = mock.MagicMock()
        scenario.run("fake_meter_name", "fake_threshold", fakearg="f")
        scenario._create_alarm.assert_called_once_with("fake_meter_name",
                                                       "fake_threshold",
                                                       {"fakearg": "f"})

    def test_list_alarm(self):
        scenario = alarms.ListAlarms(self.context)

        scenario._list_alarms = mock.MagicMock()
        scenario.run()
        scenario._list_alarms.assert_called_once_with()

    def test_create_and_list_alarm(self):
        fake_alarm = mock.MagicMock()
        scenario = alarms.CreateAndListAlarm(self.context)

        scenario._create_alarm = mock.MagicMock(return_value=fake_alarm)
        scenario._list_alarms = mock.MagicMock()
        scenario.run("fake_meter_name", "fake_threshold", fakearg="f")
        scenario._create_alarm.assert_called_once_with("fake_meter_name",
                                                       "fake_threshold",
                                                       {"fakearg": "f"})
        scenario._list_alarms.assert_called_once_with(fake_alarm.alarm_id)

    def test_create_and_update_alarm(self):
        fake_alram_dict_diff = {"description": "Changed Test Description"}
        fake_alarm = mock.MagicMock()
        scenario = alarms.CreateAndUpdateAlarm(self.context)

        scenario._create_alarm = mock.MagicMock(return_value=fake_alarm)
        scenario._update_alarm = mock.MagicMock()
        scenario.run("fake_meter_name", "fake_threshold", fakearg="f")
        scenario._create_alarm.assert_called_once_with("fake_meter_name",
                                                       "fake_threshold",
                                                       {"fakearg": "f"})
        scenario._update_alarm.assert_called_once_with(fake_alarm.alarm_id,
                                                       fake_alram_dict_diff)

    def test_create_and_delete_alarm(self):
        fake_alarm = mock.MagicMock()
        scenario = alarms.CreateAndDeleteAlarm(self.context)

        scenario._create_alarm = mock.MagicMock(return_value=fake_alarm)
        scenario._delete_alarm = mock.MagicMock()
        scenario.run("fake_meter_name", "fake_threshold", fakearg="f")
        scenario._create_alarm.assert_called_once_with("fake_meter_name",
                                                       "fake_threshold",
                                                       {"fakearg": "f"})
        scenario._delete_alarm.assert_called_once_with(fake_alarm.alarm_id)

    def test_create_and_get_alarm_history(self):
        alarm = mock.Mock(alarm_id="foo_id")
        scenario = alarms.CreateAlarmAndGetHistory(
            self.context)

        scenario._create_alarm = mock.MagicMock(return_value=alarm)
        scenario._get_alarm_state = mock.MagicMock()
        scenario._get_alarm_history = mock.MagicMock()
        scenario._set_alarm_state = mock.MagicMock()
        scenario.run("meter_name", "threshold", "state", 60, fakearg="f")
        scenario._create_alarm.assert_called_once_with(
            "meter_name", "threshold", {"fakearg": "f"})
        scenario._get_alarm_state.assert_called_once_with("foo_id")
        scenario._get_alarm_history.assert_called_once_with("foo_id")
        scenario._set_alarm_state.assert_called_once_with(alarm, "state", 60)
