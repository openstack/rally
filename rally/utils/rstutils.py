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

"""Render the reference documentation of plugins as reStructuredText."""

from __future__ import annotations

import dataclasses
import functools
import importlib.metadata
import json
import re
import textwrap
import typing as t

from packaging import version as packaging_version

from rally.common import validation
from rally.common.plugin import info as plugin_info


if t.TYPE_CHECKING:  # pragma: no cover
    from rally.common.plugin import plugin


# values nested deeper than this are not expanded, but dumped as a jsonschema
_MAX_LEVEL = 3

_NESTED_KEYWORDS = (
    "properties",
    "patternProperties",
    "items",
    "oneOf",
    "anyOf",
)

_GROUPS_NOTE = "One of the following groups of parameters should be provided"


@dataclasses.dataclass(frozen=True)
class SourceRepository:
    """A repository that hosts the source code of a python package.

    :param package: the top-level python package, e.g. ``rally_openstack``
    :param url: the repository, e.g. ``https://github.com/openstack/rally``
    :param ref: the branch or the tag to link to
    """

    package: str
    url: str
    ref: str = "master"

    @classmethod
    def from_distribution(
        cls, package: str, url: str, *, distribution: str
    ) -> SourceRepository:
        """Point to the release of the installed distribution.

        A final release is linked by its tag. A development build, a
        pre-release, a version that does not follow PEP 440 or a distribution
        that is not installed is linked by the ``master`` branch.
        """
        try:
            version = importlib.metadata.version(distribution)
            parsed = packaging_version.Version(version)
        except (
            importlib.metadata.PackageNotFoundError,
            packaging_version.InvalidVersion,
        ):
            return cls(package=package, url=url)
        if parsed.is_prerelease or parsed.is_postrelease or parsed.local:
            return cls(package=package, url=url)
        return cls(package=package, url=url, ref=version)

    def contains(self, module: str) -> bool:
        """Whether the module belongs to the package."""
        return module == self.package or module.startswith(
            f"{self.package}."
        )

    def module_url(self, module: str) -> str:
        return f"{self.url}/blob/{self.ref}/{module.replace('.', '/')}.py"


@functools.cache
def _default_repositories() -> tuple[SourceRepository, ...]:
    # the installed versions do not change while the docs are built
    return (
        SourceRepository.from_distribution(
            "rally",
            "https://github.com/openstack/rally",
            distribution="rally",
        ),
        SourceRepository.from_distribution(
            "rally_openstack",
            "https://github.com/openstack/rally-openstack",
            distribution="rally-openstack",
        ),
    )


def _join_paragraphs(*paragraphs: str) -> str:
    """Join the non-empty paragraphs, separated by a single blank line.

    Texts coming from docstrings carry leading and trailing newlines, which
    would otherwise pile up into several blank lines.
    """
    return "\n\n".join(p.strip() for p in paragraphs if p.strip())


def _capitalize(text: str) -> str:
    text = text.strip()
    # .capitalize() would lowercase the rest of the text
    return text[:1].upper() + text[1:]


def _extra_args(schema: dict[str, t.Any]) -> str | None:
    # ``additionalProperties`` that only allows or annotates extra keys (True,
    # or a description-only schema) is the ``**kwargs`` catch-all, not a
    # per-value type.
    extra = schema.get("additionalProperties")
    if extra is True:
        return ""
    if isinstance(extra, dict) and not (set(extra) - {"description"}):
        return str(extra.get("description", "")).strip()
    return None


class _Parameter(t.TypedDict):
    """A key of an object and the value it accepts."""

    name: str
    required: bool
    value: _Schema


class _Group(t.TypedDict):
    """Keys of an object that should be provided together."""

    keys: list[str]
    doc: str


class _BaseSchema(t.TypedDict):
    # see _type_label()
    label: str | None
    doc: str


class _ValueSchema(_BaseSchema):
    """A value without nested values (or with ones that are not expanded)."""

    kind: t.Literal["value"]


