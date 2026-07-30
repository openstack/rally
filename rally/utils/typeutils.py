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
import inspect
import types
import typing as t

import typing_extensions as te

from rally.common import logging


LOG = logging.getLogger(__name__)

# default values simple enough to embed verbatim as a JSON Schema ``default``.
# ``None`` is intentionally excluded: a ``None`` default just means the
# argument is optional, which the ``required`` list already conveys.
_JSON_DEFAULT_TYPES = (bool, int, float, str, list, dict)


class UnsupportedType(Exception):
    """Base error for deriving a JSON Schema from annotations/signatures."""

    def __init__(self, detail: str, *, location: t.Sequence[str] = ()) -> None:
        self.detail = detail
        self.location = tuple(location)
        if location:
            detail = f"{detail} (at {' -> '.join(location)})"
        super().__init__(detail)


@dataclasses.dataclass(frozen=True)
class Field:
    """Constraints for an annotated argument.

    A small ``pydantic.Field``-like subset, used as ``typing.Annotated``
    metadata and mapped to jsonschema keywords::

        size: typing.Annotated[int, Field(ge=1, le=10)] = 1
    """

    _: dataclasses.KW_ONLY
    ge: float | None = None  # >=  -> minimum
    gt: float | None = None  # >   -> exclusiveMinimum
    le: float | None = None  # <=  -> maximum
    lt: float | None = None  # <   -> exclusiveMaximum
    min_length: int | None = None  # -> minLength
    max_length: int | None = None  # -> maxLength
    pattern: str | None = None  # -> pattern
    description: str | None = None  # -> description

    # field attribute -> jsonschema keyword
    _SCHEMA_KEYS: t.ClassVar[dict[str, str]] = {
        "ge": "minimum",
        "gt": "exclusiveMinimum",
        "le": "maximum",
        "lt": "exclusiveMaximum",
        "min_length": "minLength",
        "max_length": "maxLength",
        "pattern": "pattern",
        "description": "description",
    }

    def as_schema(self) -> dict[str, t.Any]:
        """The jsonschema keywords for the constraints that are set."""
        return {
            key: getattr(self, attr)
            for attr, key in self._SCHEMA_KEYS.items()
            if getattr(self, attr) is not None
        }


@dataclasses.dataclass(frozen=True)
class ArgsOf:
    """Build an object schema from another callable's signature.

    Used as ``typing.Annotated`` metadata on a ``dict`` argument, so the keys
    a scenario forwards to another callable need not be duplicated::

        args: typing.Annotated[
            dict[str, typing.Any],
            ArgsOf(create_something, ignore=("c",)),
        ]

    Each parameter becomes a property; one without a default is required;
    ``ignore`` drops names; extra keys are allowed only if the callable takes
    ``**kwargs``.
    """

    target: t.Callable[..., t.Any]
    ignore: t.Sequence[str] = ()

    def __post_init__(self) -> None:
        # accept a single name as a bare string for convenience
        if isinstance(self.ignore, str):
            ignore = (self.ignore,)
        else:
            ignore = tuple(self.ignore)
        object.__setattr__(self, "ignore", ignore)


def _make_nullable(schema: dict[str, t.Any]) -> dict[str, t.Any]:
    """Allow ``None`` in a property schema (for ``Optional`` / ``| None``)."""
    if "enum" in schema:
        return (
            schema
            if None in schema["enum"]
            else {**schema, "enum": [*schema["enum"], None]}
        )
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


def _object_schema(
    fields: t.Iterable[tuple[str, t.Any, bool]],
    *,
    additional: bool,
    strict: bool = True,
) -> dict[str, t.Any]:
    """Build an object schema from ``(name, hint, required)`` triples.

    Each hint becomes a property via :func:`hint_to_schema` (an unconstrained
    ``Any`` -> ``{}``); a ``Never`` hint maps to ``{"<name>": false}``,
    forbidding that key outright (and never required). When a field cannot be
    mapped: the error is located under the field name; if ``strict`` it is
    re-raised, otherwise it is logged and the field is left unconstrained
    (``{}``).
    """
    properties: dict[str, t.Any] = {}
    required: list[str] = []
    for name, hint, is_required in fields:
        if hint is te.Never:
            properties[name] = False  # forbidden: no value is valid
            continue
        try:
            schema = hint_to_schema(hint)
        except UnsupportedType as e:
            located = UnsupportedType(e.detail, location=(name, *e.location))
            if strict:
                raise located
            LOG.warning(str(located))
            schema = None
        properties[name] = schema if schema is not None else {}
        if is_required:
            required.append(name)
    result: dict[str, t.Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": additional,
    }
    if required:
        result["required"] = required
    return result


def _typeddict_object_schema(td: type) -> dict[str, t.Any]:
    """Map a ``TypedDict`` to an object jsonschema.

    Every field becomes a property. A field is required unless it is
    ``NotRequired`` or the whole dict is ``total=False``; we read that from the
    resolved hints rather than ``__required_keys__``, which is unreliable under
    ``from __future__ import annotations``. Whether extra keys are allowed is a
    separate question, answered by PEP 728 ``closed=`` (they are, unless
    ``closed=True``).
    """
    fields: list[tuple[str, t.Any, bool]] = []
    total = bool(getattr(td, "__total__", True))
    for field, ftype in t.get_type_hints(td, include_extras=True).items():
        is_required = total
        if t.get_origin(ftype) is te.Required:
            is_required = True
            ftype = t.get_args(ftype)[0]
        elif t.get_origin(ftype) is te.NotRequired:
            is_required = False
            ftype = t.get_args(ftype)[0]
        fields.append((field, ftype, is_required))
    return _object_schema(
        fields, additional=not getattr(td, "__closed__", False)
    )


