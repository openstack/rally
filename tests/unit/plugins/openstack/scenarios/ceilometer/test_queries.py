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

import json

import mock

from rally.plugins.openstack.scenarios.ceilometer import queries
from tests.unit import test


class CeilometerQueriesTestCase(test.ScenarioTestCase):
    def test_create_and_query_alarms(self):
        scenario = queries.CeilometerQueriesCreateAndQueryAlarms(self.context)

        scenario._create_alarm = mock.MagicMock()
        scenario._query_alarms = mock.MagicMock()

        scenario.run("fake_meter_name", 100, "fake_filter",
                     "fake_orderby_attribute", 10, fakearg="f")
        scenario._create_alarm.assert_called_once_with("fake_meter_name",
                                                       100, {"fakearg": "f"})
        scenario._query_alarms.assert_called_once_with(
            json.dumps("fake_filter"), "fake_orderby_attribute", 10)

    def test_create_and_query_alarms_no_filter(self):
        scenario = queries.CeilometerQueriesCreateAndQueryAlarms(self.context)

        scenario._create_alarm = mock.MagicMock()
        scenario._query_alarms = mock.MagicMock()

        scenario.run("fake_meter_name", 100, None, "fake_orderby_attribute",
                     10, fakearg="f")
        scenario._create_alarm.assert_called_once_with("fake_meter_name",
                                                       100, {"fakearg": "f"})
        scenario._query_alarms.assert_called_once_with(
            None, "fake_orderby_attribute", 10)

    def test_create_and_query_alarm_history(self):
        fake_alarm = mock.MagicMock()
        fake_alarm.alarm_id = "fake_alarm_id"
        scenario = queries.CeilometerQueriesCreateAndQueryAlarmHistory(
            self.context)

        scenario._create_alarm = mock.MagicMock(return_value=fake_alarm)
        scenario._query_alarm_history = mock.MagicMock()

        fake_filter = json.dumps({"=": {"alarm_id": fake_alarm.alarm_id}})
        scenario.run("fake_meter_name", 100, "fake_orderby_attribute",
                     10, fakearg="f")
        scenario._create_alarm.assert_called_once_with("fake_meter_name", 100,
                                                       {"fakearg": "f"})
        scenario._query_alarm_history.assert_called_once_with(
            fake_filter, "fake_orderby_attribute", 10)

    def test_create_and_query_samples(self):
        scenario = queries.CeilometerQueriesCreateAndQuerySamples(self.context)

        scenario._create_sample = mock.MagicMock()
        scenario._query_samples = mock.MagicMock()

        scenario.run("fake_counter_name", "fake_counter_type",
                     "fake_counter_unit", "fake_counter_volume",
                     "fake_resource_id", "fake_filter",
                     "fake_orderby_attribute", 10, fakearg="f")
        scenario._create_sample.assert_called_once_with("fake_counter_name",
                                                        "fake_counter_type",
                                                        "fake_counter_unit",
                                                        "fake_counter_volume",
                                                        "fake_resource_id",
                                                        fakearg="f")
        scenario._query_samples.assert_called_once_with(
            json.dumps("fake_filter"), "fake_orderby_attribute", 10)

    def test_create_and_query_samples_no_filter(self):
        scenario = queries.CeilometerQueriesCreateAndQuerySamples(self.context)

        scenario._create_sample = mock.MagicMock()
        scenario._query_samples = mock.MagicMock()

        scenario.run("fake_counter_name", "fake_counter_type",
                     "fake_counter_unit", "fake_counter_volume",
                     "fake_resource_id", None,
                     "fake_orderby_attribute", 10, fakearg="f")
        scenario._create_sample.assert_called_once_with("fake_counter_name",
                                                        "fake_counter_type",
                                                        "fake_counter_unit",
                                                        "fake_counter_volume",
                                                        "fake_resource_id",
                                                        fakearg="f")
        scenario._query_samples.assert_called_once_with(
            None, "fake_orderby_attribute", 10)
