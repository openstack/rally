# Copyright 2015: Mirantis Inc.
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

from __future__ import annotations

import copy
import json
import re
import typing as t

from docutils.parsers import rst

from rally import plugins
from rally.common import validation
from rally.common.plugin import discover
from rally.common.plugin import info
from rally.common.plugin import plugin

from . import utils


JSON_SCHEMA_TYPES_MAP = info.JSON_SCHEMA_TYPE_LABELS


def process_jsonschema(schema: t.Any) -> dict:
    """Process jsonschema and make it looks like regular docstring."""

    if not schema:
        # nothing to parse
        return {"doc": ""}

    # ``default`` is an informational annotation, not a constraint: render it
    # as a note appended to whatever the rest of the schema describes. A
    # ``None`` default carries no information (the argument is simply
    # optional), so it is dropped without a note.
    if isinstance(schema, dict) and "default" in schema:
        rest = {k: v for k, v in schema.items() if k != "default"}
        info = process_jsonschema(rest)
        if schema["default"] is not None:
            note = "Defaults to ``%s``." % json.dumps(schema["default"])
            info["doc"] = (
                "%s\n\n%s" % (info["doc"], note) if info["doc"] else note
            )
        return info

    if "type" in schema:
        # str
        if schema["type"] == "string":
            doc = schema.get("description", "")
            if "pattern" in schema:
                doc += (
                    "\n\nShould follow next pattern: %s." % schema["pattern"]
                )
            return {"doc": doc, "type": "str"}

        # int or float
        elif schema["type"] in ("integer", "number"):
            doc = schema.get("description", "")
            if "minimum" in schema:
                doc += "\n\nMin value: %s." % schema["minimum"]
            if "maximum" in schema:
                doc += "\n\nMax value: %s." % schema["maximum"]
            return {"doc": doc, "type": JSON_SCHEMA_TYPES_MAP[schema["type"]]}

        # bool or null
        elif schema["type"] in ("boolean", "null"):
            return {
                "doc": schema.get("description", ""),
                "type": "bool" if schema["type"] == "boolean" else "null",
            }

        # list
        elif schema["type"] == "array":
            info = {"doc": schema.get("description", ""), "type": "list"}

            if "items" in schema:
                if info["doc"]:
                    info["doc"] += "\n\n"
                info["doc"] += (
                    "Elements of the list should follow format(s) "
                    "described below:\n\n"
                )

                items = schema["items"]
                itype = None
                if "type" in items:
                    itype = JSON_SCHEMA_TYPES_MAP.get(
                        items["type"], items["type"]
                    )
                    info["doc"] += "- Type: %s. " % itype
                if "description" in items:
                    # add indention
                    desc = items["description"].split("\n")
                    info["doc"] += "\n  ".join(desc)

                # only dump the raw schema when it adds something beyond the
                # ``type`` (already shown above) and ``description``
                if set(items) - {"type", "description"}:
                    new_schema = copy.copy(items)
                    new_schema.pop("description", None)
                    new_schema = json.dumps(new_schema, indent=4)
                    new_schema = "\n     ".join(new_schema.split("\n"))

                    info["doc"] += (
                        "\n  Format:\n\n"
                        "    .. code-block:: json\n\n"
                        "      %s\n" % new_schema
                    )
            return info

        elif isinstance(schema["type"], list):
            # it can be too complicated for parsing... do not do it deeply
            return {
                "doc": schema.get("description", ""),
                "type": "/".join(schema["type"]),
            }

        # dict
        elif schema["type"] == "object":
            info = {
                "doc": schema.get("description", ""),
                "type": "dict",
                "parameters": [],
            }
            required_parameters = schema.get("required", [])
            if "properties" in schema:
                for name in schema["properties"]:
                    prop = schema["properties"][name]
                    if prop is False:
                        # a forbidden key: no value validates
                        pinfo = {"name": name, "doc": "Must not be set."}
                    elif isinstance(prop, str):
                        pinfo = {"name": name, "type": prop, "doc": ""}
                    else:
                        pinfo = process_jsonschema(prop)
                        if name in required_parameters:
                            pinfo["required"] = True
                        pinfo["name"] = name
                    info["parameters"].append(pinfo)
            elif "patternProperties" in schema:
                info.pop("parameters", None)
                info["patternProperties"] = []
                for k, v in schema["patternProperties"].items():
                    info["patternProperties"].append(process_jsonschema(v))
                    info["patternProperties"][-1]["name"] = k
                    info["patternProperties"][-1]["type"] = "str"
            elif not (
                set(schema.keys())
                - {"type", "description", "$schema", "additionalProperties"}
            ):
                # it is ok, schema accepts any object. nothing to add more
                pass
            elif "oneOf" in schema or "anyOf" in schema:
                # Example:
                #   SCHEMA = {"type": "object", "$schema": consts.JSON_SCHEMA,
                #       "oneOf": [{"properties": {"foo": {"type": "string"}}
                #                  "required": ["foo"],
                #                  "additionalProperties": False},
                #                 {"properties": {"bar": {"type": "string"}}
                #                  "required": ["bar"],
                #                  "additionalProperties": False},
                #
                schema_key = "oneOf" if "oneOf" in schema else "anyOf"
                schema_value = copy.deepcopy(schema.get(schema_key))

                for item in schema_value:
                    for k, v in schema.items():
                        if k not in (schema_key, "description"):
                            item[k] = v

                return {
                    "doc": schema.get("description", ""),
                    "type": "dict",
                    schema_key: [
                        process_jsonschema(item) for item in schema_value
                    ],
                }
            else:
                raise Exception("Failed to parse jsonschema: %s" % schema)

            # ``additionalProperties`` that only allows/annotates extra keys
            # (True, or a description-only schema) is the ``**kwargs``
            # catch-all, not a per-value type: surface it as an "extra
            # arguments" note.
            extra = schema.get("additionalProperties")
            if extra is True or (
                isinstance(extra, dict) and not (set(extra) - {"description"})
            ):
                info["extra_args"] = (
                    extra.get("description", "")
                    if isinstance(extra, dict)
                    else ""
                )

            if "definitions" in schema:
                info["definitions"] = schema["definitions"]
            return info
        else:
            raise Exception("Failed to parse jsonschema: %s" % schema)

    # enum
    elif "enum" in schema:
        doc = schema.get("description", "")
        # stringify for display: enum members keep their real (typed) values in
        # the schema; str() handles None ("None"), falsy (0, '', False) and
        # non-str members without breaking the join.
        doc += "\nSet of expected values: '%s'." % (
            "', '".join(str(e) for e in schema["enum"])
        )
        return {"doc": doc}

    elif "anyOf" in schema:
        return {
            "doc": schema.get("description", ""),
            "anyOf": [process_jsonschema(i) for i in schema["anyOf"]],
        }

    elif "oneOf" in schema:
        return {
            "doc": schema.get("description", ""),
            "oneOf": [process_jsonschema(i) for i in schema["oneOf"]],
        }

    elif "$ref" in schema:
        return {"doc": schema.get("description", "n/a"), "ref": schema["$ref"]}

    # a schema with only a description (or nothing) accepts any value, so
    # there is no type to render; just carry the description.
    elif not (set(schema.keys()) - {"description"}):
        return {"doc": schema.get("description", "")}

    else:
        raise Exception("Failed to parse jsonschema: %s" % schema)