class _ListSchema(_BaseSchema):
    """A list, which elements follow a schema."""

    kind: t.Literal["list"]
    items: _Schema | None


class _ChoiceSchema(_BaseSchema):
    """A value that matches one (``oneOf``) or any (``anyOf``) option."""

    kind: t.Literal["choice"]
    options: list[_Schema]


class _ObjectSchema(_BaseSchema):
    """An object with a known set of keys."""

    kind: t.Literal["object"]
    parameters: list[_Parameter]
    # keys that no value is valid for
    forbidden: list[str]
    # description of the accepted extra keys, None if they are not accepted
    extra_args: str | None
    # alternative sets of the parameters, one of which should be provided
    required_groups: list[_Group]
    # alternative groups of more parameters, one of which should be provided
    options: list[_ObjectSchema]


class _PatternObjectSchema(_BaseSchema):
    """An object whose keys follow patterns."""

    kind: t.Literal["pattern_object"]
    patterns: list[_Parameter]
    extra_args: str | None


_Schema: t.TypeAlias = (
    _ValueSchema
    | _ListSchema
    | _ChoiceSchema
    | _ObjectSchema
    | _PatternObjectSchema
)


def _type_label(schema: t.Any) -> str | None:
    """Describe the types of a value that a jsonschema accepts.

    :returns: a short label (e.g. ``str/int/null``), or None when the value is
        not restricted to a set of types, e.g. for an enum, whose values are
        listed instead
    """
    if not isinstance(schema, dict) or "enum" in schema:
        return None

    labels: list[str] = []
    if "type" in schema:
        json_types = schema["type"]
        if not isinstance(json_types, list):
            json_types = [json_types]
        labels = [
            plugin_info.JSON_SCHEMA_TYPE_LABELS.get(json_type) or json_type
            for json_type in json_types
        ]
    else:
        options = schema.get("anyOf", schema.get("oneOf"))
        if not isinstance(options, list):
            return None
        for option in options:
            label = _type_label(option)
            if label is None:
                return None
            labels.extend(label.split("/"))

    labels = [
        label for i, label in enumerate(labels) if label not in labels[:i]
    ]
    # ``null`` reads as a note on the other types, so it goes last
    labels.sort(key=lambda label: label == "null")
    return "/".join(labels) or None


def _constraints(schema: dict[str, t.Any]) -> list[str]:
    """Describe the restrictions of a value, a paragraph per restriction."""
    paragraphs = []
    if "pattern" in schema:
        paragraphs.append(f"Should follow next pattern: {schema['pattern']}.")
    for title, key, exclusive_key in (
        ("Min value", "minimum", "exclusiveMinimum"),
        ("Max value", "maximum", "exclusiveMaximum"),
    ):
        exclusive = schema.get(exclusive_key)
        if isinstance(exclusive, bool):
            # draft 4: a flag that makes the bound itself exclusive
            if key in schema:
                suffix = " (exclusive)" if exclusive else ""
                paragraphs.append(f"{title}: {schema[key]}{suffix}.")
            continue
        # later drafts: a bound of its own, that may duplicate the inclusive
        if key in schema and schema[key] != exclusive:
            paragraphs.append(f"{title}: {schema[key]}.")
        if exclusive is not None:
            paragraphs.append(f"{title}: {exclusive} (exclusive).")
    return paragraphs


def _resolve_refs(schema: dict[str, t.Any]) -> dict[str, t.Any]:
    """Replace local references to definitions with the definitions.

    A reference that leads to itself (directly or not) is left as it is.
    """
    definitions = {**schema.get("definitions", {}), **schema.get("$defs", {})}

    def resolve(node: t.Any, seen: tuple[str, ...]) -> t.Any:
        if isinstance(node, list):
            return [resolve(item, seen) for item in node]
        if not isinstance(node, dict):
            return node
        ref = node.get("$ref")
        if isinstance(ref, str) and ref not in seen:
            for prefix in ("#/definitions/", "#/$defs/"):
                name = ref.removeprefix(prefix)
                if name != ref and name in definitions:
                    siblings = {k: v for k, v in node.items() if k != "$ref"}
                    return {
                        **resolve(definitions[name], (*seen, ref)),
                        **resolve(siblings, seen),
                    }
        return {key: resolve(value, seen) for key, value in node.items()}

    return resolve(
        {k: v for k, v in schema.items() if k not in ("definitions", "$defs")},
        (),
    )


