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
"""

from __future__ import print_function

from rally.cmd import cliutils
from rally import searchutils
from rally import utils


class InfoCommands(object):

    @cliutils.args("--query", dest="query", type=str, help="Search query.")
    def find(self, query):
        """Search for an entity that matches the query and print info about it.

        :param query: search query.
        """
        scenario_group = searchutils.find_benchmark_scenario_group(query)
        if scenario_group:
            print("%s (benchmark scenario group).\n" % scenario_group.__name__)
            # TODO(msdubov): Provide all scenario classes with docstrings.
            doc = utils.format_docstring(scenario_group.__doc__)
            print(doc)
            return

        scenario = searchutils.find_benchmark_scenario(query)
        if scenario:
            print("%(scenario_group)s.%(scenario_name)s "
                  "(benchmark scenario).\n" %
                  {"scenario_group": utils.get_method_class(scenario).__name__,
                   "scenario_name": scenario.__name__})
            doc = utils.parse_docstring(scenario.__doc__)
            print(doc["short_description"] + "\n")
            if doc["long_description"]:
                print(doc["long_description"] + "\n")
            if doc["params"]:
                print("Parameters:")
                for param in doc["params"]:
                    print("    - %(name)s: %(doc)s" % param)
            if doc["returns"]:
                print("Returns: %s" % doc["returns"])
            return

        print("Failed to find any docs for query: '%s'" % query)
        return 1
