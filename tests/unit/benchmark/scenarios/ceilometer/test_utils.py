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
from oslotest import mockpatch

from rally.benchmark.scenarios.ceilometer import utils
from tests.unit import fakes
from tests.unit import test

BM_UTILS = "rally.benchmark.utils"
CEILOMETER_UTILS = "rally.benchmark.scenarios.ceilometer.utils"


class CeilometerScenarioTestCase(test.TestCase):
    def setUp(self):
        super(CeilometerScenarioTestCase, self).setUp()
        self.scenario = utils.CeilometerScenario()
        self.scenario.clients = mock.MagicMock(
            return_value=fakes.FakeCeilometerClient())
        self.res_is = mockpatch.Patch(BM_UTILS + ".resource_is")
        self.get_fm = mockpatch.Patch(BM_UTILS + ".get_from_manager")
        self.wait_for = mockpatch.Patch(CEILOMETER_UTILS +
                                        ".bench_utils.wait_for")
        self.useFixture(self.wait_for)
        self.useFixture(self.res_is)
        self.useFixture(self.get_fm)
        self.gfm = self.get_fm.mock

    def test__list_alarms(self):
        alarm1_id = "fake_alarm1_id"
        alarm2_id = "fake_alarm2_id"
        alarm1 = self.scenario._create_alarm("fake_alarm1", 100,
                                             {"alarm_id": alarm1_id})
        alarm2 = self.scenario._create_alarm("fake_alarm2", 100,
                                             {"alarm_id": alarm2_id})

        result_by_id = self.scenario._list_alarms(alarm1_id)
        self.assertEqual([alarm1], result_by_id)

        result_no_args = self.scenario._list_alarms()
        self.assertEqual(set(result_no_args), set([alarm1, alarm2]))

    def test__create_alarm(self):
        """Test _create_alarm returns alarm."""
        fake_alarm_dict = {"alarm_id": "fake-alarm-id"}
        created_alarm = self.scenario._create_alarm("fake-meter-name", 100,
                                                    fake_alarm_dict)

        self.assertEqual(created_alarm.alarm_id, "fake-alarm-id")

    def test__delete_alarms(self):
        """Test if call to alarms.delete is made to ensure alarm is deleted."""
        # pre-populate alarm for this test scenario
        fake_alarm_dict = {"alarm_id": "fake-alarm-id"}
        fake_alarm = self.scenario._create_alarm("fake-meter-name", 100,
                                                 fake_alarm_dict)

        self.scenario._delete_alarm(fake_alarm.alarm_id)
        self.assertEqual(fake_alarm.status, "DELETED")

    def test__update_alarms(self):
        """Test if call to alarms.update is made to ensure alarm is updated."""
        # pre-populate alarm for this test scenario
        fake_alarm_dict = {"alarm_id": "fake-alarm-id"}
        fake_alarm = self.scenario._create_alarm("fake-meter-name", 100,
                                                 fake_alarm_dict)

        fake_alarm_dict_diff = {"description": "Changed Test Description"}
        self.scenario._update_alarm(fake_alarm.alarm_id, fake_alarm_dict_diff)
        self.assertEqual(fake_alarm.description, "Changed Test Description")

    def test__get_alarm_history(self):
        fake_history = self.scenario._get_alarm_history("fake-alarm")
        self.assertEqual(fake_history, ["fake-alarm-history"])

    def test__get_alarm_state(self):
        fake_alarm_dict = {"alarm_id": "alarm-id", "state": "alarm-state"}
        fake_alarm = self.scenario._create_alarm("fake-meter-name", 100,
                                                 fake_alarm_dict)
        fake_state = self.scenario._get_alarm_state(fake_alarm.alarm_id)
        self.assertEqual(fake_state, "alarm-state")

    @mock.patch(CEILOMETER_UTILS + ".CeilometerScenario.clients")
    def test__set_alarm_state(self, mock_clients):
        alarm = mock.Mock()
        mock_clients("ceilometer").alarms.create.return_value = alarm
        return_alarm = self.scenario._set_alarm_state(alarm, "ok", 100)
        self.wait_for.mock.assert_called_once_with(
            alarm,
            is_ready=self.res_is.mock(),
            update_resource=self.gfm(),
            timeout=100, check_interval=1)
        self.res_is.mock.assert_has_calls([mock.call("ok")])
        self.assertEqual(self.wait_for.mock(), return_alarm)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "ceilometer.set_alarm_state")

    def test__list_meters(self):
        """Test _list_meters."""
        fake_meters = self.scenario._list_meters()
        self.assertEqual(fake_meters, ["fake-meter"])

    def test__list_resources(self):
        """Test _list_resources."""
        fake_resources = self.scenario._list_resources()
        self.assertEqual(fake_resources, ["fake-resource"])

    def test__get_stats(self):
        """Test _get_stats function."""
        fake_statistics = self.scenario._get_stats("fake-meter")
        self.assertEqual(fake_statistics, ["fake-meter-statistics"])

    def test__create_meter(self):
        """Test _create_meter returns meter."""
        self.scenario._generate_random_name = mock.MagicMock(
            return_value="fake-counter-name")
        created_meter = self.scenario._create_meter()
        self.assertEqual(created_meter.counter_name, "fake-counter-name")

    def test__query_alarms(self):
        expected_result = ["fake-query-result"]
        query_result = self.scenario._query_alarms("fake-filter",
                                                   "fake-orderby-attribute",
                                                   10)
        self.assertEqual(query_result, expected_result)

    def test__query_alarm_history(self):
        expected_result = ["fake-query-result"]
        query_result = self.scenario._query_alarm_history(
            "fake-filter", "fake-orderby-attribute", 10)
        self.assertEqual(query_result, expected_result)

    def test__query_samples(self):
        expected_result = ["fake-query-result"]
        query_result = self.scenario._query_samples("fake-filter",
                                                    "fake-orderby-attribute",
                                                    10)
        self.assertEqual(query_result, expected_result)

    def test__create_sample(self):
        """Test _create_sample returns sample."""
        self.scenario._generate_random_name = mock.MagicMock(
            return_value="test-counter-name")
        created_sample = self.scenario._create_sample("test-counter-name",
                                                      "fake-counter-type",
                                                      "fake-counter-unit",
                                                      "fake-counter-volume",
                                                      "fake-resource-id")
        self.assertEqual(created_sample[0].counter_name, "test-counter-name")
