# Copyright (C) 2014 Yahoo! Inc. All Rights Reserved.
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

import copy
import pickle
import typing as t
from unittest import mock

import typing_extensions as te

from rally import exceptions
from rally.common.plugin import plugin
from rally.task import scenario
from rally.task import types
from tests.unit import test


class _FakeSelector(types.DeferredResource):
    """Module-level (pick-able) deferred resource for tests.

    Holds an already-shaped value; ``resolve`` only selects it.
    """

    def __init__(self, value):
        self.value = value

    def resolve(self, scenario):
        return self.value


class ConvertTestCase(test.TestCase):

    # NOTE(stpierre): These cases test types.convert(),
    # types._get_preprocessor_loader(), and bits of
    # types.preprocess(). This may not look very elegant, but it's the
    # easiest way to test both convert() and
    # _get_preprocessor_loader() without getting so fine-grained that
    # the tests are basically tests that the computer is on.

    def setUp(self):
        super(ConvertTestCase, self).setUp()

        @types.convert(bar={"type": "test_bar"})
        @scenario.configure(name="FakeConvertPlugin.one_arg")
        class FakeConvertOneArgPlugin(scenario.Scenario):
            def run(self, bar):
                """Dummy docstring.

                :param bar: dummy parameter
                """
                pass

        self.addCleanup(FakeConvertOneArgPlugin.unregister)

        @types.convert(bar={"type": "test_bar"},
                       baz={"type": "test_baz"})
        @scenario.configure(name="FakeConvertPlugin.two_args")
        class FakeConvertTwoArgsPlugin(scenario.Scenario):

            def run(self, bar, baz):
                """Dummy docstring.

                :param bar: dummy parameter
                :param baz: dummy parameter
                """
                pass

        self.addCleanup(FakeConvertTwoArgsPlugin.unregister)

    @mock.patch("rally.task.types.ResourceType.get", create=True)
    def test_convert(self, mock_resource_type_get):
        ctx = mock.MagicMock()
        args = types.preprocess("FakeConvertPlugin.one_arg",
                                ctx,
                                {"bar": "bar_config"})
        mock_resource_type_get.assert_called_once_with("test_bar")
        resourcetype_cls = mock_resource_type_get.return_value
        resourcetype_cls.assert_called_once_with(ctx, {})
        resourcetype_obj = resourcetype_cls.return_value
        resourcetype_obj.pre_process.assert_called_once_with(
            "bar_config", {"type": "test_bar"})
        self.assertDictEqual(
            args, {"bar": resourcetype_obj.pre_process.return_value})

    @mock.patch("rally.task.types.ResourceType.get", create=True)
    def test_convert_multiple(self, mock_resource_type_get):
        resourcetype_classes = {"bar": mock.Mock(), "baz": mock.Mock()}

        def _get_resource_type(name):
            # cut "test_" prefix
            name = name[5:]
            if name in resourcetype_classes:
                return resourcetype_classes[name]
            self.fail("The unexpected resource class tried to be used.")

        mock_resource_type_get.side_effect = _get_resource_type

        ctx = mock.MagicMock()
        scenario_args = {"bar": "bar_config", "baz": "baz_config"}
        processed_args = types.preprocess(
            "FakeConvertPlugin.two_args", ctx, scenario_args)

        mock_resource_type_get.assert_has_calls([mock.call("test_bar"),
                                                 mock.call("test_baz")],
                                                any_order=True)

        expected_dict = {}
        for resourcetype_n, resourcetype_cls in resourcetype_classes.items():
            resourcetype_cls.assert_called_once_with(ctx, {})
            resourcetype_obj = resourcetype_cls.return_value
            resourcetype_obj.pre_process.assert_called_once_with(
                scenario_args[resourcetype_n],
                {"type": "test_%s" % resourcetype_n})
            return_value = resourcetype_obj.pre_process.return_value
            expected_dict[resourcetype_n] = return_value

        self.assertDictEqual(expected_dict, processed_args)

    def test_convert_annotation(self):
        from rally.common.plugin import plugin

        class ImageSpec(te.TypedDict, closed=True):
            id: te.NotRequired[str]

        @plugin.configure(name="test_cm")
        class Conv(types.ResourceType):
            def pre_process(
                self, *, resource_spec: ImageSpec, config, output_type
            ):
                return resource_spec

        @scenario.configure(name="fooscenario.convmarker")
        class S(scenario.Scenario):
            def run(
                self, image: t.Annotated[str, types.Convert("test_cm")]
            ):
                """Do it.

                :param image: the image
                """

        self.addCleanup(S.unregister)
        self.addCleanup(Conv.unregister)

        # the converter is discovered from the annotation (no decorator)
        self.assertEqual(
            {"image": {"type": "test_cm"}},
            types.collect_scenario_args_preprocessors(
                S, t.get_type_hints(S.run, include_extras=True))
        )
        # ... and its resource_spec annotation drives the argument schema
        image = S.get_info()["schema"]["properties"]["image"]
        self.assertEqual(
            {"type": "object", "additionalProperties": False,
             "properties": {"id": {"type": "string"}}},
            {k: v for k, v in image.items() if k != "description"})