def _dump_jsonschema(schema: dict[str, t.Any]) -> str:
    raw = {k: v for k, v in schema.items() if k != "description"}
    return (
        f"Format:\n\n.. code-block:: json\n\n"
        f"{textwrap.indent(json.dumps(raw, indent=4), '    ')}"
    )


def _process_properties(
    schema: dict[str, t.Any], *, level: int
) -> tuple[list[_Parameter], list[str]]:
    """Describe the keys of an object and the keys that are forbidden."""
    required = schema.get("required", [])
    parameters: list[_Parameter] = []
    forbidden: list[str] = []
    for name, prop in schema.get("properties", {}).items():
        if prop is False:
            forbidden.append(name)
            continue
        parameters.append(
            _Parameter(
                name=name,
                required=name in required,
                value=_process_jsonschema(
                    prop if isinstance(prop, dict) else {}, level=level + 1
                ),
            )
        )
    return parameters, forbidden


def _process_object_jsonschema(
    schema: dict[str, t.Any], *, level: int
) -> _ObjectSchema | _PatternObjectSchema:
    label = _type_label(schema)
    doc = schema.get("description", "")

    if "patternProperties" in schema and "properties" not in schema:
        return _PatternObjectSchema(
            kind="pattern_object",
            label=label,
            doc=doc,
            patterns=[
                _Parameter(
                    name=pattern,
                    required=False,
                    value=_process_jsonschema(value, level=level + 1),
                )
                for pattern, value in schema["patternProperties"].items()
            ],
            extra_args=_extra_args(schema),
        )

    keyword = next((k for k in ("oneOf", "anyOf") if k in schema), None)
    options = schema[keyword] if keyword else []

    if not any("properties" in option for option in options):
        # the options (if any) only tell which keys should go together:
        #
        #   {"type": "object",
        #    "properties": {"foo": {...}, "bar": {...}, "baz": {...}},
        #    "oneOf": [{"required": ["foo", "bar"]},
        #              {"required": ["foo", "baz"]}]}
        parameters, forbidden = _process_properties(schema, level=level)
        requireds = [option.get("required", []) for option in options]
        common = [
            key for key in (requireds[0] if requireds else [])
            if all(key in required for required in requireds[1:])
        ]
        for parameter in parameters:
            if parameter["name"] in common:
                parameter["required"] = True
        return _ObjectSchema(
            kind="object",
            label=label,
            doc=doc,
            parameters=parameters,
            forbidden=forbidden,
            extra_args=_extra_args(schema),
            required_groups=[
                _Group(
                    keys=[key for key in required if key not in common],
                    doc=option.get("description", ""),
                )
                for option, required in zip(options, requireds)
            ],
            options=[],
        )

    # each option is a group of more keys, while the rest of the schema is
    # shared by all options:
    #
    #   {"type": "object",
    #    "properties": {"foo": {...}},
    #    "oneOf": [{"properties": {"bar": {...}}, "required": ["bar"]},
    #              {"properties": {"baz": {...}}, "required": ["baz"]}]}
    merged_options = []
    for option in options:
        merged = {k: v for k, v in schema.items() if k != keyword}
        merged.update(option)
        merged["description"] = option.get("description", "")
        merged["properties"] = {
            **schema.get("properties", {}),
            **option.get("properties", {}),
        }
        merged["required"] = [
            *schema.get("required", []),
            *option.get("required", []),
        ]
        merged_options.append(merged)

    # the groups of a nested object are items of a list, so their keys are
    # nested one level deeper; top-level groups are sections of their own
    options_level = level if level == 1 else level + 1
    processed = [
        _process_properties(merged, level=options_level)
        for merged in merged_options
    ]
    shared = [
        parameter["name"]
        for parameter in processed[0][0]
        if all(parameter in parameters for parameters, _ in processed[1:])
    ]
    first = merged_options[0]
    parameters, _forbidden = _process_properties(
        {
            "properties": {name: first["properties"][name] for name in shared},
            "required": [name for name in first["required"] if name in shared],
        },
        level=level,
    )
    return _ObjectSchema(
        kind="object",
        label=label,
        doc=doc,
        parameters=parameters,
        forbidden=[],
        extra_args=_extra_args(schema),
        required_groups=[],
        options=[
            _ObjectSchema(
                kind="object",
                label=plugin_info.JSON_SCHEMA_TYPE_LABELS["object"],
                doc=merged["description"],
                parameters=[
                    p for p in option_parameters if p["name"] not in shared
                ],
                forbidden=option_forbidden,
                extra_args=None,
                required_groups=[],
                options=[],
            )
            for merged, (option_parameters, option_forbidden) in zip(
                merged_options, processed
            )
        ],
    )


