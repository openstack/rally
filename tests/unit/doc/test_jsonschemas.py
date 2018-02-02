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
import json

from rally.common.plugin import plugin
from rally import plugins
from tests.unit import test


class ConfigSchemasTestCase(test.TestCase):

    OBJECT_TYPE_KEYS = {"$schema", "type", "description", "required",
                        "properties", "patternProperties",
                        "minProperties", "maxProperties",
                        "additionalProperties", "oneOf", "anyOf"}
    ARRAY_TYPE_KEYS = {"$schema", "type", "description", "items",
                       "uniqueItems", "minItems", "maxItems",
                       "additionalItems"}
    NUMBER_TYPE_KEYS = {"$schema", "type", "description", "minimum", "maximum",
                        "exclusiveMinimum"}
    STRING_TYPE_KEYS = {"$schema", "type", "description", "pattern"}

    def fail(self, p, schema, msg):
        super(ConfigSchemasTestCase, self).fail(
            "Config schema of plugin '%s' (%s) is invalid. %s "
            "Schema: \n%s" % (p.get_name(),
                              "%s.%s" % (p.__module__, p.__name__),
                              msg,
                              json.dumps(schema, indent=3)))

    def _check_anyOf_or_oneOf(self, p, schema, definitions):
        if "anyOf" in schema or "oneOf" in schema:
            key = "anyOf" if "anyOf" in schema else "oneOf"
            for case in schema[key]:
                if "description" not in case and "$ref" not in case:
                    self.fail(p, schema, "Each case of '%s' should have "
                                         "description." % key)
                full_schema = copy.deepcopy(schema)
                full_schema.pop(key)
                for k, v in case.items():
                    full_schema[k] = v
                self._check_item(p, full_schema, definitions)

    def _check_object_type(self, p, schema, definitions):
        unexpected_keys = set(schema.keys()) - self.OBJECT_TYPE_KEYS
        if "definitions" in unexpected_keys:
            # TODO(andreykurilin): do not use definitions since it is a hard
            #     task to parse and display them
            unexpected_keys -= {"definitions"}
        if unexpected_keys:
            self.fail(p, schema, ("Found unexpected key(s) for object type: "
                                  "%s." % ", ".join(unexpected_keys)))
        if "additionalProperties" not in schema:
            self.fail(p, schema,
                      "'additionalProperties' is required field for objects. "
                      "Specify `'additionalProperties': True` explicitly to "
                      "accept not validated properties.")

        if "patternProperties" in schema:
            if "properties" in schema:
                self.fail(p, schema, "Usage both 'patternProperties' and "
                                     "'properties' in one time is restricted.")
            if not isinstance(schema["patternProperties"], dict):
                self.fail(p, schema, "Field 'patternProperties' should be a "
                                     "dict.")
            for pattern, description in schema["patternProperties"].items():
                self._check_item(p, description, definitions)

        if "properties" in schema:
            for property_name, description in schema["properties"].items():
                self._check_item(p, description, definitions)

    def _check_array_type(self, p, schema, definitions):
        unexpected_keys = set(schema.keys()) - self.ARRAY_TYPE_KEYS
        if "additionalProperties" in unexpected_keys:
            self.fail(p, schema, "Array type doesn't support "
                                 "'additionalProperties' field.")

        if unexpected_keys:
            self.fail(p, schema, ("Found unexpected key(s) for array type: "
                                  "%s." % ", ".join(unexpected_keys)))

        if "items" not in schema:
            self.fail(p, schema, "Expected items of array type should be "
                                 "described via 'items' field.")

        if isinstance(schema["items"], dict):
            self._check_item(p, schema["items"], definitions)
            if "additionalItems" in schema:
                self.fail(p, schema, "When items is a single schema, the "
                                     "`additionalItems` keyword is "
                                     "meaningless, and it should not be used.")
        elif isinstance(schema["items"], list):
            for item in schema["items"]:
                self._check_item(p, item, definitions)
        else:
            self.fail(p, schema, ("Field 'items' of array type should be a "
                                  "list or a dict, but not '%s'" %
                                  type(schema["items"])))

    def _check_string_type(self, p, schema):
        unexpected_keys = set(schema.keys()) - self.STRING_TYPE_KEYS
        if unexpected_keys:
            self.fail(p, schema, ("Found unexpected key(s) for string type: "
                                  "%s." % ", ".join(unexpected_keys)))

    def _check_number_type(self, p, schema):
        unexpected_keys = set(schema.keys()) - self.NUMBER_TYPE_KEYS
        if unexpected_keys:
            self.fail(p, schema, ("Found unexpected key(s) for integer/number "
                                  "type: %s." % ", ".join(unexpected_keys)))

    def _check_simpliest_types(self, p, schema, type_name):
        unexpected_keys = set(schema.keys()) - {"type", "description"}
        if unexpected_keys:
            self.fail(p, schema, ("Found unexpected key(s) for %s type: "
                                  "%s." % (type_name,
                                           ", ".join(unexpected_keys))))

    def _check_item(self, p, schema, definitions):
        if "type" in schema or "anyOf" in schema or "oneOf" in schema:
            if "anyOf" in schema or "oneOf" in schema:
                self._check_anyOf_or_oneOf(p, schema, definitions)
            elif "type" in schema:
                if schema["type"] == "object":
                    self._check_object_type(p, schema, definitions)
                elif schema["type"] == "array":
                    self._check_array_type(p, schema, definitions)
                elif schema["type"] == "string":
                    self._check_string_type(p, schema)
                elif schema["type"] in ("number", "integer"):
                    self._check_number_type(p, schema)
                elif schema["type"] in ("boolean", "null"):
                    self._check_simpliest_types(p, schema, schema["type"])
                elif isinstance(schema["type"], list):
                    self._check_simpliest_types(p, schema, "mixed")
                else:
                    self.fail(p, schema,
                              "Wrong type is used: %s" % schema["type"])
        elif "enum" in schema:
            pass
        elif schema == {}:
            # NOTE(andreykurilin): an empty dict means that the user can
            #   transmit whatever he wants in whatever he wants format. It is
            #   not the case which we want to support.
            self.fail(p, schema, "Empty schema is not allowed.")
        elif "$ref" in schema:
            definition_name = schema["$ref"].replace("#/definitions/", "")
            if definition_name not in definitions:
                self.fail(p, schema,
                          "Definition '%s' is not found." % definition_name)
        else:
            self.fail(p, schema, "Wrong format.")

    @plugins.ensure_plugins_are_loaded
    def test_schema_is_valid(self):
        for p in plugin.Plugin.get_all():
            if not hasattr(p, "CONFIG_SCHEMA") or "tests.unit" in p.__module__:
                continue
            # allow only top level definitions
            definitions = p.CONFIG_SCHEMA.get("definitions", {})
            for definition in definitions.values():
                self._check_item(p, definition, definitions)

            # check schema itself
            self._check_item(p, p.CONFIG_SCHEMA, definitions)
