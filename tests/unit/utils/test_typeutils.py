# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import enum
import typing as t

import typing_extensions as te

from rally.common import logging
from rally.utils import typeutils
from tests.unit import test


class Color(enum.Enum):
    RED = "red"
    BLUE = "blue"


def _make_widget(name: str, size: int = 1, tag: t.Any = None) -> None:
    pass


class HintToSchemaTestCase(test.TestCase):

    def test_scalar(self):
        self.assertEqual({"type": "integer"}, typeutils.hint_to_schema(int))

    def test_container(self):
        self.assertEqual({"type": "array", "items": {"type": "string"}},
                         typeutils.hint_to_schema(list[str]))

    def test_any_is_unconstrained(self):
        self.assertEqual({}, typeutils.hint_to_schema(t.Any))

    def test_unsupported_raises(self):
        self.assertRaises(typeutils.UnsupportedType,
                          typeutils.hint_to_schema, bytes)

    def test_field_constraints_and_description(self):
        hint = t.Annotated[int, typeutils.Field(ge=1, description="how many")]
        self.assertEqual(
            {"type": "integer", "minimum": 1, "description": "how many"},
            typeutils.hint_to_schema(hint))

    def test_annotated_ignores_non_field_metadata(self):
        self.assertEqual(
            {"type": "integer"},
            typeutils.hint_to_schema(t.Annotated[int, "just a note"]))

    def test_annotated_any_inner_keeps_field(self):
        # an ``Any`` base is unconstrained ({}); a Field still merges on top
        hint = t.Annotated[t.Any, typeutils.Field(ge=1)]
        self.assertEqual({"minimum": 1}, typeutils.hint_to_schema(hint))

    def test_literal_and_enum(self):
        self.assertEqual({"enum": ["a", "b"]},
                         typeutils.hint_to_schema(t.Literal["a", "b"]))
        self.assertEqual({"enum": ["red", "blue"]},
                         typeutils.hint_to_schema(Color))

    def test_optional_scalar(self):
        self.assertEqual({"type": ["string", "null"]},
                         typeutils.hint_to_schema(t.Optional[str]))

    def test_optional_enum_appends_none(self):
        self.assertEqual(
            {"enum": ["a", "b", None]},
            typeutils.hint_to_schema(t.Optional[t.Literal["a", "b"]]))

    def test_union_of_scalars_is_a_type_list(self):
        self.assertEqual(
            {"type": ["boolean", "string", "null"]},
            typeutils.hint_to_schema(bool | str | None))

    def test_union_with_keyword_members_is_anyof(self):
        self.assertEqual(
            {"anyOf": [{"type": "integer"},
                       {"type": "object",
                        "additionalProperties": {"type": "integer"}},
                       {"type": "null"}]},
            typeutils.hint_to_schema(int | dict[str, int] | None))

    def test_union_with_any_member_is_unconstrained(self):
        self.assertEqual({}, typeutils.hint_to_schema(t.Union[int, t.Any]))

    def test_make_nullable_is_idempotent(self):
        # a schema that already admits null, or has no type/anyOf, is unchanged
        type_list = {"type": ["string", "null"]}
        self.assertEqual(type_list, typeutils._make_nullable(type_list))
        any_of = {"anyOf": [{"type": "string"}, {"type": "null"}]}
        self.assertEqual(any_of, typeutils._make_nullable(any_of))
        self.assertEqual({}, typeutils._make_nullable({}))

    def test_homogeneous_tuple(self):
        self.assertEqual({"type": "array", "items": {"type": "integer"}},
                         typeutils.hint_to_schema(tuple[int, ...]))

    def test_dict_value_type(self):
        self.assertEqual(
            {"type": "object", "additionalProperties": {"type": "integer"}},
            typeutils.hint_to_schema(dict[str, int]))

    def test_typeddict_required_and_forbidden(self):
        class Spec(te.TypedDict, closed=True):
            name: str
            count: te.NotRequired[int]
            secret: te.NotRequired[te.Never]

        self.assertEqual(
            {"type": "object", "additionalProperties": False,
             "required": ["name"],
             "properties": {"name": {"type": "string"},
                            "count": {"type": "integer"},
                            "secret": False}},
            typeutils.hint_to_schema(Spec))

    def test_typeddict_total_false_with_required_field(self):
        class Spec(te.TypedDict, total=False):
            a: te.Required[int]
            b: str

        self.assertEqual(
            {"type": "object", "additionalProperties": True,
             "required": ["a"],
             "properties": {"a": {"type": "integer"},
                            "b": {"type": "string"}}},
            typeutils.hint_to_schema(Spec))