def _process_jsonschema(schema: dict[str, t.Any], *, level: int) -> _Schema:
    """Describe a jsonschema in a shape that is easy to render as docs.

    :param level: the nesting level of the values nested into this one, 1 for
        the parameters of a plugin. The values nested deeper than
        ``_MAX_LEVEL`` are not expanded, the jsonschema is dumped instead.
    """
    if "default" in schema:
        # ``default`` is an informational annotation, not a constraint: render
        # it as a note appended to whatever the rest of the schema describes.
        # A ``None`` default carries no information (the argument is simply
        # optional), so it is dropped without a note.
        processed = _process_jsonschema(
            {k: v for k, v in schema.items() if k != "default"}, level=level
        )
        if schema["default"] is not None:
            processed["doc"] = _join_paragraphs(
                processed["doc"],
                f"Defaults to ``{json.dumps(schema['default'])}``.",
            )
        return processed

    label = _type_label(schema)
    doc = schema.get("description", "")

    if level > _MAX_LEVEL and any(k in schema for k in _NESTED_KEYWORDS):
        options = schema.get("anyOf", schema.get("oneOf"))
        # a choice of bare types (e.g. ``str/float``) is told by the label
        # already, the dump would only repeat it
        bare_types = isinstance(options, list) and all(
            isinstance(option, dict) and set(option) <= {"type"}
            for option in options
        )
        if not bare_types:
            doc = _join_paragraphs(doc, _dump_jsonschema(schema))
        return _ValueSchema(kind="value", label=label, doc=doc)

    json_types = schema.get("type", [])
    if not isinstance(json_types, list):
        json_types = [json_types]
    if set(json_types) - {*plugin_info.JSON_SCHEMA_TYPE_LABELS, "null"}:
        raise ValueError(f"Failed to parse jsonschema: {schema}")

    if "object" in json_types:
        return _process_object_jsonschema(schema, level=level)

    if "array" in json_types:
        items = schema.get("items")
        processed_items = None
        if isinstance(items, dict) and items:
            # objects and choices are described right in the list, while
            # other elements (including a nested list) are items of their own
            item_types = items.get("type", [])
            if not isinstance(item_types, list):
                item_types = [item_types]
            nested_list = "array" in item_types
            processed_items = _process_jsonschema(
                items, level=level + 1 if nested_list else level
            )
        return _ListSchema(
            kind="list",
            label=label,
            doc=_join_paragraphs(doc, *_constraints(schema)),
            items=processed_items,
        )

    if "enum" in schema:
        # values are shown as they are written in a task (like the default),
        # so a string is told apart from a number or ``null``
        values = [
            f"``{json.dumps(value, default=str)}``" for value in schema["enum"]
        ]
        if len(values) == 1:
            expected = f"Expected value: {values[0]}."
        else:
            expected = f"Set of expected values: {', '.join(values)}."
        return _ValueSchema(
            kind="value", label=label, doc=_join_paragraphs(doc, expected)
        )

    for keyword in ("anyOf", "oneOf"):
        if keyword in schema:
            return _ChoiceSchema(
                kind="choice",
                label=label,
                doc=doc,
                options=[
                    _process_jsonschema(option, level=level + 1)
                    for option in schema[keyword]
                ],
            )

    return _ValueSchema(
        kind="value",
        label=label,
        doc=_join_paragraphs(doc, *_constraints(schema)),
    )


