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

from docutils.parsers import rst
import re

from rally.common.plugin import discover
from rally.common.plugin import plugin
from rally import plugins
from utils import category, subcategory, section, paragraph, parse_text


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

    @staticmethod
    def _make_pretty_parameters(parameters):
        if not parameters:
            return ""

        result = "**Parameters**:\n\n"
        for p in parameters:
            result += "* %(name)s: %(doc)s\n" % p
        return result

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

        if info["parameters"]:
            section_obj.extend(parse_text(
                self._make_pretty_parameters(info["parameters"])))
            if info["returns"]:
                section_obj.extend(parse_text(
                    "**Returns**:\n%s" % info["returns"]))
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
