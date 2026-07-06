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

from __future__ import annotations

import dataclasses
import enum
import types
import typing as t

import typing_extensions as te


@dataclasses.dataclass(frozen=True)
class Field:
    """Constraints for an annotated argument.

    A small ``pydantic.Field``-like subset, used as ``typing.Annotated``
    metadata and mapped to jsonschema keywords::

        size: typing.Annotated[int, Field(ge=1, le=10)] = 1
    """
    _: dataclasses.KW_ONLY
    ge: float | None = None          # >=  -> minimum
    gt: float | None = None          # >   -> exclusiveMinimum
    le: float | None = None          # <=  -> maximum
    lt: float | None = None          # <   -> exclusiveMaximum
    min_length: int | None = None    # -> minLength
    max_length: int | None = None    # -> maxLength
    pattern: str | None = None       # -> pattern
    description: str | None = None    # -> description

    # field attribute -> jsonschema keyword
    _SCHEMA_KEYS: t.ClassVar[dict[str, str]] = {
        "ge": "minimum",
        "gt": "exclusiveMinimum",
        "le": "maximum",
        "lt": "exclusiveMaximum",
        "min_length": "minLength",
        "max_length": "maxLength",
        "pattern": "pattern",
        "description": "description"
    }

    def as_schema(self) -> dict[str, t.Any]:
        """The jsonschema keywords for the constraints that are set."""
        return {key: getattr(self, attr)
                for attr, key in self._SCHEMA_KEYS.items()
                if getattr(self, attr) is not None}


class UnsupportedType(Exception):
    """A type hint :func:`hint_to_schema` cannot map to a JSON Schema."""

    def __init__(self, hint: t.Any) -> None:
        self.hint = hint
        super().__init__(repr(hint))


def _make_nullable(schema: dict[str, t.Any]) -> dict[str, t.Any]:
    """Allow ``None`` in a property schema (for ``Optional`` / ``| None``)."""
    if "enum" in schema:
        return (schema if None in schema["enum"]
                else {**schema, "enum": [*schema["enum"], None]})
    if "type" in schema:
        types_ = schema["type"]
        if isinstance(types_, list):
            if "null" in types_:
                return schema
            else:
                return {**schema, "type": [*types_, "null"]}
        return {**schema, "type": [types_, "null"]}
    if "anyOf" in schema:
        if any(m.get("type") == "null" for m in schema["anyOf"]):
            return schema
        else:
            return {**schema, "anyOf": [*schema["anyOf"], {"type": "null"}]}
    return schema


def _sequence_item(container: t.Any, args: tuple[t.Any, ...]) -> t.Any:
    """The single element type of a homogeneous sequence hint, else None.

    ``list[X]``/``set[X]``/``frozenset[X]`` and ``tuple[X, ...]`` -> ``X``; a
    fixed heterogeneous ``tuple[X, Y]`` has no single element -> None.
    """
    if not args:
        return None
    if container is tuple:
        return args[0] if len(args) == 2 and args[1] is Ellipsis else None
    return args[0]