class ConfigSchemaTestCase(test.TestCase):

    def test_derived_from_resource_spec(self):
        @plugin.configure(name="test_cfg_schema")
        class RT(types.ResourceType):
            def pre_process(
                self, *, resource_spec: list[str], config, output_type
            ):
                return resource_spec

        self.addCleanup(RT.unregister)
        self.assertEqual(
            {"type": "array", "items": {"type": "string"}},
            types._compose_jsonschema(RT))

    def test_unannotated_is_unconstrained(self):
        @plugin.configure(name="test_cfg_any")
        class RT(types.ResourceType):
            def pre_process(self, *, resource_spec, config, output_type):
                return resource_spec

        self.addCleanup(RT.unregister)
        self.assertEqual({}, types._compose_jsonschema(RT))

    def test_full_signature_derives_schema(self):
        # the extra output_type parameter does not obscure the resource_spec
        # schema.
        @plugin.configure(name="test_cfg_ng")
        class RT(types.ResourceType):
            def pre_process(self, resource_spec: str, config, *, output_type):
                return resource_spec

        self.addCleanup(RT.unregister)
        self.assertEqual({"type": "string"}, types._compose_jsonschema(RT))

    def test_unresolvable_warns_then_raises_under_strict(self):
        @plugin.configure(name="test_cfg_bad")
        class RT(types.ResourceType):
            def pre_process(
                self, *, resource_spec: "Nope",  # noqa: F821
                config, output_type,
            ):
                return resource_spec

        self.addCleanup(RT.unregister)

        # by default an unresolvable annotation degrades to unconstrained
        with mock.patch.object(types.LOG, "warning") as m_warn:
            self.assertEqual({}, types._compose_jsonschema(RT))
        m_warn.assert_called_once()

        # ... and becomes a hard error under strict_type_annotations
        opt = "strict_type_annotations"
        types.CONF.set_override(opt, True)
        self.addCleanup(types.CONF.clear_override, opt)
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types._compose_jsonschema, RT)

    def test_convert_marker_type_cfg(self):
        self.assertEqual({"type": "glance_image"},
                         types.Convert("glance_image").type_cfg)
        # extra kwargs are forwarded (mirrors the @types.convert dict)
        self.assertEqual(
            {"type": "glance_image", "list_kwargs": {"x": 1}},
            types.Convert("glance_image", list_kwargs={"x": 1}).type_cfg)


class LegacyDetectionTestCase(test.TestCase):

    def test_preprocess_detects_and_warns_legacy(self):
        # a legacy (2-arg pre_process) converter is auto-detected: it is called
        # with the legacy signature, and a deprecation warning is logged.
        @plugin.configure(name="test_leg_warn")
        class Leg(types.ResourceType):
            def pre_process(self, resource_spec, config):
                return resource_spec * 2

        self.addCleanup(Leg.unregister)

        @scenario.configure(name="Dummy.leg")
        class S(scenario.Scenario):
            def run(self, a: t.Annotated[int, types.Convert("test_leg_warn")]):
                pass

        self.addCleanup(S.unregister)

        with mock.patch.object(types.LOG, "warning") as m_warn:
            result = types.preprocess("Dummy.leg", {}, {"a": 5})
        self.assertEqual({"a": 10}, result)
        m_warn.assert_called_once()
        self.assertIn("deprecated", m_warn.call_args[0][0])


