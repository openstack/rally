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

from rally.utils import typeutils
from tests.unit import test


class Color(enum.Enum):
    RED = "red"
    BLUE = "blue"


class HintToSchemaTestCase(test.TestCase):

    def test_scalar(self):
        self.assertEqual({"type": "integer"}, typeutils.hint_to_schema(int))

    def test_container(self):
        self.assertEqual({"type": "array", "items": {"type": "string"}},
                         typeutils.hint_to_schema(list[str]))

    def test_any_is_unconstrained(self):
        self.assertIsNone(typeutils.hint_to_schema(t.Any))

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

    def test_annotated_any_inner_is_unconstrained(self):
        hint = t.Annotated[t.Any, typeutils.Field(ge=1)]
        self.assertIsNone(typeutils.hint_to_schema(hint))

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
        self.assertIsNone(typeutils.hint_to_schema(t.Union[int, t.Any]))

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


class FieldTestCase(test.TestCase):

    def test_as_schema_only_set_keys(self):
        self.assertEqual({"pattern": "a.*"},
                         typeutils.Field(pattern="a.*").as_schema())

    def test_as_schema_empty(self):
        self.assertEqual({}, typeutils.Field().as_schema())