def hint_to_schema(hint: t.Any) -> dict[str, t.Any] | None:
    """Convert a Python type hint into a jsonschema property.

    Returns None when the value is intentionally unconstrained (``typing.Any``
    or a multi-type union), and raises :class:`UnsupportedType` for a type
    that cannot be mapped at all. Supports plain scalars/containers,
    ``Optional``/``| None``, ``enum.Enum``/``typing.Literal`` and
    ``typing.Annotated[T, Field(...)]``.
    """
    if hint is t.Any:
        return None

    origin = t.get_origin(hint)

    # Union: map every non-``None`` member and combine into a single ``type``
    # list when they are all plain scalars, otherwise ``anyOf``. ``None`` (from
    # ``Optional`` / ``| None``) applies on top as nullability. Any Annotated
    # metadata nests *inside* the Union, so recursion handles it.
    # Accepts both ``typing.Union``/``Optional`` and PEP 604 ``X | Y``.
    if origin is t.Union or origin is types.UnionType:
        args = t.get_args(hint)
        raw = [hint_to_schema(a) for a in args if a is not type(None)]
        parts = [m for m in raw if m is not None]
        if len(parts) != len(raw):
            return None  # an ``Any`` member -> whole union unconstrained
        if len(parts) == 1:
            schema = parts[0]
        elif all(set(m) == {"type"} and isinstance(m["type"], str)
                 for m in parts):
            schema = {"type": [m["type"] for m in parts]}
        else:
            schema = {"anyOf": parts}
        return _make_nullable(schema) if type(None) in args else schema

    # ``Annotated[T, Field(...)]``
    if hasattr(hint, "__metadata__"):
        schema = hint_to_schema(t.get_args(hint)[0])
        if schema is None:
            return None
        for meta in hint.__metadata__:
            if isinstance(meta, Field):
                schema = {**schema, **meta.as_schema()}
        return schema

    # ``typing.Literal[...]`` / ``enum.Enum`` -> a fixed set of values
    if origin is t.Literal:
        return {"enum": list(t.get_args(hint))}
    if isinstance(hint, type) and issubclass(hint, enum.Enum):
        return {"enum": [member.value for member in hint]}

    # ``TypedDict`` -> an object schema (``te.is_typeddict`` recognizes both
    # stdlib and ``typing_extensions`` TypedDicts, incl. PEP 728 ``closed=``)
    if te.is_typeddict(hint):
        return _typeddict_object_schema(hint)

    # plain scalars (bool before int: bool is a subclass of int) / containers
    for tp, json_type in ((bool, "boolean"), (int, "integer"),
                          (float, "number"), (str, "string")):
        if hint is tp:
            return {"type": json_type}
    container = origin or hint
    if container in (list, tuple, set, frozenset):
        array_schema: dict[str, t.Any] = {"type": "array"}
        item = _sequence_item(container, t.get_args(hint))
        if item is not None:
            item_schema = hint_to_schema(item)
            if item_schema is not None:  # ``Any`` element -> stay open
                array_schema["items"] = item_schema
        return array_schema
    if container is dict:
        object_schema: dict[str, t.Any] = {"type": "object"}
        dargs = t.get_args(hint)
        if len(dargs) == 2:
            value_schema = hint_to_schema(dargs[1])
            if value_schema is not None:  # ``dict[str, Any]`` stays open
                object_schema["additionalProperties"] = value_schema
        return object_schema
    raise UnsupportedType(hint)


def _typeddict_object_schema(td: type) -> dict[str, t.Any]:
    """Map a ``TypedDict`` to an object jsonschema.

    Every field becomes a property, typed via :func:`hint_to_schema`. A field
    is required unless it is ``NotRequired`` or the whole dict is
    ``total=False``; we read that from the resolved hints rather than
    ``__required_keys__``, which is unreliable under
    ``from __future__ import annotations``. Whether extra keys are allowed is a
    separate question, answered by PEP 728 ``closed=`` (they are, unless
    ``closed=True``). Finally, a ``NotRequired[Never]`` (or plain ``Never``)
    field maps to ``{"<key>": false}``, forbidding that key outright.
    """
    properties: dict[str, t.Any] = {}
    required: list[str] = []
    total = bool(getattr(td, "__total__", True))
    for field, ftype in t.get_type_hints(td, include_extras=True).items():
        is_required = total
        if t.get_origin(ftype) is te.Required:
            is_required, ftype = True, t.get_args(ftype)[0]
        elif t.get_origin(ftype) is te.NotRequired:
            is_required, ftype = False, t.get_args(ftype)[0]
        if ftype is te.Never:
            properties[field] = False  # forbidden: no value is valid
            continue
        schema = hint_to_schema(ftype)
        properties[field] = schema if schema is not None else {}
        if is_required:
            required.append(field)
    result: dict[str, t.Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": not getattr(td, "__closed__", False),
    }
    if required:
        result["required"] = required
    return result