class ArgsOfTestCase(test.TestCase):

    def test_signature_becomes_object_schema(self):
        hint = t.Annotated[dict[str, t.Any], typeutils.ArgsOf(_make_widget)]
        self.assertEqual(
            {"type": "object", "additionalProperties": False,
             "required": ["name"],
             "properties": {"name": {"type": "string"},
                            "size": {"type": "integer"},
                            "tag": {}}},
            typeutils.hint_to_schema(hint))

    def test_ignore_drops_parameters(self):
        hint = t.Annotated[dict[str, t.Any],
                           typeutils.ArgsOf(_make_widget, ignore=("size",
                                                                  "tag"))]
        self.assertEqual(
            {"type": "object", "additionalProperties": False,
             "required": ["name"],
             "properties": {"name": {"type": "string"}}},
            typeutils.hint_to_schema(hint))

    def test_ignore_accepts_a_bare_string(self):
        marker = typeutils.ArgsOf(_make_widget, ignore="tag")
        self.assertEqual(("tag",), marker.ignore)
        hint = t.Annotated[dict[str, t.Any], marker]
        self.assertNotIn("tag", typeutils.hint_to_schema(hint)["properties"])

    def test_var_keyword_allows_extra_keys(self):
        def target(name: str, **extra: t.Any) -> None:
            pass

        hint = t.Annotated[dict[str, t.Any],
                           typeutils.ArgsOf(target)]
        self.assertEqual(
            {"type": "object", "additionalProperties": True,
             "required": ["name"],
             "properties": {"name": {"type": "string"}}},
            typeutils.hint_to_schema(hint))

    def test_field_description_merges_on_top(self):
        hint = t.Annotated[dict[str, t.Any],
                           typeutils.ArgsOf(_make_widget, ignore=("size",
                                                                  "tag")),
                           typeutils.Field(description="the widget")]
        self.assertEqual(
            {"type": "object", "additionalProperties": False,
             "required": ["name"],
             "properties": {"name": {"type": "string"}},
             "description": "the widget"},
            typeutils.hint_to_schema(hint))

    def test_unknown_ignore_name_raises(self):
        hint = t.Annotated[dict[str, t.Any],
                           typeutils.ArgsOf(_make_widget, ignore=("nope",))]
        e = self.assertRaises(TypeError, typeutils.hint_to_schema, hint)
        self.assertIn("nope", str(e))


class ArgumentsSchemaTestCase(test.TestCase):

    def test_skips_self_varargs_and_flags_kwargs(self):
        def target(self, a: str, b=2, *args, **kw) -> None:
            pass

        schema, _sig, _hints = typeutils.arguments_schema(target)
        # self/*args dropped; **kw -> additional; b untyped -> {}; a required
        self.assertTrue(schema["additionalProperties"])
        self.assertEqual({"a": {"type": "string"}, "b": {}},
                         schema["properties"])
        self.assertEqual(["a"], schema["required"])

    def test_returns_schema_signature_and_hints(self):
        schema, signature, hints = typeutils.arguments_schema(_make_widget)
        self.assertEqual(
            {"type": "object", "additionalProperties": False,
             "required": ["name"],
             "properties": {"name": {"type": "string"},
                            "size": {"type": "integer"},
                            "tag": {}}},
            schema)
        self.assertEqual(["name", "size", "tag"],
                         list(signature.parameters))
        self.assertEqual(str, hints["name"])

    def test_bad_ignore_raises(self):
        e = self.assertRaises(TypeError,
                              typeutils.arguments_schema, _make_widget,
                              ignore=("nope",))
        self.assertIn("nope", str(e))

    def test_strict_raises_with_located_hint(self):
        def target(a: int, b: bytes) -> None:  # bytes is unmappable
            pass

        e = self.assertRaises(typeutils.UnsupportedType,
                              typeutils.arguments_schema, target)
        self.assertEqual(("b",), e.location)
        self.assertIn("bytes", str(e))

    def test_nested_error_builds_a_location_path(self):
        # an unmappable param of a forwarded ArgsOf callable is located through
        # the nesting: the dict argument, then the offending key (which is the
        # forwarded callable's parameter).
        def make_thing(good: int, bad: bytes) -> None:
            pass

        def outer(
            create_args: t.Annotated[dict[str, t.Any],
                                     typeutils.ArgsOf(make_thing)],
        ) -> None:
            pass

        e = self.assertRaises(typeutils.UnsupportedType,
                              typeutils.arguments_schema, outer)
        self.assertEqual(("create_args", "bad"), e.location)

    def test_non_strict_degrades_to_empty(self):
        def target(a: int, b: bytes) -> None:
            pass

        with logging.LogCatcher(typeutils.LOG) as catcher:
            schema, _sig, _hints = typeutils.arguments_schema(
                target, strict=False)
        self.assertEqual({"type": "integer"}, schema["properties"]["a"])
        self.assertEqual({}, schema["properties"]["b"])  # unmappable -> {}
        catcher.assertInLogs("at b")


class FieldTestCase(test.TestCase):

    def test_as_schema_only_set_keys(self):
        self.assertEqual({"pattern": "a.*"},
                         typeutils.Field(pattern="a.*").as_schema())

    def test_as_schema_empty(self):
        self.assertEqual({}, typeutils.Field().as_schema())
