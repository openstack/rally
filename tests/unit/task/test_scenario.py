# Copyright 2013: Mirantis Inc.
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
from rally.task import context
from rally.task import scenario
from tests.unit import test


class ScenarioConfigureTestCase(test.TestCase):

    def test_configure(self):

        @scenario.configure(name="fooscenario.name", platform="testing")
        class SomeScenario(scenario.Scenario):
            def run(self):
                pass

        self.assertEqual("fooscenario.name", SomeScenario.get_name())
        self.assertEqual("testing", SomeScenario.get_platform())
        SomeScenario.unregister()


class ScenarioTestCase(test.TestCase):

    def test_sleep_between_invalid_args(self):
        self.assertRaises(exceptions.InvalidArgumentsException,
                          scenario.Scenario().sleep_between, 15, 5)

        self.assertRaises(exceptions.InvalidArgumentsException,
                          scenario.Scenario().sleep_between, -1, 0)

        self.assertRaises(exceptions.InvalidArgumentsException,
                          scenario.Scenario().sleep_between, 0, -2)

    def test_get_owner_id_from_task(self):
        scenario_inst = scenario.Scenario(
            context={"task": {"uuid": "task_uuid"}})
        self.assertEqual("task_uuid", scenario_inst.get_owner_id())

    def test_get_owner_id(self):
        scenario_inst = scenario.Scenario(
            context={"task": {"uuid": "task_uuid"}, "owner_id": "foo_uuid"})
        self.assertEqual("foo_uuid", scenario_inst.get_owner_id())

    def test_sleep_between(self):
        scenario_inst = scenario.Scenario()
        scenario_inst.sleep_between(0.001, 0.002)
        self.assertGreaterEqual(scenario_inst.idle_duration(), 0.001)
        self.assertLessEqual(scenario_inst.idle_duration(), 0.002)

    def test_sleep_beetween_multi(self):
        scenario_inst = scenario.Scenario()
        scenario_inst.sleep_between(0.001, 0.001)
        scenario_inst.sleep_between(0.004, 0.004)
        self.assertEqual(0.005, scenario_inst.idle_duration())

    @mock.patch("rally.common.utils.interruptable_sleep")
    @mock.patch("rally.task.scenario.random.uniform")
    def test_sleep_between_internal(self, mock_uniform,
                                    mock_interruptable_sleep):
        scenario_inst = scenario.Scenario()

        mock_uniform.return_value = 1.5
        scenario_inst.sleep_between(1, 2)

        mock_interruptable_sleep.assert_called_once_with(
            mock_uniform.return_value, 0.1)
        self.assertEqual(scenario_inst.idle_duration(),
                         mock_uniform.return_value)

    def test_scenario_context_are_valid(self):
        for s in scenario.Scenario.get_all():
            results = []
            for context_name, context_conf in s.get_default_context().items():
                results.extend(context.Context.validate(
                    name=context_name,
                    context=None,
                    config=None,
                    plugin_cfg=context_conf,
                    allow_hidden=True,
                    vtype="syntax"))

            if results:
                msg = "\n ".join([str(r) for r in results])
                print(msg)
                self.fail("Scenario `%s` has wrong context" % s)

    def test_add_output(self):
        scenario_inst = scenario.Scenario()
        self.assertEqual({"additive": [], "complete": []},
                         scenario_inst._output)

        additive1 = {"title": "Additive 1", "chart_plugin": "Plugin1",
                     "description": "Foo description",
                     "data": [["foo", 1], ["bar", 2]]}
        additive2 = {"title": "Additive 2", "chart_plugin": "Plugin2",
                     "description": "Bar description",
                     "data": [["foo", 42], ["bar", 24]]}
        complete1 = {"title": "Complete 1", "chart_plugin": "Plugin3",
                     "description": "Complete description",
                     "data": [["ab", 1], ["cd", 2]]}
        complete2 = {"title": "Complete 2", "chart_plugin": "Plugin4",
                     "description": "Another complete description",
                     "data": [["vx", 1], ["yz", 2]]}

        scenario_inst.add_output(additive=additive1)
        self.assertEqual({"additive": [additive1], "complete": []},
                         scenario_inst._output)

        scenario_inst.add_output(complete=complete1)
        self.assertEqual({"additive": [additive1], "complete": [complete1]},
                         scenario_inst._output)

        scenario_inst.add_output(additive=additive2, complete=complete2)
        self.assertEqual({"additive": [additive1, additive2],
                          "complete": [complete1, complete2]},
                         scenario_inst._output)

    def test_add_output_raises(self):
        additive = {"title": "Foo title", "chart_plugin": "Plugin1",
                    "description": "Foo description",
                    "data": [["ab", 1], ["cd", 2]]}
        complete = {"title": "Bar title", "chart_plugin": "Plugin2",
                    "description": "Bar description",
                    "data": [["ef", 1], ["jh", 2]]}
        scenario_inst = scenario.Scenario()

        scenario_inst.add_output(additive=additive, complete=complete)

        for key in "title", "chart_plugin", "data":
            broken_additive = additive.copy()
            del broken_additive[key]
            self.assertRaises(exceptions.RallyException,
                              scenario_inst.add_output,
                              additive=broken_additive)

            broken_complete = complete.copy()
            del broken_complete[key]
            self.assertRaises(exceptions.RallyException,
                              scenario_inst.add_output,
                              complete=broken_complete)