CATEGORIES = {
    "Common": ["OS Client"],
    "Deployment": ["Engine", "Provider Factory"],
    "Task Component": [
        "Chart",
        "Context",
        "Hook Action",
        "Hook Trigger",
        "Resource Type",
        "Task Exporter",
        "SLA",
        "Scenario",
        "Scenario Runner",
        "Trigger",
        "Validator",
    ],
    "Verification Component": [
        "Verifier Context",
        "Verification Reporter",
        "Verifier Manager",
    ],
}

# NOTE(andreykurilin): several bases do not have docstings at all, so it is
# redundant to display them
IGNORED_BASES = ["Resource Type", "OS Client", "Exporters"]


class PluginsReferenceDirective(rst.Directive):
    optional_arguments = 1
    option_spec = {"base_cls": str}

    def _make_arg_items(
        self,
        items: list[dict],
        ref_prefix: str,
        description: list[str] | None = None,
        title: str = "Parameters",
    ) -> list:
        terms: list[tuple[str, str, list[str]]] = []
        for item in items:
            name = item.get("name", "")
            if name:
                # the anchor uses the bare argument name; the visible term adds
                # the type and whether it is required (restricted characters
                # like parentheses must not leak into the anchor)
                qualifiers = []
                if "type" in item:
                    qualifiers.append(item["type"])
                if item.get("required"):
                    qualifiers.append("required")
                iname = name
                if qualifiers:
                    iname += " (%s)" % ", ".join(qualifiers)
                ref = name
            else:
                iname = ref = item.pop("type")
            terms.append((iname, ref, [item["doc"]]))
        return utils.make_definitions(
            title=title,
            ref_prefix=ref_prefix,
            terms=terms,
            descriptions=description,
        )

    def _make_plugin_section(
        self, plugin_cls: t.Any, base_name: str | None = None
    ) -> t.Any:
        section_name = plugin_cls.get_name()
        if base_name:
            section_name += f" [{base_name}]"
        section_obj = utils.section(section_name)

        info = plugin_cls.get_info()
        if info["title"]:
            section_obj.append(utils.paragraph(info["title"]))

        if info["description"]:
            section_obj.extend(utils.parse_text(info["description"]))

        if info["platform"]:
            section_obj.append(
                utils.paragraph("**Platform**: %s" % info["platform"])
            )

        if base_name:
            ref_prefix = f"{base_name}-{plugin_cls.get_name()}-"
        else:
            ref_prefix = f"{plugin_cls.get_name()}-"

        if info["schema"]:
            schema = process_jsonschema(info["schema"])
            if "type" in schema:
                if "parameters" in schema:
                    # skip the empty "Parameters" header when a scenario only
                    # takes ``**kwargs`` (rendered as "Additional parameters")
                    if schema["parameters"]:
                        section_obj.extend(
                            self._make_arg_items(
                                items=schema["parameters"],
                                ref_prefix=ref_prefix,
                            )
                        )
                elif "patternProperties" in schema:
                    section_obj.extend(
                        self._make_arg_items(
                            items=schema["patternProperties"],
                            ref_prefix=ref_prefix,
                            description=[
                                "*Dictionary is expected. Keys should "
                                "follow pattern(s) described bellow.*"
                            ],
                        )
                    )
                elif "oneOf" in schema:
                    section_obj.append(
                        utils.note(
                            "One of the following groups of "
                            "parameters should be provided."
                        )
                    )
                    for i, oneOf in enumerate(schema["oneOf"], 1):
                        description = None
                        if oneOf.get("doc", None):
                            description = [oneOf["doc"]]
                        section_obj.extend(
                            self._make_arg_items(
                                items=oneOf["parameters"],
                                ref_prefix=ref_prefix,
                                title="Option %s of parameters" % i,
                                description=description,
                            )
                        )
                else:
                    section_obj.extend(
                        self._make_arg_items(
                            items=[schema], ref_prefix=ref_prefix
                        )
                    )
                if "extra_args" in schema:
                    detail = schema["extra_args"] or "accepted"
                    section_obj.append(
                        utils.paragraph(f"**Additional parameters**: {detail}")
                    )
            else:
                raise Exception(
                    "Failed to display provided schema: %s" % info["schema"]
                )
        # include parameters only if there is no schema
        elif info["parameters"]:
            section_obj.extend(
                self._make_arg_items(info["parameters"], ref_prefix)
            )

        if info["returns"]:
            section_obj.extend(
                utils.parse_text("**Returns**:\n%s" % info["returns"])
            )

        if issubclass(plugin_cls, validation.ValidatablePluginMixin):
            validators = plugin_cls._meta_get("validators", default=[])
            platforms = [
                kwargs
                for name, args, kwargs in validators
                if name == "required_platform"
            ]
            if platforms:
                section_obj.append(
                    utils.paragraph("**Requires platform(s)**:")
                )
                section = ""
                for p in platforms:
                    section += "* %s" % p["platform"]
                    admin_msg = "credentials for admin user"
                    user_msg = (
                        "regular users (temporary users can be created"
                        " via the 'users' context if admin user is "
                        "specified for the platform)"
                    )
                    if p.get("admin", False) and p.get("users", False):
                        section += f" with {admin_msg} and {user_msg}."
                    elif p.get("admin", False):
                        section += f" with {admin_msg}."
                    elif p.get("users", False):
                        section += f" with {user_msg}."
                    section += "\n"

                section_obj.extend(utils.parse_text(section))

        filename = info["module"].replace(".", "/")
        if filename.startswith("rally/"):
            project = "rally"
        elif filename.startswith("rally_openstack/"):
            project = "rally-openstack"
        else:
            # WTF is it?!
            return None
        ref = (
            f"https://github.com/openstack/{project}/blob/master/{filename}.py"
        )
        section_obj.extend(
            utils.parse_text(
                "**Module**:\n`%s`__\n\n__ %s" % (info["module"], ref)
            )
        )
        return section_obj

    def _make_plugin_base_section(
        self, base_cls: t.Any, base_name: str | None = None
    ) -> list:
        if base_name:
            title = (
                f"%{base_name}"
                if base_name[-1] != "y"
                else f"{base_name[:-1]}ies"
            )
            subcategory_obj = utils.subcategory(title)
        else:
            subcategory_obj = []
        for p in sorted(base_cls.get_all(), key=lambda o: o.get_name()):
            # do not display hidden contexts
            if p._meta_get("hidden", False):
                continue
            subcategory_obj.append(self._make_plugin_section(p, base_name))

        return subcategory_obj

    @staticmethod
    def _parse_class_name(cls: t.Any) -> str:
        name = ""
        for word in re.split(r"([A-Z][a-z]*)", cls.__name__):
            if word:
                if len(word) > 1 and name:
                    name += " "
                name += word
        return name

    @plugins.ensure_plugins_are_loaded
    def _get_all_plugins_bases(self) -> list:
        """Return grouped and sorted all plugins bases."""
        bases = []
        bases_names = []
        for p in discover.itersubclasses(plugin.Plugin):
            base_ref = getattr(p, "base_ref", None)
            if base_ref == p:
                name = self._parse_class_name(p)
                if name in bases_names:
                    raise Exception(
                        f"Two base classes with same name "
                        f"'{name}' are detected."
                    )
                bases_names.append(name)
                category_of_base = "Common"
                for cname, cbases in CATEGORIES.items():
                    if name in cbases:
                        category_of_base = cname

                bases.append((category_of_base, name, p))
        return sorted(bases)

    def run(self) -> list:
        bases = self._get_all_plugins_bases()
        if "base_cls" in self.options:
            for _category_name, base_name, base_cls in bases:
                if base_name == self.options["base_cls"]:
                    return self._make_plugin_base_section(base_cls)
            raise Exception(
                "Failed to generate plugins reference for '%s'"
                " plugin base." % self.options["base_cls"]
            )

        categories = {}

        for category_name, base_name, base_cls in bases:
            # FIXME(andreykurilin): do not ignore anything
            if base_name in IGNORED_BASES:
                continue
            if category_name not in categories:
                categories[category_name] = utils.category(category_name)
            category_of_base = categories[category_name]
            category_of_base.append(
                self._make_plugin_base_section(base_cls, base_name)
            )
        return [content for _name, content in sorted(categories.items())]


def setup(app: t.Any) -> None:
    plugins.load()
    app.add_directive("generate_plugin_reference", PluginsReferenceDirective)