def _parameter_term(parameter: _Parameter, *, pattern: bool = False) -> str:
    """Render the name of a parameter with its type and whether it is required.

    A pattern is shown verbatim, since it is full of inline markup characters.
    """
    if pattern:
        return f"``{parameter['name']}`` *(string)*"
    qualifiers = []
    if parameter["value"]["label"]:
        qualifiers.append(parameter["value"]["label"])
    if parameter["required"]:
        qualifiers.append("required")
    if qualifiers:
        return f"*{parameter['name']} ({', '.join(qualifiers)})*"
    return f"*{parameter['name']}*"


def _bullet(term: str, body: str) -> str:
    """Render an item of a nested list, with the body aligned to the term."""
    if not term:
        return f"- {textwrap.indent(body, '  ')[2:]}"
    if not body:
        return f"- {term}"
    return f"- {term}\n\n{textwrap.indent(body, '  ')}"


def _make_group_bullets(groups: t.Sequence[_Group]) -> list[str]:
    return [
        _bullet(
            ", ".join(f"``{key}``" for key in group["keys"])
            or "*no other parameters*",
            _capitalize(group["doc"]),
        )
        for group in groups
    ]


def _make_object_body(value: _ObjectSchema) -> list[str]:
    """Render the keys of a nested object, a paragraph per item."""
    paragraphs = [
        _bullet(_parameter_term(p), _make_value_body(p["value"]))
        for p in value["parameters"]
    ]
    if value["forbidden"]:
        paragraphs.append(
            f"**Restricted parameters**: {', '.join(value['forbidden'])}"
        )
    if value["required_groups"]:
        paragraphs.append(f"{_GROUPS_NOTE}:")
        paragraphs.extend(_make_group_bullets(value["required_groups"]))
    if value["options"]:
        paragraphs.append(f"{_GROUPS_NOTE}:")
        for i, option in enumerate(value["options"], 1):
            body = _join_paragraphs(
                _capitalize(option["doc"]), *_make_object_body(option)
            )
            paragraphs.append(_bullet(f"*Option {i}*", body))
    if value["extra_args"] is not None:
        detail = value["extra_args"] or "accepted"
        paragraphs.append(f"**Additional parameters**: {detail}")
    return paragraphs


def _make_value_body(value: _Schema) -> str:
    """Render the description of a value followed by its nested values."""
    paragraphs = [_capitalize(value["doc"])]

    if value["kind"] == "list" and value["items"] is not None:
        items = value["items"]
        if items["kind"] in ("object", "choice", "pattern_object"):
            items_body = _make_value_body(items)
        else:
            items_body = _join_paragraphs(
                f"Type: {items['label']}." if items["label"] else "",
                _make_value_body(items),
            )
            items_body = _bullet("", items_body) if items_body else ""
        if items_body:
            paragraphs.append(
                "Elements of the list should follow format(s) described "
                "below:"
            )
            paragraphs.append(items_body)

    elif value["kind"] == "choice":
        bodies = [_make_value_body(option) for option in value["options"]]
        # options that have nothing to add would only repeat the type label
        if any(bodies):
            paragraphs.append("One of:")
            labels = [option["label"] for option in value["options"]]
            # e.g. several objects with different keys
            numbered = len(set(labels)) < len(labels)
            for i, (label, body) in enumerate(zip(labels, bodies), 1):
                term = f"*Option {i}*" if numbered else f"*{label or 'any'}*"
                paragraphs.append(_bullet(term, body))

    elif value["kind"] == "object":
        paragraphs.extend(_make_object_body(value))

    elif value["kind"] == "pattern_object":
        paragraphs.append("Keys should follow pattern(s) described below:")
        paragraphs.extend(
            _bullet(
                _parameter_term(p, pattern=True), _make_value_body(p["value"])
            )
            for p in value["patterns"]
        )
        if value["extra_args"] is not None:
            detail = value["extra_args"] or "accepted"
            paragraphs.append(f"**Additional parameters**: {detail}")

    return _join_paragraphs(*paragraphs)


