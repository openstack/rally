# Copyright 2014: Mirantis Inc.
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

""" Rally command: info

Samples:

    $ rally info find CeilometerStats.create_meter_and_get_stats
    CeilometerStats.create_meter_and_get_stats (benchmark scenario).

    Test creating a meter and fetching its statistics.

    Meter is first created and then statistics is fetched for the same
    using GET /v2/meters/(meter_name)/statistics.
    Parameters:
        - name_length: length of generated (random) part of meter name
        - kwargs: contains optional arguments to create a meter

    $ rally info find some_non_existing_benchmark

    Failed to find any docs for query: 'some_non_existing_benchmark'
"""

from __future__ import print_function

import inspect

from rally.cli import cliutils
from rally.common.plugin import info
from rally.common import utils
from rally.deployment import engine
from rally.deployment.serverprovider import provider
from rally import exceptions
from rally import plugins
from rally.task import scenario
from rally.task import sla


class InfoCommands(object):
    """This command allows you to get quick doc of some rally entities.

    Available for scenario groups, scenarios, SLA, deploy engines and
    server providers.

    Usage:
        $ rally info find <query>

    To get information about main concepts of Rally as well as to list entities
    you can query docs for, type one of the following:
        $ rally info BenchmarkScenarios
        $ rally info SLA
        $ rally info DeploymentEngines
        $ rally info ServerProviders
    """

    @cliutils.args("--query", dest="query", type=str, help="Search query.")
    @plugins.ensure_plugins_are_loaded
    def find(self, query):
        """Search for an entity that matches the query and print info about it.

        :param query: search query.
        """

        info = self._find_info(query)

        if info:
            print(info)
        else:
            substitutions = self._find_substitution(query)
            if len(substitutions) == 1:
                print(self._find_info(substitutions[0]))
            else:
                print("Failed to find any docs for query: '%s'" % query)
                if substitutions:
                    print("Did you mean one of these?\n\t%s" %
                          "\n\t".join(substitutions))
                return 1

    @plugins.ensure_plugins_are_loaded
    def list(self):
        """List main entities in Rally for which rally info find works.

        Lists task scenario groups, deploy engines and server providers.
        """
        self.BenchmarkScenarios()
        self.SLA()
        self.DeploymentEngines()
        self.ServerProviders()

    @plugins.ensure_plugins_are_loaded
    def BenchmarkScenarios(self):
        """Get information about benchmark scenarios available in Rally."""
        scenarios = self._get_descriptions(scenario.Scenario)
        info = (self._make_header("Rally - Task scenarios") +
                "\n\n"
                "Task scenarios are what Rally actually uses to test "
                "the performance of an OpenStack deployment.\nEach Task "
                "scenario implements a sequence of atomic operations "
                "(server calls) to simulate\ninteresing user/operator/"
                "client activity in some typical use case, usually that of "
                "a specific OpenStack\nproject. Iterative execution of this "
                "sequence produces some kind of load on the target cloud.\n"
                "Task scenarios play the role of building blocks in "
                "task configuration files."
                "\n\n" +
                self._compose_table("List of Task scenarios", scenarios) +
                "To get information about benchmark scenarios: "
                "  $ rally info find <scenario_name>\n\n")
        print(info)

    @plugins.ensure_plugins_are_loaded
    def SLA(self):
        """Get information about SLA available in Rally."""
        slas = self._get_descriptions(sla.SLA)
        # NOTE(msdubov): Add config option names to the "Name" column
        info = (self._make_header("Rally - SLA checks "
                                  "(Service-Level Agreements)") +
                "\n\n"
                "SLA in Rally enable quick and easy checks of "
                "whether the results of a particular\nbenchmark task have "
                "passed certain success criteria."
                "\n\n"
                "SLA checks can be configured in the 'sla' section of "
                "benchmark task configuration\nfiles, used to launch new "
                "tasks by the 'rally task start <config_file>' command.\n"
                "For each SLA check you would like to use, you should put "
                "its name as a key and the\ntarget check parameter as an "
                "associated value, e.g.:\n\n"
                "  sla:\n"
                "    max_seconds_per_iteration: 4\n"
                "    failure_rate:\n"
                "      max: 1"
                "\n\n" +
                self._compose_table("List of SLA checks", slas) +
                "To get information about specific SLA checks, run:\n"
                "  $ rally info find <sla_check_name>\n")
        print(info)

    @plugins.ensure_plugins_are_loaded
    def DeploymentEngines(self):
        """Get information about deploy engines available in Rally."""
        engines = self._get_descriptions(engine.Engine)
        info = (self._make_header("Rally - Deployment engines") +
                "\n\n"
                "Rally is an OpenStack benchmarking system. Before starting "
                "benchmarking with Rally,\nyou obviously have either to "
                "deploy a new OpenStack cloud or to register an existing\n"
                "one in Rally. Deployment engines in Rally are essentially "
                "plugins that control the\nprocess of deploying some "
                "OpenStack distribution, say, with DevStack or FUEL, and\n"
                "register these deployments in Rally before any benchmarking "
                "procedures against them\ncan take place."
                "\n\n"
                "A typical use case in Rally would be when you first "
                "register a deployment using the\n'rally deployment create' "
                "command and then reference this deployment by uuid "
                "when\nstarting a benchmark task with 'rally task start'. "
                "The 'rally deployment create'\ncommand awaits a deployment "
                "configuration file as its parameter. This file may look "
                "like:\n"
                "{\n"
                "  \"type\": \"ExistingCloud\",\n"
                "  \"auth_url\": \"http://example.net:5000/v2.0/\",\n"
                "  \"admin\": { <credentials> },\n"
                "  ...\n"
                "}"
                "\n\n" +
                self._compose_table("List of Deployment engines", engines) +
                "To get information about specific Deployment engines, run:\n"
                "  $ rally info find <DeploymentEngineName>\n")
        print(info)

    @plugins.ensure_plugins_are_loaded
    def ServerProviders(self):
        """Get information about server providers available in Rally."""
        providers = self._get_descriptions(provider.ProviderFactory)
        info = (self._make_header("Rally - Server providers") +
                "\n\n"
                "Rally is an OpenStack benchmarking system. Before starting "
                "benchmarking with Rally,\nyou obviously have either to "
                "deploy a new OpenStack cloud or to register an existing\n"
                "one in Rally with one of the Deployment engines. These "
                "deployment engines, in turn,\nmay need Server "
                "providers to manage virtual machines used for "
                "OpenStack deployment\nand its following benchmarking. The "
                "key feature of server providers is that they\nprovide a "
                "unified interface for interacting with different "
                "virtualization\ntechnologies (LXS, Virsh etc.)."
                "\n\n"
                "Server providers are usually referenced in deployment "
                "configuration files\npassed to the 'rally deployment create'"
                " command, e.g.:\n"
                "{\n"
                "  \"type\": \"DevstackEngine\",\n"
                "  \"provider\": {\n"
                "  \"type\": \"ExistingServers\",\n"
                "  \"credentials\": [{\"user\": \"root\",\n"
                "                     \"host\": \"10.2.0.8\"}]\n"
                "  }\n"
                "}"
                "\n\n" +
                self._compose_table("List of Server providers", providers) +
                "To get information about specific Server providers, run:\n"
                "  $ rally info find <ServerProviderName>\n")
        print(info)

    def _get_descriptions(self, base_cls):
        descriptions = []
        for entity in base_cls.get_all():
            name = entity.get_name()
            doc = info.parse_docstring(entity.__doc__)
            description = doc["short_description"] or ""
            descriptions.append((name, description))
        descriptions.sort(key=lambda d: d[0])
        return descriptions

    def _find_info(self, query):
        return (self._get_scenario_info(query) or
                self._get_sla_info(query) or
                self._get_deploy_engine_info(query) or
                self._get_server_provider_info(query))

    def _find_substitution(self, query):
        max_distance = min(3, len(query) / 4)
        scenarios = [s.get_name() for s in scenario.Scenario.get_all()]
        sla_info = [cls.get_name() for cls in sla.SLA.get_all()]
        deploy_engines = [cls.get_name() for cls in
                          engine.Engine.get_all()]
        server_providers = [cls.get_name() for cls in
                            provider.ProviderFactory.get_all()]

        candidates = (scenarios + sla_info + deploy_engines + server_providers)
        suggestions = []
        # NOTE(msdubov): Incorrect query may either have typos or be truncated.
        for candidate in candidates:
            if ((utils.distance(query, candidate) <= max_distance or
                 query.lower() in candidate.lower())):
                suggestions.append(candidate)
        return suggestions

    def _get_scenario_info(self, query):
        try:
            scenario_inst = scenario.Scenario.get(query)
            header = "%s (task scenario)" % scenario_inst.get_name()
            result = self._make_header(header)
            result += "\n\n"
            doc = info.parse_docstring(scenario_inst.__doc__)
            if not doc["short_description"]:
                return None
            result += doc["short_description"] + "\n\n"
            if doc["long_description"]:
                result += doc["long_description"] + "\n\n"
            if doc["params"]:
                args = inspect.getargspec(scenario_inst)
                if args.defaults:
                    default_values = dict(zip(args.args[-len(args.defaults):],
                                              args.defaults))
                else:
                    default_values = {}
                result += "Parameters:\n"
                for param in doc["params"]:
                    result += "    - %(name)s: %(doc)s" % param

                    name = param["name"]
                    if name in default_values:
                        if default_values[name] is not None:
                            result += " [Default: %s]" % default_values[name]
                        else:
                            result += " [optional]"
                    result += "\n"
            if doc["returns"]:
                result += "Returns: %s" % doc["returns"]
            return result
        except exceptions.PluginNotFound:
            return None

    def _get_sla_info(self, query):
        try:
            found_sla = sla.SLA.get(query)
            header = "%s (SLA)" % found_sla.get_name()
            result = self._make_header(header)
            result += "\n\n"
            result += info.format_docstring(found_sla.__doc__) + "\n"
            return result
        except exceptions.PluginNotFound:
            return None

    def _get_deploy_engine_info(self, query):
        try:
            deploy_engine = engine.Engine.get(query)
            header = "%s (deploy engine)" % deploy_engine.get_name()
            result = self._make_header(header)
            result += "\n\n"
            result += info.format_docstring(deploy_engine.__doc__)
            return result
        except exceptions.PluginNotFound:
            return None

    def _get_server_provider_info(self, query):
        try:
            server_provider = provider.ProviderFactory.get(query)
            header = "%s (server provider)" % server_provider.get_name()
            result = self._make_header(header)
            result += "\n\n"
            result += info.format_docstring(server_provider.__doc__)
            return result
        except exceptions.PluginNotFound:
            return None

    def _make_header(self, string):
        header = "-" * (len(string) + 2) + "\n"
        header += " " + string + " \n"
        header += "-" * (len(string) + 2)
        return header

    def _compose_table(self, title, descriptions):
        table = " " + title + ":\n"
        len0 = lambda x: len(x[0])
        len1 = lambda x: len(x[1])
        first_column_len = max(map(len0, descriptions)) + cliutils.MARGIN
        second_column_len = max(map(len1, descriptions)) + cliutils.MARGIN
        table += "-" * (first_column_len + second_column_len + 1) + "\n"
        table += (" Name" + " " * (first_column_len - len("Name")) +
                  "Description\n")
        table += "-" * (first_column_len + second_column_len + 1) + "\n"
        for (name, descr) in descriptions:
            table += " " + name
            table += " " * (first_column_len - len(name))
            table += descr + "\n"
        table += "-" * (first_column_len + second_column_len + 1) + "\n"
        table += "\n"
        return table
