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

from rally.benchmark.scenarios.ceilometer import utils
from tests.benchmark.scenarios import test_utils
from tests import test

UTILS = "rally.benchmark.scenarios.ceilometer.utils"


class CeilometerScenarioTestCase(test.TestCase):
    def _test_atomic_action_timer(self, atomic_actions_time, name):
        action_duration = test_utils.get_atomic_action_timer_value_by_name(
            atomic_actions_time, name)
        self.assertIsNotNone(action_duration)
        self.assertIsInstance(action_duration, float)

    @mock.patch(UTILS + '.CeilometerScenario.clients')
    def test__list_alarm(self, mock_clients):
        """Test _list_alarms when alarm_id is passed to it."""
        fake_alarms = ['fake_alarm']
        mock_clients("ceilometer").alarms.get.return_value = fake_alarms
        scenario = utils.CeilometerScenario()
        alarms = scenario._list_alarms("FAKE_ALARM_ID")
        self.assertEqual(fake_alarms, alarms)

    @mock.patch(UTILS + '.CeilometerScenario.clients')
    def test__list_alarms(self, mock_clients):
        """Test _list_alarms when no alarm_id is passed to it."""
        fake_alarms = []
        mock_clients("ceilometer").alarms.list.return_value = fake_alarms
        scenario = utils.CeilometerScenario()
        alarms = scenario._list_alarms()
        self.assertEqual(fake_alarms, alarms)

    @mock.patch(UTILS + '.CeilometerScenario.clients')
    def test__create_alarm(self, mock_clients):
        """Test _create_alarm returns alarm."""
        fake_alarm = mock.MagicMock()
        fake_alarm_dict = dict()
        mock_clients("ceilometer").alarms.create.return_value = fake_alarm
        scenario = utils.CeilometerScenario()
        created_alarm = scenario._create_alarm("fake_meter_name",
                                               "fake_threshold",
                                               fake_alarm_dict)
        self.assertEqual(fake_alarm, created_alarm)

    @mock.patch(UTILS + '.CeilometerScenario.clients')
    def test__delete_alarms(self, mock_clients):
        """Test if call to alarms.delete is made to ensure alarm is deleted."""
        scenario = utils.CeilometerScenario()
        scenario._delete_alarm("FAKE_ALARM_ID")
        mock_clients("ceilometer").alarms.delete.assert_called_once_with(
            "FAKE_ALARM_ID")

    @mock.patch(UTILS + '.CeilometerScenario.clients')
    def test__update_alarms(self, mock_clients):
        """Test if call to alarms.update is made to ensure alarm is updated."""
        fake_alarm_dict_diff = {"description": "Changed Test Description"}
        scenario = utils.CeilometerScenario()
        scenario._update_alarm("FAKE_ALARM_ID", fake_alarm_dict_diff)
        mock_clients("ceilometer").alarms.update.assert_called_once_with(
            "FAKE_ALARM_ID", **fake_alarm_dict_diff)

    @mock.patch(UTILS + '.CeilometerScenario.clients')
    def test__list_meters(self, mock_clients):
        """Test _list_meters."""
        fake_meters = []
        mock_clients("ceilometer").meters.list.return_value = fake_meters
        scenario = utils.CeilometerScenario()
        meters = scenario._list_meters()
        self.assertEqual(fake_meters, meters)

    @mock.patch(UTILS + '.CeilometerScenario.clients')
    def test__list_resources(self, mock_clients):
        """Test _list_resources."""
        fake_resources = []
        mock_clients("ceilometer").resources.list.return_value = fake_resources
        scenario = utils.CeilometerScenario()
        resources = scenario._list_resources()
        self.assertEqual(fake_resources, resources)

    @mock.patch(UTILS + '.CeilometerScenario.clients')
    def test__get_stats(self, mock_clients):
        """Test _get_stats function."""
        fake_stats = mock.MagicMock()
        mock_clients("ceilometer").statistics.list.return_value = fake_stats
        scenario = utils.CeilometerScenario()
        stats = scenario._get_stats("fake_name")
        self.assertEqual(fake_stats, stats)

    @mock.patch(UTILS + '.CeilometerScenario.clients')
    def test__create_meter(self, mock_clients):
        """Test _create_meter returns meter."""
        fake_meter = mock.MagicMock()
        kwargs = mock.MagicMock()
        mock_clients("ceilometer").samples.create.return_value = [fake_meter]
        scenario = utils.CeilometerScenario()
        created_meter = scenario._create_meter(**kwargs)
        self.assertEqual(fake_meter, created_meter)
