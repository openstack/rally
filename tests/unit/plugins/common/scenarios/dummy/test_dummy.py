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


import ddt
import mock

from rally.plugins.common.scenarios.dummy import dummy
from tests.unit import test


DUMMY = "rally.plugins.common.scenarios.dummy.dummy."


@ddt.ddt
class DummyFailureTestCase(test.TestCase):

    @ddt.data({"iteration": 0, "kwargs": {}},
              {"iteration": 0, "kwargs": {"each": 1}},
              {"iteration": 5, "kwargs": {"from_iteration": 4},
               "raises": False},
              {"iteration": 5,
               "kwargs": {"from_iteration": 5, "to_iteration": 5}},
              {"iteration": 5,
               "kwargs": {"from_iteration": 4, "to_iteration": 5}},
              {"iteration": 5,
               "kwargs": {"from_iteration": 5, "to_iteration": 6}},
              {"iteration": 5,
               "kwargs": {"from_iteration": 4, "to_iteration": 6}},
              {"iteration": 5, "kwargs": {"from_iteration": 4,
                                          "to_iteration": 6, "sleep": 5}},
              {"iteration": 5, "raises": False,
               "kwargs": {"from_iteration": 4, "to_iteration": 6,
                          "sleep": 5, "each": 2}},
              {"iteration": 6, "kwargs": {"from_iteration": 4,
                                          "to_iteration": 6,
                                          "sleep": 5, "each": 2}})
    @ddt.unpack
    @mock.patch(DUMMY + "utils.interruptable_sleep")
    def test_run(self, mock_interruptable_sleep, iteration, kwargs,
                 raises=True):
        scenario = dummy.DummyFailure(
            test.get_test_context(iteration=iteration))
        if raises:
            self.assertRaises(dummy.DummyScenarioException, scenario.run,
                              **kwargs)
        else:
            scenario.run(**kwargs)
        mock_interruptable_sleep.assert_called_once_with(
            kwargs.get("sleep", 0.1))


