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
from rally.benchmark import sla
from rally.common.plugin import discover
from rally.common import utils
from rally.deploy import engine
from rally.deploy.serverprovider import provider
from tests.unit import test


class DocstringsTestCase(test.TestCase):

    def _assert_class_has_docstrings(self, obj, long_description=True):
        if not obj.__module__.startswith("rally."):
            return

        self.assertIsNotNone(obj.__doc__,
                             "%s doesn't have a class-level docstring." %
                             obj)
        doc = utils.parse_docstring(obj.__doc__)
        self.assertIsNotNone(
            doc["short_description"],
            "Docstring for %s should have a one-line description." % obj)
        if long_description:
            self.assertIsNotNone(
                doc["long_description"],
                "Docstring for %s should have a multi-line description." % obj)

    def test_all_scenarios_have_docstrings(self):
        ignored_params = ["self", "scenario_obj"]
        for scenario_group in discover.itersubclasses(base.Scenario):
            if scenario_group.__module__.startswith("tests."):
                continue

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
                    params_count = scenario.__code__.co_argcount
                    params = scenario.__code__.co_varnames[:params_count]
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
        for scenario_group in discover.itersubclasses(base.Scenario):
            self._assert_class_has_docstrings(scenario_group,
                                              long_description=False)

    def test_all_deploy_engines_have_docstrings(self):
        for deploy_engine in engine.EngineFactory.get_all():
            self._assert_class_has_docstrings(deploy_engine)

    def test_all_server_providers_have_docstrings(self):
        for _provider in provider.ProviderFactory.get_all():
            self._assert_class_has_docstrings(_provider)

    def test_all_SLA_have_docstrings(self):
        for s in discover.itersubclasses(sla.SLA):
            self._assert_class_has_docstrings(s, long_description=False)
