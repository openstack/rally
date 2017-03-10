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

import copy
from docutils.parsers import rst
import json
import re

from rally.common.plugin import discover
from rally.common.plugin import plugin
from rally import plugins
from utils import category, subcategory, section, paragraph, parse_text, \
    make_definitions, note


JSON_SCHEMA_TYPES_MAP = {"boolean": "bool",
                         "string": "str",
                         "number": "float",
                         "integer": "int",
                         "array": "list",
                         "object": "dict"}


def process_jsonschema(schema):
    """Process jsonschema and make it looks like regular docstring."""

    if not schema:
        # nothing to parse
        return

    if "type" in schema:

        # str
        if schema["type"] == "string":
            doc = schema.get("description", "")
            if "pattern" in schema:
                doc += ("\n\nShould follow next pattern: %s." %
                        schema["pattern"])
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
            return {"doc": schema.get("description", ""),
                    "type": "bool" if schema["type"] == "boolean" else "null"}

        # list
        elif schema["type"] == "array":
            info = {"doc": schema.get("description", ""),
                    "type": "list"}

            if "items" in schema:
                if info["doc"]:
                    info["doc"] += "\n\n"
                info["doc"] += ("Elements of the list should follow format(s) "
                                "described below:\n\n")

                items = schema["items"]
                if "type" in items:
                    itype = JSON_SCHEMA_TYPES_MAP.get(items["type"],
                                                      items["type"])
                    info["doc"] += "- Type: %s. " % itype
                    if "description" in items:
                        # add indention
                        desc = items["description"].split("\n")
                        info["doc"] += "\n  ".join(desc)

                    if itype in ("list", "dict"):
                        new_schema = copy.copy(items)
                        new_schema.pop("description", None)
                        new_schema = json.dumps(new_schema, indent=4)
                        new_schema = "\n     ".join(
                            new_schema.split("\n"))

                        info["doc"] += ("\n  Format:\n\n"
                                        "    .. code-block:: json\n\n"
                                        "      %s\n" % new_schema)
                else:
                    info["doc"] += " - ``%s`` " % items
            return info

        elif isinstance(schema["type"], list):
            # it can be too complicated for parsing... do not do it deeply
            return {"doc": schema.get("description", ""),
                    "type": "/".join(schema["type"])}

        # dict
        elif schema["type"] == "object":
            info = {"doc": schema.get("description", ""),
                    "type": "dict",
                    "parameters": []}
            required_parameters = schema.get("required", [])
            if "properties" in schema:
                for name in schema["properties"]:
                    if isinstance(schema["properties"][name], str):
                        pinfo = {"name": name,
                                 "type": schema["properties"][name],
                                 "doc": ""}
                    else:
                        pinfo = process_jsonschema(schema["properties"][name])
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
            elif (not (set(schema.keys()) - {"type", "description", "$schema",
                                             "additionalProperties"})):
                # it is ok, schema accepts any object. nothing to add more
                pass
            elif "oneOf" in schema:
                # Example:
                #   SCHEMA = {"type": "object", "$schema": consts.JSON_SCHEMA,
                #       "oneOf": [{"properties": {"foo": {"type": "string"}}
                #                  "required": ["foo"],
                #                  "additionalProperties": False},
                #                 {"properties": {"bar": {"type": "string"}}
                #                  "required": ["bar"],
                #                  "additionalProperties": False},
                #
                oneOf = copy.deepcopy(schema["oneOf"])
                for item in oneOf:
                    for k, v in schema.items():
                        if k not in ("oneOf", "description"):
                            item[k] = v

                return {"doc": schema.get("description", ""),
                        "type": "dict",
                        "oneOf": [process_jsonschema(item) for item in oneOf]}
            else:
                raise Exception("Failed to parse jsonschema: %s" % schema)

            if "definitions" in schema:
                info["definitions"] = schema["definitions"]
            return info
        else:
            raise Exception("Failed to parse jsonschema: %s" % schema)

    # enum
    elif "enum" in schema:
        doc = schema.get("description", "")
        doc += "\nSet of expected values: '%s'." % ("', '".join(
            [e or "None" for e in schema["enum"]]))
        return {"doc": doc}

    elif "anyOf" in schema:
        return {"doc": schema.get("description", ""),
                "anyOf": [process_jsonschema(i) for i in schema["anyOf"]]}

    elif "oneOf" in schema:
        return {"doc": schema.get("description", ""),
                "oneOf": [process_jsonschema(i) for i in schema["oneOf"]]}

    elif "$ref" in schema:
        return {"doc": schema.get("description", "n/a"),
                "ref": schema["$ref"]}
    else:
        raise Exception("Failed to parse jsonschema: %s" % schema)


CATEGORIES = {
    "Common": ["OS Client"],
    "Deployment": ["Engine", "Provider Factory"],
    "Task Component": ["Chart", "Context", "Exporter", "Hook",
                       "Resource Type", "SLA", "Scenario", "Scenario Runner",
                       "Trigger"],
    "Verification Component": ["Verifier Context", "Verification Reporter",
                               "Verifier Manager"]
}

# NOTE(andreykurilin): several bases do not have docstings at all, so it is
# redundant to display them
IGNORED_BASES = ["Resource Type", "Task Exporter", "OS Client"]


