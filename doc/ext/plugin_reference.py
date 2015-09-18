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
        "group": "Task plugins",
        "items": [
            {
                "name": "Scenario Runners",
                "base": "rally.task.runner:ScenarioRunner"
            },
            {
                "name": "SLAs",
                "base": "rally.task.sla:SLA"
            },
            {
                "name": "Contexts",
                "base": "rally.task.context:Context"
            },
            {
                "name": "Scenarios",
                "base": "rally.task.scenario:Scenario"
            }
        ]
    },
    {
        "group": "Deployment plugins",
        "items": [
            {
                "name": "Engines",
                "base": "rally.deployment.engine:Engine"
            },
            {
                "name": "ProviderFactory",
                "base":
                "rally.deployment.serverprovider.provider:ProviderFactory"
            }
        ]
    }
]


def make_row(data):
    row = nodes.row()
    for item in data:
        node_type, text = item
        entry = nodes.entry()
        entry.append(node_type(text=text))
        row.append(entry)

    return row


def make_table(data):
    table = nodes.table()
    table_group = nodes.tgroup()

    for w in data["colwidth"]:
        table_group.append(nodes.colspec(colwidth=w))

    table_head = nodes.thead()
    table_head.append(make_row(data["headers"]))
    table_group.append(table_head)

    table_body = nodes.tbody()
    for row in data["rows"]:
        table_body.append(make_row(row))
    table_group.append(table_body)

    table.append(table_group)

    return table


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

        return [
            [nodes.inline, p.get_name()],
            [nodes.doctest_block, "\n\n".join(description)]
        ]

    return {
        "headers": zip([nodes.inline] * 2,
                       ["name", "description"]),
        "colwidth": [1, 1],
        "rows": map(process_plugin, plugin_base.get_all())
    }


def make_plugin_section(plugin_group):
    elements = []

    for item in plugin_group["items"]:
        elements.append(nodes.rubric(text=item["name"]))
        elements.append(make_table(_get_plugin_info(item)))

    return elements


class PluginReferenceDirective(rst.Directive):

    def run(self):
        content = []
        for i in range(len(DATA)):
            content.append(nodes.subtitle(text=DATA[i]["group"]))
            content.extend(make_plugin_section(DATA[i]))

        return content


def setup(app):
    plugins.load()
    app.add_directive('generate_plugin_reference', PluginReferenceDirective)
