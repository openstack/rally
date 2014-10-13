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

from rally.benchmark.scenarios import base
from rally.benchmark.sla import base as sla_base
from rally import deploy
from rally.deploy import serverprovider
from rally import utils
from tests.unit import test


class DocstringsTestCase(test.TestCase):

    def test_all_scenarios_have_docstrings(self):
        ignored_params = ["self", "scenario_obj"]
        for scenario_group in utils.itersubclasses(base.Scenario):
            for method in dir(scenario_group):
                if base.Scenario.is_scenario(scenario_group, method):
                    scenario = getattr(scenario_group, method)
                    scenario_name = scenario_group.__name__ + "." + method
                    self.assertIsNotNone(scenario.__doc__,
                                         "%s doensn't have a docstring." %
                                         scenario_name)
                    doc = utils.parse_docstring(scenario.__doc__)
                    short_description = doc["short_description"]
                    self.assertIsNotNone(short_description,
                                         "Docstring for %s should have "
                                         "at least a one-line description." %
                                         scenario_name)
                    self.assertFalse(short_description.startswith("Test"),
                                     "One-line description for %s "
                                     "should be declarative and not start "
                                     "with 'Test(s) ...'" % scenario_name)
                    params_count = scenario.func_code.co_argcount
                    params = scenario.func_code.co_varnames[:params_count]
                    documented_params = [p["name"] for p in doc["params"]]
                    for param in params:
                        if param not in ignored_params:
                            self.assertIn(param, documented_params,
                                          "Docstring for %(scenario)s should "
                                          "describe the '%(param)s' parameter "
                                          "in the :param <name>: clause." %
                                          {"scenario": scenario_name,
                                           "param": param})

    def test_all_scenario_groups_have_docstrings(self):
        for scenario_group in utils.itersubclasses(base.Scenario):
            scenario_group_name = scenario_group.__name__
            self.assertIsNotNone(scenario_group.__doc__,
                                 "%s doesn't have a class-level docstring." %
                                 scenario_group_name)
            doc = utils.parse_docstring(scenario_group.__doc__)
            msg = ("Docstring for %s should have a one-line description." %
                   scenario_group_name)
            self.assertIsNotNone(doc["short_description"], msg)

    def test_all_deploy_engines_have_docstrings(self):
        for deploy_engine in utils.itersubclasses(deploy.EngineFactory):
            deploy_engine_name = deploy_engine.__name__
            self.assertIsNotNone(deploy_engine.__doc__,
                                 "%s doesn't have a class-level docstring." %
                                 deploy_engine_name)
            doc = utils.parse_docstring(deploy_engine.__doc__)
            msg = ("Docstring for %s should have a one-line description "
                   "and a detailed description." % deploy_engine_name)
            self.assertIsNotNone(doc["short_description"], msg)
            self.assertIsNotNone(doc["long_description"], msg)

    def test_all_server_providers_have_docstrings(self):
        for provider in utils.itersubclasses(serverprovider.ProviderFactory):
            provider_name = provider.__name__
            self.assertIsNotNone(provider.__doc__,
                                 "%s doesn't have a class-level docstring." %
                                 provider_name)
            doc = utils.parse_docstring(provider.__doc__)
            msg = ("Docstring for %s should have a one-line description "
                   "and a detailed description." % provider_name)
            self.assertIsNotNone(doc["short_description"], msg)
            self.assertIsNotNone(doc["long_description"], msg)

    def test_all_SLA_have_docstrings(self):
        for sla in utils.itersubclasses(sla_base.SLA):
            sla_name = sla.OPTION_NAME
            self.assertIsNotNone(sla.__doc__,
                                 "%s doesn't have a class-level docstring." %
                                 sla_name)
            doc = utils.parse_docstring(sla.__doc__)
            self.assertIsNotNone(doc["short_description"],
                                 "Docstring for %s should have a "
                                 "one-line description." % sla_name)
