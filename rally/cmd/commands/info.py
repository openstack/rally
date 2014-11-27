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

    $ rally info find create_meter_and_get_stats
    CeilometerStats.create_meter_and_get_stats (benchmark scenario).

    Test creating a meter and fetching its statistics.

    Meter is first created and then statistics is fetched for the same
    using GET /v2/meters/(meter_name)/statistics.
    Parameters:
        - name_length: length of generated (random) part of meter name
        - kwargs: contains optional arguments to create a meter

    $ rally info find Authenticate
    Authenticate (benchmark scenario group).

    This class should contain authentication mechanism.

    Benchmark scenarios:
    ---------------------------------------------------------
     Name                            Description
    ---------------------------------------------------------
     Authenticate.keystone
     Authenticate.validate_cinder    Check Cinder Client ...
     Authenticate.validate_glance    Check Glance Client ...
     Authenticate.validate_heat      Check Heat Client ...

    $ rally info find some_non_existing_benchmark

    Failed to find any docs for query: 'some_non_existing_benchmark'
"""

from __future__ import print_function

from rally.benchmark.scenarios import base as scenario_base
from rally.benchmark.sla import base as sla_base
from rally.cmd import cliutils
from rally import deploy
from rally.deploy import serverprovider
from rally import exceptions
from rally import utils


class InfoCommands(object):
    """This command allows you to get quick doc of some rally entities.

    Available for scenario groups, scenarios, SLA, deploy engines and
    server providers.

    Usage:
        $ rally info find <query>

    To see lists of entities you can query docs for, type one of the following:
        $ rally info BenchmarkScenarios
        $ rally info SLA
        $ rally info DeployEngines
        $ rally info ServerProviders
    """

    @cliutils.args("--query", dest="query", type=str, help="Search query.")
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

    def list(self):
        """List main entities in Rally for which rally info find works.

        Lists benchmark scenario groups, deploy engines and server providers.
        """
        self.BenchmarkScenarios()
        self.SLA()
        self.DeployEngines()
        self.ServerProviders()

    def BenchmarkScenarios(self):
        """List benchmark scenarios available in Rally."""
        scenarios = self._get_descriptions(scenario_base.Scenario)
        info = self._compose_table("Benchmark scenario groups", scenarios)
        info += ("  To get information about benchmark scenarios inside "
                 "each scenario group, run:\n"
                 "      $ rally info find <ScenarioGroupName>\n\n")
        print(info)

    def SLA(self):
        """List server providers available in Rally."""
        sla = self._get_descriptions(sla_base.SLA)
        info = self._compose_table("SLA", sla)
        print(info)

    def DeployEngines(self):
        """List deploy engines available in Rally."""
        engines = self._get_descriptions(deploy.EngineFactory)
        info = self._compose_table("Deploy engines", engines)
        print(info)

    def ServerProviders(self):
        """List server providers available in Rally."""
        providers = self._get_descriptions(serverprovider.ProviderFactory)
        info = self._compose_table("Server providers", providers)
        print(info)

    def _get_descriptions(self, base_cls):
        descriptions = []
        for entity in utils.itersubclasses(base_cls):
            name = entity.__name__
            doc = utils.parse_docstring(entity.__doc__)
            description = doc["short_description"] or ""
            descriptions.append((name, description))
        return descriptions

    def _find_info(self, query):
        return (self._get_scenario_group_info(query) or
                self._get_scenario_info(query) or
                self._get_sla_info(query) or
                self._get_deploy_engine_info(query) or
                self._get_server_provider_info(query))

    def _find_substitution(self, query):
        max_distance = min(3, len(query) / 4)
        scenarios = scenario_base.Scenario.list_benchmark_scenarios()
        scenario_groups = list(set(s.split(".")[0] for s in scenarios))
        scenario_methods = list(set(s.split(".")[1] for s in scenarios))
        deploy_engines = [cls.__name__ for cls in utils.itersubclasses(
                          deploy.EngineFactory)]
        server_providers = [cls.__name__ for cls in utils.itersubclasses(
                            serverprovider.ProviderFactory)]
        candidates = (scenarios + scenario_groups + scenario_methods +
                      deploy_engines + server_providers)
        suggestions = []
        # NOTE(msdubov): Incorrect query may either have typos or be truncated.
        for candidate in candidates:
            if ((utils.distance(query, candidate) <= max_distance or
                 candidate.startswith(query))):
                suggestions.append(candidate)
        return suggestions

    def _get_scenario_group_info(self, query):
        try:
            scenario_group = scenario_base.Scenario.get_by_name(query)
            info = ("%s (benchmark scenario group).\n\n" %
                    scenario_group.__name__)
            info += utils.format_docstring(scenario_group.__doc__)
            info += "\nBenchmark scenarios:\n"
            scenarios = scenario_group.list_benchmark_scenarios()
            first_column_len = max(map(len, scenarios)) + cliutils.MARGIN
            second_column_len = len("Description") + cliutils.MARGIN
            table = ""
            for scenario_name in scenarios:
                cls, method_name = scenario_name.split(".")
                if hasattr(scenario_group, method_name):
                    scenario = getattr(scenario_group, method_name)
                    doc = utils.parse_docstring(scenario.__doc__)
                    descr = doc["short_description"] or ""
                    second_column_len = max(second_column_len,
                                            len(descr) + cliutils.MARGIN)
                    table += " " + scenario_name
                    table += " " * (first_column_len - len(scenario_name))
                    table += descr + "\n"
            info += "-" * (first_column_len + second_column_len + 1) + "\n"
            info += (" Name" + " " * (first_column_len - len("Name")) +
                     "Description\n")
            info += "-" * (first_column_len + second_column_len + 1) + "\n"
            info += table
            return info
        except exceptions.NoSuchScenario:
            return None

    def _get_scenario_info(self, query):
        try:
            scenario = scenario_base.Scenario.get_scenario_by_name(query)
            scenario_group_name = utils.get_method_class(scenario).__name__
            info = ("%(scenario_group)s.%(scenario_name)s "
                    "(benchmark scenario).\n\n" %
                    {"scenario_group": scenario_group_name,
                     "scenario_name": scenario.__name__})
            doc = utils.parse_docstring(scenario.__doc__)
            if not doc["short_description"]:
                return None
            info += doc["short_description"] + "\n\n"
            if doc["long_description"]:
                info += doc["long_description"] + "\n\n"
            if doc["params"]:
                info += "Parameters:\n"
                for param in doc["params"]:
                    info += "    - %(name)s: %(doc)s" % param + "\n"
            if doc["returns"]:
                info += "Returns: %s" % doc["returns"]
            return info
        except exceptions.NoSuchScenario:
            return None

    def _get_sla_info(self, query):
        try:
            sla = sla_base.SLA.get_by_name(query)
            info = "%s (SLA).\n\n" % sla.__name__
            info += utils.format_docstring(sla.__doc__)
            return info
        except exceptions.NoSuchSLA:
            return None

    def _get_deploy_engine_info(self, query):
        try:
            deploy_engine = deploy.EngineFactory.get_by_name(query)
            info = "%s (deploy engine).\n\n" % deploy_engine.__name__
            info += utils.format_docstring(deploy_engine.__doc__)
            return info
        except exceptions.NoSuchEngine:
            return None

    def _get_server_provider_info(self, query):
        try:
            server_provider = serverprovider.ProviderFactory.get_by_name(query)
            info = "%s (server provider).\n\n" % server_provider.__name__
            info += utils.format_docstring(server_provider.__doc__)
            return info
        except exceptions.NoSuchVMProvider:
            return None

    def _compose_table(self, title, descriptions):
        table = title + ":\n"
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
        table += "\n"
        return table