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

from rally.benchmark.scenarios.ceilometer import ceilometer
from tests import test


class CeilometerBasicTestCase(test.TestCase):
    def test_create_alarm(self):
        scenario = ceilometer.CeilometerBasic()

        scenario._create_alarm = mock.MagicMock()
        scenario.create_alarm("fake_meter_name",
                              "fake_threshold",
                              fakearg="f")
        scenario._create_alarm.assert_called_once_with("fake_meter_name",
                                                       "fake_threshold",
                                                       {'fakearg': 'f'})

    def test_list_alarm(self):
        scenario = ceilometer.CeilometerBasic()

        scenario._list_alarms = mock.MagicMock()
        scenario.list_alarms()
        scenario._list_alarms.assert_called_once_with()

    def test_create_and_list_alarm(self):
        fake_alarm = mock.MagicMock()
        scenario = ceilometer.CeilometerBasic()

        scenario._create_alarm = mock.MagicMock(return_value=fake_alarm)
        scenario._list_alarms = mock.MagicMock()
        scenario.create_and_list_alarm("fake_meter_name",
                                       "fake_threshold",
                                       fakearg="f")
        scenario._create_alarm.assert_called_once_with("fake_meter_name",
                                                       "fake_threshold",
                                                       {'fakearg': 'f'})
        scenario._list_alarms.assert_called_once_with(fake_alarm.alarm_id)

    def test_create_and_update_alarm(self):
        fake_alram_dict_diff = {'description': 'Changed Test Description'}
        fake_alarm = mock.MagicMock()
        scenario = ceilometer.CeilometerBasic()

        scenario._create_alarm = mock.MagicMock(return_value=fake_alarm)
        scenario._update_alarm = mock.MagicMock()
        scenario.create_and_update_alarm("fake_meter_name",
                                         "fake_threshold",
                                         fakearg="f")
        scenario._create_alarm.assert_called_once_with("fake_meter_name",
                                                       "fake_threshold",
                                                       {'fakearg': 'f'})
        scenario._update_alarm.assert_called_once_with(fake_alarm.alarm_id,
                                                       fake_alram_dict_diff)

    def test_create_and_delete_alarm(self):
        fake_alarm = mock.MagicMock()
        scenario = ceilometer.CeilometerBasic()

        scenario._create_alarm = mock.MagicMock(return_value=fake_alarm)
        scenario._delete_alarm = mock.MagicMock()
        scenario.create_and_delete_alarm("fake_meter_name",
                                         "fake_threshold",
                                         fakearg="f")
        scenario._create_alarm.assert_called_once_with("fake_meter_name",
                                                       "fake_threshold",
                                                       {'fakearg': 'f'})
        scenario._delete_alarm.assert_called_once_with(fake_alarm.alarm_id)