def hint_to_schema(hint: t.Any) -> dict[str, t.Any]:
    """Convert a Python type hint into a jsonschema property.

    Supports plain scalars/containers, ``Optional``/``| None``,
    ``enum.Enum``/``typing.Literal`` and ``typing.Annotated[T, Field(...)]``.

    :raises UnsupportedType: for a type that cannot be mapped at all
    """
    if hint is t.Any:
        return {}

    origin = t.get_origin(hint)

    # Union: map every non-``None`` member and combine into a single ``type``
    # list when they are all plain scalars, otherwise ``anyOf``. ``None`` (from
    # ``Optional`` / ``| None``) applies on top as nullability. Any Annotated
    # metadata nests *inside* the Union, so recursion handles it.
    # Accepts both ``typing.Union``/``Optional`` and PEP 604 ``X | Y``.
    if origin is t.Union or origin is types.UnionType:
        args = t.get_args(hint)
        parts = [hint_to_schema(a) for a in args if a is not type(None)]
        if any(not part for part in parts):
            return {}  # an unconstrained (``Any``) member -> whole union open
        if len(parts) == 1:
            schema = parts[0]
        elif all(
            set(m) == {"type"} and isinstance(m["type"], str) for m in parts
        ):
            schema = {"type": [m["type"] for m in parts]}
        else:
            schema = {"anyOf": parts}
        return _make_nullable(schema) if type(None) in args else schema

    # ``Annotated[T, Field(...)]`` / ``Annotated[dict, ArgsOf(...)]``. An
    # ``ArgsOf`` replaces the base type's schema (the ``dict`` is only there
    # for linters); a ``Field`` then merges its constraints on top.
    if hasattr(hint, "__metadata__"):
        args_of = next(
            (m for m in hint.__metadata__ if isinstance(m, ArgsOf)), None
        )
        if args_of is not None:
            schema, _signature, _hints = arguments_schema(
                args_of.target, ignore=args_of.ignore
            )
        else:
            schema = hint_to_schema(t.get_args(hint)[0])
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
    for tp, json_type in (
        (bool, "boolean"),
        (int, "integer"),
        (float, "number"),
        (str, "string"),
    ):
        if hint is tp:
            return {"type": json_type}
    container = origin or hint
    if container in (list, tuple, set, frozenset):
        array_schema: dict[str, t.Any] = {"type": "array"}
        item = _sequence_item(container, t.get_args(hint))
        if item is not None:
            item_schema = hint_to_schema(item)
            if item_schema:  # ``Any`` element ({}) -> stay open
                array_schema["items"] = item_schema
        return array_schema
    if container is dict:
        object_schema: dict[str, t.Any] = {"type": "object"}
        dargs = t.get_args(hint)
        if len(dargs) == 2:
            value_schema = hint_to_schema(dargs[1])
            if value_schema:  # ``dict[str, Any]`` ({}) stays open
                object_schema["additionalProperties"] = value_schema
        return object_schema
    raise UnsupportedType(
        f"Cannot map type annotation `{hint!r}` to a JSON Schema"
    )


def arguments_schema(
    target: t.Callable[..., t.Any],
    *,
    target_name: str | None = None,
    ignore: t.Collection[str] = (),
    strict: bool = True,
) -> tuple[dict[str, t.Any], inspect.Signature, dict[str, t.Any]]:
    """Build a complete object schema from a callable's arguments.

    Resolves the callable's ``signature`` and type ``hints`` and returns them
    alongside the schema so a caller can reuse them without resolving twice.
    ``self``/``cls``, ``*args`` are skipped. ``**kwargs`` is treated as
    ``additionalProperties: True``.

    :param target: callable to proceed
    :param target_name: labels the callable in error messages
        (defaults to ``target.__name__``)
    :param ignore: extra parameters to ignore (defaults to ``()``)
    :param strict: raise errors for unresolvable hints instead of warnings
    """
    try:
        signature = inspect.signature(target)
        hints = t.get_type_hints(target, include_extras=True)
    except Exception:
        label = target_name or getattr(target, "__name__", repr(target))
        raise UnsupportedType(f"Failed to resolve type hints for `{label}`.")
    unknown = [n for n in ignore if n not in signature.parameters]
    if unknown and strict:
        raise TypeError(
            f"Ignore list includes unknown parameter(s): {unknown}"
        )

    fields: list[tuple[str, t.Any, bool]] = []
    defaults: dict[str, t.Any] = {}
    additional = False
    for name, param in signature.parameters.items():
        if name in ("self", "cls") or name in ignore:
            continue
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            additional = True  # ``**kwargs`` -> extra keys allowed
            continue
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            continue
        required = param.default is inspect.Parameter.empty
        if not required:
            default = param.default
            if isinstance(default, enum.Enum):
                default = default.value  # an enum default -> its raw value
            if isinstance(default, _JSON_DEFAULT_TYPES):
                defaults[name] = default
        fields.append((name, hints.get(name, t.Any), required))

    schema = _object_schema(fields, additional=additional, strict=strict)
    # overlay defaults onto the derived properties (a signature-only concern,
    # so it lives here rather than in _object_schema)
    for name, default in defaults.items():
        prop = schema["properties"].get(name)
        if isinstance(prop, dict):  # not a forbidden (False) property
            prop["default"] = default
    return schema, signature, hints