def _make_definitions(
    *,
    title: str,
    ref_prefix: str,
    terms: t.Sequence[tuple[str, str, str]],
    descriptions: t.Sequence[str] = (),
) -> str:
    """Render a list of definitions, each with a reference to itself.

    :param terms: ``(term, ref, doc)`` triples, where the term is already
        formatted as inline reStructuredText
    """
    blocks = [f"**{title}**:", *(d.strip() for d in descriptions if d.strip())]

    for term, ref, doc in terms:
        # docutils turns a target name into an id by collapsing every run of
        # other characters into "-", while the ``__ #<ref>`` URI is kept
        # verbatim, so the ref is normalized the same way to match the id
        ref = re.sub(r"[^a-z0-9]+", "-", f"{ref_prefix}{ref}".lower())
        ref = ref.strip("-")
        blocks.append(f".. _{ref}:")
        blocks.append(f"* {term} [ref__]")
        doc = _capitalize(doc)
        if doc:
            blocks.append(textwrap.indent(doc, "  "))
        blocks.append(f"__ #{ref}")

    return "\n\n".join(blocks)


def _make_arg_items(
    parameters: t.Sequence[_Parameter],
    *,
    ref_prefix: str,
    forbidden: t.Sequence[str] = (),
    title: str = "Parameters",
    descriptions: t.Sequence[str] = (),
    patterns: bool = False,
) -> str:
    terms = []
    for i, parameter in enumerate(parameters, 1):
        # the anchor uses the bare argument name, while a pattern is anchored
        # by its position, since nothing of it may survive the normalization
        # of the anchor
        ref = f"pattern-{i}" if patterns else parameter["name"]
        terms.append(
            (
                _parameter_term(parameter, pattern=patterns),
                ref,
                _make_value_body(parameter["value"]),
            )
        )

    text = _make_definitions(
        title=title,
        ref_prefix=ref_prefix,
        terms=terms,
        descriptions=descriptions,
    )
    if forbidden:
        text += f"\n\n**Restricted parameters**: {', '.join(forbidden)}"
    return text


def _make_schema_items(
    raw_schema: dict[str, t.Any], *, ref_prefix: str
) -> list[str]:
    raw_schema = _resolve_refs(raw_schema)
    schema = _process_jsonschema(raw_schema, level=1)
    blocks = []
    if schema["kind"] == "object":
        # skip the empty "Parameters" header when a plugin only takes extra
        # arguments (rendered as "Additional parameters") or groups of them
        if schema["parameters"] or schema["forbidden"]:
            blocks.append(
                _make_arg_items(
                    schema["parameters"],
                    ref_prefix=ref_prefix,
                    forbidden=schema["forbidden"],
                )
            )
        if schema["required_groups"]:
            bullets = "\n\n".join(
                _make_group_bullets(schema["required_groups"])
            )
            blocks.append(
                f".. note:: {_GROUPS_NOTE}:\n\n"
                f"{textwrap.indent(bullets, '   ')}"
            )
        if schema["options"]:
            blocks.append(f".. note:: {_GROUPS_NOTE}.")
        for i, option in enumerate(schema["options"], 1):
            # options may share parameter names, so anchors are per option
            blocks.append(
                _make_arg_items(
                    option["parameters"],
                    ref_prefix=f"{ref_prefix}option-{i}-",
                    forbidden=option["forbidden"],
                    title=f"Option {i} of parameters",
                    descriptions=[option["doc"]],
                )
            )
    elif schema["kind"] == "pattern_object":
        blocks.append(
            _make_arg_items(
                schema["patterns"],
                ref_prefix=ref_prefix,
                descriptions=[
                    "*Dictionary is expected. Keys should follow pattern(s) "
                    "described below.*"
                ],
                patterns=True,
            )
        )
    else:
        # the plugin accepts a single value rather than named parameters
        if schema["label"] is None:
            raise ValueError(
                f"Failed to display provided schema: {raw_schema}"
            )
        blocks.append(f"**Input value**: *{schema['label']}*")
        blocks.append(_make_value_body(schema))

    if schema["kind"] == "object" or schema["kind"] == "pattern_object":
        if schema["extra_args"] is not None:
            detail = schema["extra_args"] or "accepted"
            blocks.append(f"**Additional parameters**: {detail}")
    return [block for block in blocks if block]


