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

""" Rally entities discovery by queries. """

from rally.benchmark.scenarios import base as scenarios_base
from rally import exceptions
from rally import utils


def find_benchmark_scenario_group(query):
    """Find a scenario class by query.

    :param query: string with the name of the class being searched.
    :returns: class object or None if the query doesn't match any
              scenario class.
    """
    try:
        # TODO(msdubov): support approximate string matching
        #                (here and in other find_* methods).
        return scenarios_base.Scenario.get_by_name(query)
    except exceptions.NoSuchScenario:
        return None


def find_benchmark_scenario(query):
    """Find a scenario method by query.

    :param query: string with the name of the benchmark scenario being
                  searched. It can be either a full name (e.g,
                  'NovaServers.boot_server') or just a method name (e.g.,
                  'boot_server')
    :returns: method object or None if the query doesn't match any
              scenario method.
    """
    if "." in query:
        scenario_group, scenario_name = query.split(".", 1)
    else:
        scenario_group = None
        scenario_name = query

    if scenario_group:
        scenario_cls = find_benchmark_scenario_group(scenario_group)
        if hasattr(scenario_cls, scenario_name):
            return getattr(scenario_cls, scenario_name)
        else:
            return None
    else:
        for scenario_cls in utils.itersubclasses(scenarios_base.Scenario):
            if scenario_name in dir(scenario_cls):
                return getattr(scenario_cls, scenario_name)
        return None
