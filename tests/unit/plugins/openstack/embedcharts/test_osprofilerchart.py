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
from rally.plugins.openstack.embedcharts.osprofilerchart import OSProfilerChart
from tests.unit import test


class OSProfilerChartTestCase(test.TestCase):

    class OSProfilerChart(OSProfilerChart):
        widget = "OSProfiler"

    @mock.patch("osprofiler.drivers.base.get_driver")
    def test_get_osprofiler_data(self, mock_get_driver):
        engine = mock.Mock()
        attrs = {"get_report.return_value": "html"}
        engine.configure_mock(**attrs)
        mock_get_driver.return_value = engine

        data = {"data": {"conn_str": "a", "trace_id": ["1"]}, "title": "a"}
        return_data = OSProfilerChart.render_complete_data(data)
        self.assertEqual("EmbedChart", return_data["widget"])
        self.assertEqual("a : 1", return_data["title"])

        data = {"data": {"conn_str": None, "trace_id": ["1"]}, "title": "a"}
        return_data = OSProfilerChart.render_complete_data(data)
        self.assertEqual("TextArea", return_data["widget"])
        self.assertEqual(["1"], return_data["data"])
        self.assertEqual("a", return_data["title"])

        mock_get_driver.side_effect = Exception
        data = {"data": {"conn_str": "a", "trace_id": ["1"]}, "title": "a"}
        return_data = OSProfilerChart.render_complete_data(data)
        self.assertEqual("TextArea", return_data["widget"])
        self.assertEqual(["1"], return_data["data"])
        self.assertEqual("a", return_data["title"])

    def test_datetime_json_serialize(self):
        from rally.plugins.openstack.embedcharts.osprofilerchart \
            import _datetime_json_serialize
        A = mock.Mock()
        B = A.isoformat()
        self.assertEqual(B, _datetime_json_serialize(A))
        self.assertEqual("C", _datetime_json_serialize("C"))