def _make_required_platforms(plugin_cls: type[plugin.Plugin]) -> list[str]:
    if not issubclass(plugin_cls, validation.ValidatablePluginMixin):
        return []
    platforms = [
        kwargs
        for name, _args, kwargs in plugin_cls._meta_get(
            "validators", default=[]
        )
        if name == "required_platform"
    ]
    if not platforms:
        return []

    admin_msg = "credentials for admin user"
    user_msg = (
        "regular users (temporary users can be created via the 'users' "
        "context if admin user is specified for the platform)"
    )
    lines = []
    for p in platforms:
        line = f"* {p['platform']}"
        if p.get("admin", False) and p.get("users", False):
            line += f" with {admin_msg} and {user_msg}."
        elif p.get("admin", False):
            line += f" with {admin_msg}."
        elif p.get("users", False):
            line += f" with {user_msg}."
        lines.append(line)
    return ["**Requires platform(s)**:", "\n".join(lines)]


def make_plugin_section(
    plugin_cls: type[plugin.Plugin],
    *,
    base_name: str | None = None,
    repositories: t.Sequence[SourceRepository] | None = None,
) -> str:
    """Render the reference documentation of a plugin.

    :param plugin_cls: the plugin to document
    :param base_name: the name of the plugin base, to add to the title and to
        the anchors of parameters
    :param repositories: where the source code of plugins is hosted. By
        default, rally and rally-openstack at GitHub, linked by the release
        tag of the installed version or by the ``master`` branch for a
        development version.
    :returns: a section (with a title underlined by ``"``) in reStructuredText
    """
    if repositories is None:
        repositories = _default_repositories()

    info = plugin_cls.get_info()
    module = info["module"]
    repository = next((r for r in repositories if r.contains(module)), None)
    if repository is None:
        raise ValueError(
            f"Plugin '{plugin_cls.get_name()}' is defined in module "
            f"'{module}' that does not belong to any known repository."
        )

    title = plugin_cls.get_name()
    if base_name:
        title += f" [{base_name}]"
        ref_prefix = f"{base_name}-{plugin_cls.get_name()}-"
    else:
        ref_prefix = f"{plugin_cls.get_name()}-"
    underline = '"' * len(title)
    blocks = [f"{title}\n{underline}"]

    if info["title"].strip():
        blocks.append(info["title"].strip())
    if info["description"].strip():
        blocks.append(info["description"].strip())
    if info["platform"]:
        blocks.append(f"**Platform**: {info['platform']}")

    if info["schema"]:
        blocks.extend(
            _make_schema_items(info["schema"], ref_prefix=ref_prefix)
        )
    elif info["parameters"]:
        blocks.append(
            _make_arg_items(
                [
                    _Parameter(
                        name=p["name"],
                        required=False,
                        value=_ValueSchema(
                            kind="value", label=None, doc=p["doc"]
                        ),
                    )
                    for p in info["parameters"]
                ],
                ref_prefix=ref_prefix,
            )
        )

    if info["returns"].strip():
        blocks.append(f"**Returns**:\n{info['returns'].strip()}")

    blocks.extend(_make_required_platforms(plugin_cls))

    blocks.append(
        f"**Module**:\n`{module}`__\n\n__ {repository.module_url(module)}"
    )
    return "\n\n".join(blocks) + "\n"
