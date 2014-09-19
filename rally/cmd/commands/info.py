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

    For different types of clients like Keystone.

    $ rally info find some_non_existing_benchmark

    Failed to find any docs for query: 'some_non_existing_benchmark'
"""

from __future__ import print_function

from rally.benchmark.scenarios import base as scenario_base
from rally.cmd import cliutils
from rally import deploy
from rally.deploy import serverprovider
from rally import exceptions
from rally import utils


class InfoCommands(object):

    @cliutils.args("--query", dest="query", type=str, help="Search query.")
    def find(self, query):
        """Search for an entity that matches the query and print info about it.

        :param query: search query.
        """
        info = self._find_info(query)

        if info:
            print(info)
        else:
            print("Failed to find any docs for query: '%s'" % query)
            return 1

    def _find_info(self, query):
        return (self._get_scenario_group_info(query) or
                self._get_scenario_info(query) or
                self._get_deploy_engine_info(query) or
                self._get_server_provider_info(query))

    def _get_scenario_group_info(self, query):
        try:
            scenario_group = scenario_base.Scenario.get_by_name(query)
            info = ("%s (benchmark scenario group).\n\n" %
                    scenario_group.__name__)
            info += utils.format_docstring(scenario_group.__doc__)
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
