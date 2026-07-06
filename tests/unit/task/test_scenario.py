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

import enum
import typing as t
from unittest import mock

import typing_extensions as te

from rally import exceptions
from rally.common.plugin import plugin
from rally.task import context
from rally.task import scenario
from rally.task import types
from tests.unit import test


class Color(enum.Enum):
    RED = "red"
    BLUE = "blue"


class ScenarioConfigureTestCase(test.TestCase):

    def test_configure(self):

        @scenario.configure(name="fooscenario.name", platform="testing")
        class SomeScenario(scenario.Scenario):
            def run(self):
                pass

        self.assertEqual("fooscenario.name", SomeScenario.get_name())
        self.assertEqual("testing", SomeScenario.get_platform())
        SomeScenario.unregister()

    def test_schema_from_annotations(self):
        # One fat run() signature exercises the whole annotation -> jsonschema
        # matrix in a single assertion: scalars and Field constraints,
        # Literal/Enum, Optional/union nullability, parameterized containers
        # and TypedDict objects. Documented params carry their doc text as the
        # property description.
        #
        # The args are deliberately required (no ``= None`` defaults): on
        # Python <= 3.10 get_type_hints() wraps a None-defaulted annotation in
        # Optional, which would make the derived schema nullable there but not
        # on 3.11+.
        class OpenSpec(t.TypedDict):                  # total -> name required
            name: str
            count: te.NotRequired[int]

        class ClosedSpec(te.TypedDict, closed=True):  # no extra keys
            name: str

        class GuardedSpec(t.TypedDict):               # open, one key forbidden
            name: str
            admin_pass: te.NotRequired[te.Never]

        @scenario.configure(name="fooscenario.fat")
        class FatScenario(scenario.Scenario):
            def run(
                self,
                a_int: int,
                a_float: float,
                a_min: t.Annotated[int, scenario.Field(ge=1)],
                a_rng: t.Annotated[float, scenario.Field(ge=0, le=1)],
                a_gt: t.Annotated[int, scenario.Field(gt=0, lt=9)],
                a_str: t.Annotated[str, scenario.Field(pattern="a.*")],
                a_bool: bool,
                a_list: list,
                a_dict: dict,
                a_lit: t.Literal["l2", "l3"],
                a_enum: Color,
                a_opt: t.Annotated[int, scenario.Field(ge=1)] | None,
                a_opt604: int | None,          # PEP 604 nullable
                a_optU: t.Optional[str],       # typing.Optional
                tags: list[str],
                counts: dict[str, int],
                anything: list[t.Any],         # list[Any] stays open
                size: int | dict[str, int],    # union w/ keyword member
                flag: bool | str | None,       # union of plain scalars
                a_open: OpenSpec,
                a_closed: ClosedSpec,
                a_guarded: GuardedSpec,
                a_plain,                       # unannotated -> skipped
                a_any: t.Any,                  # typing.Any -> skipped
                **kwargs                       # -> extra args ok
            ):
                """Boot it.

                :param a_int: an int
                :param a_str: a string
                """

        self.addCleanup(FatScenario.unregister)
        schema = FatScenario.get_info()["schema"]
        # **kwargs -> the object accepts arguments beyond those declared
        self.assertTrue(schema["additionalProperties"])
        # the docstring text rides on the property as its description
        self.assertIn("an int", schema["properties"]["a_int"]["description"])
        # compare the type constraints with any description stripped off
        constraints = {n: {k: v for k, v in p.items() if k != "description"}
                       for n, p in schema["properties"].items()}
        self.assertEqual(
            {"a_int": {"type": "integer"},
             "a_float": {"type": "number"},
             "a_min": {"type": "integer", "minimum": 1},
             "a_rng": {"type": "number", "minimum": 0, "maximum": 1},
             "a_gt": {"type": "integer",
                      "exclusiveMinimum": 0, "exclusiveMaximum": 9},
             "a_str": {"type": "string", "pattern": "a.*"},
             "a_bool": {"type": "boolean"},
             "a_list": {"type": "array"},
             "a_dict": {"type": "object"},
             "a_lit": {"enum": ["l2", "l3"]},
             "a_enum": {"enum": ["red", "blue"]},
             "a_opt": {"type": ["integer", "null"], "minimum": 1},
             "a_opt604": {"type": ["integer", "null"]},
             "a_optU": {"type": ["string", "null"]},
             "tags": {"type": "array", "items": {"type": "string"}},
             "counts": {"type": "object",
                        "additionalProperties": {"type": "integer"}},
             "anything": {"type": "array"},
             "size": {"anyOf": [
                 {"type": "integer"},
                 {"type": "object",
                  "additionalProperties": {"type": "integer"}}]},
             "flag": {"type": ["boolean", "string", "null"]},
             "a_open": {"type": "object", "required": ["name"],
                        "additionalProperties": True,
                        "properties": {"name": {"type": "string"},
                                       "count": {"type": "integer"}}},
             "a_closed": {"type": "object", "additionalProperties": False,
                          "required": ["name"],
                          "properties": {"name": {"type": "string"}}},
             "a_guarded": {"type": "object", "required": ["name"],
                           "additionalProperties": True,
                           "properties": {"name": {"type": "string"},
                                          "admin_pass": False}}},
            constraints)
        # unannotated and typing.Any args are simply skipped
        self.assertNotIn("a_plain", constraints)
        self.assertNotIn("a_any", constraints)

        # Without **kwargs the object is closed, and info["parameters"] stays
        # plain (no derived "type") for backward compatibility.
        @scenario.configure(name="fooscenario.closed")
        class ClosedScenario(scenario.Scenario):
            def run(self, count: int):
                """Do it.

                :param count: how many
                """

        self.addCleanup(ClosedScenario.unregister)
        info = ClosedScenario.get_info()
        self.assertFalse(info["schema"]["additionalProperties"])
        params = {p["name"]: p for p in info["parameters"]}
        self.assertNotIn("type", params["count"])

    def test_annotation_warnings(self):
        # Odd annotations degrade gracefully by default and escalate under
        # [DEFAULT]strict_type_annotations.

        # A hint that does not resolve at runtime (a forward ref to an
        # undefined name) must not break get_info(): the whole run() falls
        # back to description-only properties instead of raising.
        @scenario.configure(name="fooscenario.badann")
        class BadAnn(scenario.Scenario):
            def run(self, x: "Nope" = None, y: int = 1):  # noqa: F821
                """Do it.

                :param x: ex
                :param y: why
                """

        self.addCleanup(BadAnn.unregister)
        props = BadAnn.get_info()["schema"]["properties"]  # must not raise
        self.assertNotIn("type", props["x"])  # unresolved -> unconstrained
        self.assertNotIn("type", props["y"])  # get_type_hints failed for run()
        self.assertIn("ex", props["x"]["description"])

        # A :param that names no real run() argument is still surfaced in the
        # schema (so the docs keep it) but logs a warning.
        @scenario.configure(name="fooscenario.ghostdoc")
        class Ghost(scenario.Scenario):
            def run(self, real):
                """Do it.

                :param real: a real argument
                :param ghost: not a run() argument
                """

        self.addCleanup(Ghost.unregister)
        with mock.patch.object(scenario.LOG, "warning") as m_warn:
            self.assertIn("ghost", Ghost.get_info()["schema"]["properties"])
        m_warn.assert_called_once()
        self.assertIn("ghost", m_warn.call_args[0][0])

        # An unmappable annotation (here bytes) is treated as Any and warns.
        @scenario.configure(name="fooscenario.badtype")
        class BadType(scenario.Scenario):
            def run(self, ok: int, weird: bytes = b""):
                """Do it.

                :param ok: fine
                :param weird: unsupported
                """

        self.addCleanup(BadType.unregister)
        with mock.patch.object(scenario.LOG, "warning") as m_warn:
            props = BadType.get_info()["schema"]["properties"]
        self.assertEqual("integer", props["ok"]["type"])
        self.assertNotIn("type", props["weird"])  # Any
        m_warn.assert_called_once()
        self.assertIn("weird", m_warn.call_args[0][0])

        # Strict mode turns the warn-cases above into hard errors.
        opt = "strict_type_annotations"
        scenario.CONF.set_override(opt, True)
        self.addCleanup(scenario.CONF.clear_override, opt)
        self.assertRaises(exceptions.InvalidScenarioArgument, Ghost.get_info)
        self.assertRaises(exceptions.InvalidScenarioArgument, BadType.get_info)
        self.assertRaises(exceptions.InvalidScenarioArgument, BadAnn.get_info)

    def test_get_title_skips_schema_build(self):
        @scenario.configure(name="fooscenario.titled")
        class TitledScenario(scenario.Scenario):
            def run(self, count: t.Annotated[int, scenario.Field(ge=1)] = 1):
                """My title.

                :param count: how many
                """

        self.addCleanup(TitledScenario.unregister)
        # get_title must not trigger the (potentially costly) schema build
        with mock.patch.object(
                TitledScenario, "_arg_property_schemas") as m_build:
            self.assertEqual("My title.", TitledScenario.get_title())
            m_build.assert_not_called()

    def test_get_info(self):

        @plugin.configure(name="test_struct_conv")
        class StructConv(types.ResourceType):
            def pre_process(
                    self, *, resource_spec: str | dict, config, output_type
            ):
                return resource_spec

        # a converter that does not declare CONFIG_SCHEMA inherits the
        # permissive default ({}) -> the argument is in the schema but carries
        # no type constraint (rendered as "Any").
        @plugin.configure(name="test_any_conv")
        class AnyConv(types.ResourceType):
            def pre_process(self, *, resource_spec, config, output_type):
                return resource_spec

        @types.convert(
            spec={"type": "test_struct_conv"},
            thing={"type": "test_any_conv"},
            path={"type": "no_such_resource_type"},
        )
        @scenario.configure(name="fooscenario.conv")
        class ConvScenario(scenario.Scenario):
            def run(self, spec, thing, path):
                """Do it.

                :param spec: a structured converted arg
                :param thing: a thing
                :param path: a path
                """

        self.addCleanup(AnyConv.unregister)
        self.addCleanup(ConvScenario.unregister)
        self.addCleanup(StructConv.unregister)


        props = ConvScenario.get_info()["schema"]["properties"]

        self.assertDictEqual(
            {
                "description": "a structured converted arg\n",
                "type": ["string", "object"]
            },
            props["spec"]
        )
        self.assertDictEqual(
            # converter without declared type is fine
            {"description": "a thing\n"},
            props["thing"]
        )
        self.assertDictEqual(
            # unknown converter should not result in scenario get_info failure
            {"description": "a path"},
            props["path"]
        )


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