@ddt.ddt
class DummyTestCase(test.TestCase):

    @mock.patch(DUMMY + "utils.interruptable_sleep")
    def test_dummy(self, mock_interruptable_sleep):
        scenario = dummy.Dummy(test.get_test_context())
        scenario.sleep_between = mock.MagicMock()

        scenario.run(sleep=10)
        mock_interruptable_sleep.assert_called_once_with(10)

    @mock.patch(DUMMY + "utils.interruptable_sleep")
    def test_dummy_exception(self, mock_interruptable_sleep):
        scenario = dummy.DummyException(test.get_test_context())

        size_of_message = 5
        self.assertRaises(dummy.DummyScenarioException,
                          scenario.run, size_of_message, sleep=10)
        mock_interruptable_sleep.assert_called_once_with(10)

    def test_dummy_exception_probability(self):
        scenario = dummy.DummyExceptionProbability(test.get_test_context())

        # should not raise an exception as probability is 0
        for i in range(100):
            scenario.run(exception_probability=0)

        # should always raise an exception as probability is 1
        for i in range(100):
            self.assertRaises(dummy.DummyScenarioException,
                              scenario.run,
                              exception_probability=1)

    @mock.patch(DUMMY + "random")
    def test_dummy_output(self, mock_random):
        mock_random.randint.side_effect = lambda min_, max_: max_
        desc = "This is a description text for %s"
        for random_range, exp in (None, 25), (1, 1), (42, 42):
            scenario = dummy.DummyOutput(test.get_test_context())
            if random_range is None:
                scenario.run()
            else:
                scenario.run(random_range=random_range)
            expected = {
                "additive": [
                    {"chart_plugin": "StatsTable",
                     "data": [["%s stat" % s, exp]
                              for s in ("foo", "bar", "spam")],
                     "description": desc % "Additive StatsTable",
                     "title": "Additive StatsTable"},
                    {"chart_plugin": "StackedArea",
                     "data": [["foo %i" % i, exp] for i in range(1, 7)],
                     "label": "Measure this in Foo units",
                     "title": "Additive StackedArea (no description)"},
                    {"chart_plugin": "Lines",
                     "data": [["bar %i" % i, exp] for i in range(1, 4)],
                     "description": desc % "Additive Lines",
                     "label": "Measure this in Bar units",
                     "title": "Additive Lines"},
                    {"chart_plugin": "Pie",
                     "data": [["spam %i" % i, exp] for i in range(1, 4)],
                     "description": desc % "Additive Pie",
                     "title": "Additive Pie"}],
                "complete": [
                    {"axis_label": "This is a custom X-axis label",
                     "chart_plugin": "Lines",
                     "data": [["Foo", [[i, exp] for i in range(1, 8)]],
                              ["Bar", [[i, exp] for i in range(1, 8)]],
                              ["Spam", [[i, exp] for i in range(1, 8)]]],
                     "description": desc % "Complete Lines",
                     "label": "Measure this is some units",
                     "title": "Complete Lines"},
                    {"axis_label": "This is a custom X-axis label",
                     "chart_plugin": "StackedArea",
                     "data": [["alpha", [[i, exp] for i in range(50)]],
                              ["beta", [[i, exp] for i in range(50)]],
                              ["gamma", [[i, exp] for i in range(50)]]],
                     "description": desc % "Complete StackedArea",
                     "label": "Yet another measurement units",
                     "title": "Complete StackedArea"},
                    {"title": "Arbitrary Text",
                     "chart_plugin": "TextArea",
                     "data": ["Lorem ipsum dolor sit amet, consectetur "
                              "adipiscing elit, sed do eiusmod tempor "
                              "incididunt ut labore et dolore magna "
                              "aliqua." * 2] * 4},
                    {"chart_plugin": "Pie",
                     "data": [[s, exp] for s in ("delta", "epsilon", "zeta",
                                                 "theta", "lambda", "omega")],
                     "title": "Complete Pie (no description)"},
                    {"chart_plugin": "Table",
                     "data": {"cols": ["%s column" % s
                                       for s in ("mu", "xi", "pi",
                                                 "tau", "chi")],
                              "rows": [["%s row" % s, exp, exp, exp, exp]
                                       for s in ("iota", "nu", "rho",
                                                 "phi", "psi")]},
                     "description": desc % "Complete Table",
                     "title": "Complete Table"}]}

        self.assertEqual(expected, scenario._output)

    def test_dummy_random_fail_in_atomic(self):
        scenario = dummy.DummyRandomFailInAtomic(test.get_test_context())

        for i in range(10):
            scenario.run(exception_probability=0)
        for i in range(10):
            self.assertRaises(KeyError,
                              scenario.run,
                              exception_probability=1)

    @ddt.data({},
              {"actions_num": 5, "sleep_min": 0, "sleep_max": 2},
              {"actions_num": 7, "sleep_min": 1.23, "sleep_max": 4.56},
              {"actions_num": 1, "sleep_max": 4.56},
              {"sleep_min": 1})
    @ddt.unpack
    @mock.patch(DUMMY + "random")
    @mock.patch(DUMMY + "utils.interruptable_sleep")
    def test_dummy_random_action(self, mock_interruptable_sleep, mock_random,
                                 **kwargs):
        mock_random.uniform.side_effect = range(100)

        scenario = dummy.DummyRandomAction(test.get_test_context())
        scenario.run(**kwargs)
        actions_num = kwargs.get("actions_num", 5)
        calls = [mock.call(i) for i in range(actions_num)]
        self.assertEqual(calls, mock_interruptable_sleep.mock_calls)

        calls = [mock.call(kwargs.get("sleep_min", 0),
                           kwargs.get("sleep_max", 2))
                 for i in range(actions_num)]
        self.assertEqual(calls, mock_random.uniform.mock_calls)
        for i in range(actions_num):
            self._test_atomic_action_timer(scenario.atomic_actions(),
                                           "action_%d" % i)

    @ddt.data({"number_of_actions": 5, "sleep_factor": 1},
              {"number_of_actions": 7, "sleep_factor": 2},
              {"number_of_actions": 1, "sleep_factor": 3})
    @ddt.unpack
    @mock.patch(DUMMY + "utils.interruptable_sleep")
    def test_dummy_timed_atomic_actions(self, mock_interruptable_sleep,
                                        number_of_actions, sleep_factor):
        dummy.DummyRandomAction(test.get_test_context()).run(
            number_of_actions, sleep_factor)
        scenario = dummy.DummyTimedAtomicAction(test.get_test_context())
        scenario.run(number_of_actions, sleep_factor)
        for i in range(number_of_actions):
            self._test_atomic_action_timer(scenario.atomic_actions(),
                                           "action_%d" % i)
            mock_interruptable_sleep.assert_any_call(i * sleep_factor)
