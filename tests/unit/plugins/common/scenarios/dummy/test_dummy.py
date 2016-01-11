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

from rally.plugins.common.scenarios.dummy import dummy
from tests.unit import test


class DummyTestCase(test.TestCase):

    @mock.patch("rally.plugins.common.scenarios.dummy.dummy.utils."
                "interruptable_sleep")
    def test_dummy(self, mock_interruptable_sleep):
        scenario = dummy.Dummy(test.get_test_context())
        scenario.sleep_between = mock.MagicMock()

        scenario.dummy(sleep=10)
        mock_interruptable_sleep.assert_called_once_with(10)

    @mock.patch("rally.plugins.common.scenarios.dummy.dummy.utils."
                "interruptable_sleep")
    def test_dummy_exception(self, mock_interruptable_sleep):
        scenario = dummy.Dummy(test.get_test_context())

        size_of_message = 5
        self.assertRaises(dummy.DummyScenarioException,
                          scenario.dummy_exception, size_of_message, sleep=10)
        mock_interruptable_sleep.assert_called_once_with(10)

    def test_dummy_exception_probability(self):
        scenario = dummy.Dummy(test.get_test_context())

        # should not raise an exception as probability is 0
        for i in range(100):
            scenario.dummy_exception_probability(exception_probability=0)

        # should always raise an exception as probability is 1
        for i in range(100):
            self.assertRaises(dummy.DummyScenarioException,
                              scenario.dummy_exception_probability,
                              exception_probability=1)

    @mock.patch("rally.plugins.common.scenarios.dummy.dummy.random")
    def test_dummy_output(self, mock_random):
        mock_random.randint.side_effect = lambda min_, max_: max_
        desc = "This is a description text for %s"
        for random_range, exp in (None, 25), (1, 1), (42, 42):
            scenario = dummy.Dummy(test.get_test_context())
            if random_range is None:
                scenario.dummy_output()
            else:
                scenario.dummy_output(random_range=random_range)
            expected = {
                "additive": [
                    {"chart_plugin": "StatsTable",
                     "data": [[s + " stat", exp]
                              for s in ("foo", "bar", "spam")],
                     "title": "Additive Stat Table",
                     "description": desc % "Additive Stat Table"},
                    {"chart_plugin": "StackedArea",
                     "data": [["foo 1", exp], ["foo 2", exp]],
                     "title": "Additive Foo StackedArea",
                     "description": desc % "Additive Foo StackedArea"},
                    {"chart_plugin": "StackedArea",
                     "data": [["bar %d" % i, exp] for i in range(1, 7)],
                     "title": "Additive Bar StackedArea (no description)",
                     "description": ""},
                    {"chart_plugin": "Pie",
                     "data": [["spam %d" % i, exp] for i in range(1, 4)],
                     "title": "Additive Spam Pie",
                     "description": desc % "Additive Spam Pie"}],
                "complete": [
                    {"data": [["alpha", [[i, exp] for i in range(30)]],
                              ["beta", [[i, exp] for i in range(30)]],
                              ["gamma", [[i, exp] for i in range(30)]]],
                     "title": "Complete StackedArea",
                     "description": desc % "Complete StackedArea",
                     "chart_plugin": "StackedArea"},
                    {"data": [["delta", exp], ["epsilon", exp], ["zeta", exp],
                              ["theta", exp], ["lambda", exp], ["omega", exp]],
                     "title": "Complete Pie (no description)",
                     "description": "",
                     "chart_plugin": "Pie"},
                    {"data": {
                        "cols": ["mu column", "xi column", "pi column",
                                 "tau column", "chi column"],
                        "rows": [
                            [r + " row", exp, exp, exp, exp]
                            for r in ("iota", "nu", "rho", "phi", "psi")]},
                     "title": "Complete Table",
                     "description": desc % "Complete Table",
                     "chart_plugin": "Table"}]}
        self.assertEqual(expected, scenario._output)

    def test_dummy_dummy_with_scenario_output(self):
        scenario = dummy.Dummy(test.get_test_context())
        result = scenario.dummy_with_scenario_output()
        self.assertEqual(result["errors"], "")
        # Since the data is generated in random,
        # checking for not None
        self.assertNotEqual(result["data"], None)

    def test_dummy_random_fail_in_atomic(self):
        scenario = dummy.Dummy(test.get_test_context())

        for i in range(10):
            scenario.dummy_random_fail_in_atomic(exception_probability=0)

        for i in range(10):
            self.assertRaises(KeyError,
                              scenario.dummy_random_fail_in_atomic,
                              exception_probability=1)