class PluginsReferenceDirective(rst.Directive):
    optional_arguments = 1
    option_spec = {"base_cls": str}

    def _make_arg_items(self, items, ref_prefix, description=None,
                        title="Parameters"):
        terms = []
        for item in items:
            iname = item.get("name", "") or item.pop("type")
            if "type" in item:
                iname += " (%s)" % item["type"]
            terms.append((iname, [item["doc"]]))
        return make_definitions(title=title,
                                ref_prefix=ref_prefix,
                                terms=terms,
                                descriptions=description)

    def _make_plugin_section(self, plugin_cls, base_name=None):
        section_name = plugin_cls.get_name()
        if base_name:
            section_name += " [%s]" % base_name
        section_obj = section(section_name)

        info = plugin_cls.get_info()
        if info["title"]:
            section_obj.append(paragraph(info["title"]))

        if info["description"]:
            section_obj.extend(parse_text(info["description"]))

        if info["namespace"]:
            section_obj.append(paragraph(
                "**Namespace**: %s" % info["namespace"]))

        if base_name:
            ref_prefix = "%s-%s-" % (base_name, plugin_cls.get_name())
        else:
            ref_prefix = "%s-" % plugin_cls.get_name()

        if info["parameters"]:
            section_obj.extend(self._make_arg_items(info["parameters"],
                                                    ref_prefix))

        if info["returns"]:
            section_obj.extend(parse_text(
                "**Returns**:\n%s" % info["returns"]))

        if info["schema"]:
            schema = process_jsonschema(info["schema"])
            if "type" in schema:
                if "parameters" in schema:
                    section_obj.extend(self._make_arg_items(
                        items=schema["parameters"],
                        ref_prefix=ref_prefix))
                elif "patternProperties" in schema:
                    section_obj.extend(self._make_arg_items(
                        items=schema["patternProperties"],
                        ref_prefix=ref_prefix,
                        description=["*Dictionary is expected. Keys should "
                                     "follow pattern(s) described bellow.*"]))
                elif "oneOf" in schema:
                    section_obj.append(note("One of the following groups of "
                                            "parameters should be provided."))
                    for i, oneOf in enumerate(schema["oneOf"], 1):
                        description = None
                        if oneOf.get("doc", None):
                            description = [oneOf["doc"]]
                        section_obj.extend(self._make_arg_items(
                            items=oneOf["parameters"],
                            ref_prefix=ref_prefix,
                            title="Option %s of parameters" % i,
                            description=description))
                else:
                    section_obj.extend(self._make_arg_items(
                        items=[schema], ref_prefix=ref_prefix))
            else:
                raise Exception("Failed to display provided schema: %s" %
                                info["schema"])

        filename = info["module"].replace(".", "/")
        ref = "https://github.com/openstack/rally/blob/master/%s.py" % filename
        section_obj.extend(parse_text("**Module**:\n`%s`__\n\n__ %s"
                                          % (info["module"], ref)))
        return section_obj

    def _make_plugin_base_section(self, base_cls, base_name=None):
        if base_name:
            title = ("%ss" % base_name if base_name[-1] != "y"
                     else "%sies" % base_name[:-1])
            subcategory_obj = subcategory(title)
        else:
            subcategory_obj = []
        for p in sorted(base_cls.get_all(), key=lambda o: o.get_name()):
            # do not display hidden contexts
            if p._meta_get("hidden", False):
                continue
            subcategory_obj.append(self._make_plugin_section(p, base_name))

        return subcategory_obj

    @staticmethod
    def _parse_class_name(cls):
        name = ""
        for word in re.split(r'([A-Z][a-z]*)', cls.__name__):
            if word:
                if len(word) > 1 and name:
                    name += " "
                name += word
        return name

    def _get_all_plugins_bases(self):
        """Return grouped and sorted all plugins bases."""
        bases = []
        bases_names = []
        for p in discover.itersubclasses(plugin.Plugin):
            base_ref = getattr(p, "base_ref", None)
            if base_ref == p:
                name = self._parse_class_name(p)
                if name in bases_names:
                    raise Exception("Two base classes with same name '%s' are "
                                    "detected." % name)
                bases_names.append(name)
                category_of_base = "Common"
                for cname, cbases in CATEGORIES.items():
                    if name in cbases:
                        category_of_base = cname

                bases.append((category_of_base, name, p))
        return sorted(bases)

    def run(self):
        plugins.load()
        bases = self._get_all_plugins_bases()
        if "base_cls" in self.options:
            for _category_name, base_name, base_cls in bases:
                if base_name == self.options["base_cls"]:
                    return self._make_plugin_base_section(base_cls)
            raise Exception("Failed to generate plugins reference for '%s'"
                            " plugin base." % self.options["base_cls"])

        categories = {}

        for category_name, base_name, base_cls in bases:
            # FIXME(andreykurilin): do not ignore anything
            if base_name in IGNORED_BASES:
                continue
            if category_name not in categories:
                categories[category_name] = category(category_name)
            category_of_base = categories[category_name]
            category_of_base.append(self._make_plugin_base_section(base_cls,
                                                                   base_name))
        return [content for _name, content in sorted(categories.items())]


def setup(app):
    plugins.load()
    app.add_directive("generate_plugin_reference", PluginsReferenceDirective)