class PreprocessTestCase(test.TestCase):

    def test_preprocess(self):

        scenario_name = f"Dummy.{self.id()}"
        type_name = f"{self.id()}_type"

        context = {
            "a": 1,
            "b": 2,
        }
        args = {"a": 10, "b": 20}

        @scenario.configure(name=scenario_name)
        class S(scenario.Scenario):
            def run(
                self, a: t.Annotated[int, types.Convert(type_name)], b: int
            ):
                pass

        self.addCleanup(S.unregister)

        @plugin.configure(type_name)
        class SomeType(types.ResourceType):

            def pre_process(self, *, resource_spec, config, output_type):
                return resource_spec * 2

        self.addCleanup(SomeType.unregister)

        result = types.preprocess(scenario_name, context, args)
        self.assertEqual({"a": 20, "b": 20}, result)

    def test_preprocess_unresolvable_run_hints(self):
        # a run() annotation that fails to resolve does not break preprocess;
        # decorator-bound converters still run.
        @plugin.configure(name="test_dbl")
        class Dbl(types.ResourceType):
            def pre_process(self, *, resource_spec, config, output_type):
                return resource_spec * 2

        self.addCleanup(Dbl.unregister)

        @types.convert(a={"type": "test_dbl"})
        @scenario.configure(name="Dummy.badhint")
        class S(scenario.Scenario):
            def run(self, a, b: "Undefined" = None):  # noqa: F821
                pass

        self.addCleanup(S.unregister)

        self.assertEqual({"a": 10},
                         types.preprocess("Dummy.badhint", {}, {"a": 5}))

    def test_preprocess_init_failure_raises_rally_exception(self):
        @plugin.configure(name="test_badinit")
        class Bad(types.ResourceType):
            def __init__(self, *args, **kwargs):
                raise ValueError("boom")

            def pre_process(self, *, resource_spec, config, output_type):
                return resource_spec

        self.addCleanup(Bad.unregister)

        @types.convert(a={"type": "test_badinit"})
        @scenario.configure(name="Dummy.badinit")
        class S(scenario.Scenario):
            def run(self, a):
                pass

        self.addCleanup(S.unregister)

        self.assertRaises(exceptions.RallyException,
                          types.preprocess, "Dummy.badinit", {}, {"a": 1})

    def test_preprocess_modern_present(self):
        # a modern resource type (pre_process takes output_type) receives the
        # argument's annotation base type as output_type and can read the
        # running scenario class from self._scenario_cls.
        seen = {}

        @plugin.configure(name="test_ng")
        class NG(types.ResourceType):
            def pre_process(self, resource_spec, config, *, output_type):
                seen.update(spec=resource_spec, cls=self._scenario_cls,
                            out=output_type)
                return "resolved:%s" % resource_spec

        self.addCleanup(NG.unregister)

        @scenario.configure(name="Dummy.ng")
        class S(scenario.Scenario):
            def run(self, image: t.Annotated[list, types.Convert("test_ng")]):
                """Do it.

                :param image: the image
                """

        self.addCleanup(S.unregister)

        result = types.preprocess("Dummy.ng", {}, {"image": "x"})
        self.assertEqual("resolved:x", result["image"])
        self.assertEqual("x", seen["spec"])
        self.assertIs(S, seen["cls"])       # running scenario class
        self.assertIs(list, seen["out"])    # annotation base type

    def test_preprocess_skips_absent_args(self):
        # neither a legacy nor a modern converter is called for an argument
        # absent from the task; the argument stays absent.
        calls = []

        @plugin.configure(name="test_ng_abs")
        class NG(types.ResourceType):
            def pre_process(self, resource_spec, config, *, output_type):
                calls.append(("ng", resource_spec))
                return resource_spec

        self.addCleanup(NG.unregister)

        @plugin.configure(name="test_legacy_abs")
        class Legacy(types.ResourceType):
            def pre_process(self, resource_spec, config):
                calls.append(("leg", resource_spec))
                return resource_spec

        self.addCleanup(Legacy.unregister)

        @types.convert(ng={"type": "test_ng_abs"},
                       leg={"type": "test_legacy_abs"})
        @scenario.configure(name="Dummy.ng_absent")
        class S(scenario.Scenario):
            def run(self, ng=None, leg=None):
                """Do it.

                :param ng: a
                :param leg: b
                """

        self.addCleanup(S.unregister)

        result = types.preprocess("Dummy.ng_absent", {}, {})  # both absent
        self.assertEqual([], calls)      # neither converter called
        self.assertEqual({}, result)     # both args stay absent

    def test_preprocess_returns_deferred_unresolved(self):
        # a returned DeferredResource is left unresolved by preprocess and must
        # survive the per-iteration deepcopy and the process-boundary pickle.
        # The shape decision (from output_type) is baked in here, at
        # pre_process time; the wrapper carries the already-shaped value.
        @plugin.configure(name="test_deferred")
        class Def(types.ResourceType):
            def pre_process(self, resource_spec, config, *, output_type):
                value = (resource_spec if output_type is str
                         else [resource_spec])
                return _FakeSelector(value)

        self.addCleanup(Def.unregister)

        @scenario.configure(name="Dummy.deferred")
        class S(scenario.Scenario):
            def run(self,
                    image: t.Annotated[str, types.Convert("test_deferred")]):
                """Do it.

                :param image: the image
                """

        self.addCleanup(S.unregister)

        result = types.preprocess("Dummy.deferred", {}, {"image": "x"})
        wrapper = result["image"]
        self.assertIsInstance(wrapper, types.DeferredResource)  # unresolved
        self.assertEqual("x", wrapper.value)  # shaped for the str annotation
        copy.deepcopy(wrapper)              # per-iteration isolation
        pickle.loads(pickle.dumps(wrapper))  # crosses the process boundary
