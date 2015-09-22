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

from docutils import nodes
from docutils.parsers import rst

from oslo_utils import importutils

from rally import plugins

DATA = [
    {
        "group": "task",
        "items": [
            {
                "name": "scenario runner",
                "base": "rally.task.runner:ScenarioRunner"
            },
            {
                "name": "SLA",
                "base": "rally.task.sla:SLA"
            },
            {
                "name": "context",
                "base": "rally.task.context:Context"
            },
            {
                "name": "scenario",
                "base": "rally.task.scenario:Scenario"
            }
        ]
    },
    {
        "group": "deployment",
        "items": [
            {
                "name": "engine",
                "base": "rally.deployment.engine:Engine"
            },
            {
                "name": "server provider",
                "base":
                "rally.deployment.serverprovider.provider:ProviderFactory"
            }
        ]
    }
]


def _make_pretty_parameters(parameters):
    if not parameters:
        return ""

    result = "PARAMETERS:\n"
    for p in parameters:
        result += "* %(name)s: %(doc)s\n" % p
    return result


def _get_plugin_info(plugin_group_item):
    module, cls = plugin_group_item["base"].split(":")
    plugin_base = getattr(importutils.import_module(module), cls)

    def process_plugin(p):
        info = p.get_info()

        description = [info["title"] or ""]
        if info["description"]:
            description.append(info["description"])
        if info["parameters"]:
            description.append(_make_pretty_parameters(info["parameters"]))
        if info["returns"]:
            description.append("RETURNS:\n%s" % info["returns"])
        description.append("MODULE:\n%s" % info["module"])

        return {
            "name": p.get_name(),
            "description": "\n\n".join(description)
        }

    return map(process_plugin, plugin_base.get_all())


def make_plugin_section(plugin_group):
    elements = []

    for item in plugin_group["items"]:
        name = item["name"].title() if "SLA" != item["name"] else item["name"]
        elements.append(nodes.subtitle(
            text="%ss [%s]" % (name, plugin_group["group"])))

        for p in _get_plugin_info(item):
            elements.append(nodes.rubric(
                text="%s [%s]" % (p["name"], item["name"])))

            elements.append(nodes.doctest_block(text=p["description"]))

    return elements


class PluginReferenceDirective(rst.Directive):

    def run(self):
        content = []
        for i in range(len(DATA)):
            content.extend(make_plugin_section(DATA[i]))

        return content


def setup(app):
    plugins.load()
    app.add_directive('generate_plugin_reference', PluginReferenceDirective)
