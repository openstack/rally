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

import re
import typing as t

from docutils.parsers import rst

from rally import plugins
from rally.common.plugin import discover
from rally.common.plugin import plugin
from rally.utils import rstutils

from . import utils


CATEGORIES = {
    "Environment Component": ["Platform"],
    "Task Component": [
        "Chart",
        "Context",
        "Hook Action",
        "Hook Trigger",
        "Task Exporter",
        "SLA",
        "Scenario",
        "Scenario Runner",
        "Validator",
    ],
    "Verification Component": [
        "Verifier Context",
        "Verification Reporter",
        "Verifier Manager",
    ],
}

# NOTE(andreykurilin): these bases are mostly internal plugins that are not
# exposed to end users (rally consumers), so they are not displayed in the
# plugins reference
IGNORED_BASES = ["Resource Type"]


class PluginsReferenceDirective(rst.Directive):
    optional_arguments = 1
    option_spec = {"base_cls": str}

    def _make_plugin_base_section(
        self, base_cls: type[plugin.Plugin], base_name: str | None = None
    ) -> list:
        plugins_cls = sorted(
            (p for p in base_cls.get_all()
             if not p._meta_get("hidden", False)),
            key=lambda p: p.get_name()
        )
        if not plugins_cls:
            return []

        if base_name:
            title = (
                f"{base_name}s"
                if base_name[-1] != "y"
                else f"{base_name[:-1]}ies"
            )
            subcategory_obj = utils.subcategory(title)
        else:
            subcategory_obj = []
        for p in plugins_cls:
            subcategory_obj.extend(
                utils.parse_text(
                    rstutils.make_plugin_section(p, base_name=base_name),
                    source=f"<plugin {p.get_name()}@{p.get_platform()} "
                    f"({p.__module__})>",
                )
            )
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
    def _get_all_plugins_bases(self) -> dict[str, type[plugin.Plugin]]:
        """Return all plugins bases by their names."""
        bases = {}
        in_tree_bases: set[str] = set()
        for p in discover.itersubclasses(plugin.Plugin):
            base_ref = getattr(p, "base_ref", None)
            if base_ref == p:
                name = self._parse_class_name(p)
                if name in bases:
                    raise Exception(
                        f"Two base classes with same name "
                        f"'{name}' are detected."
                    )
                bases[name] = p
                if p.__module__.startswith("rally."):
                    in_tree_bases.add(name)

        known = set(IGNORED_BASES)
        for names in CATEGORIES.values():
            known.update(names)
        unknown = sorted(set(in_tree_bases) - known)
        if unknown:
            raise Exception(
                f"Plugin base(s) {', '.join(unknown)} should be added to "
                f"CATEGORIES or IGNORED_BASES."
            )
        missing = sorted(known - set(in_tree_bases))
        if missing:
            raise Exception(
                f"Plugin base(s) {', '.join(missing)} from CATEGORIES or "
                f"IGNORED_BASES do not exist."
            )
        return bases

    def run(self) -> list:
        bases = self._get_all_plugins_bases()
        if "base_cls" in self.options:
            base_name = self.options["base_cls"]
            if base_name not in bases:
                raise Exception(
                    f"Failed to generate plugins reference for "
                    f"'{base_name}' plugin base."
                )
            return self._make_plugin_base_section(bases[base_name])

        categories = []
        for category_name, base_names in sorted(CATEGORIES.items()):
            category_obj = None
            for base_name in sorted(base_names):
                base_cls = bases[base_name]
                plugins_details = self._make_plugin_base_section(
                    base_cls, base_name
                )
                if not plugins_details:
                    continue
                if category_obj is None:
                    category_obj = utils.category(category_name)
                category_obj.append(plugins_details)

            if category_obj is not None:
                categories.append(category_obj)
        return categories


def setup(app: t.Any) -> None:
    plugins.load()
    app.add_directive("generate_plugin_reference", PluginsReferenceDirective)
