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

import unittest

from tests.functional import utils


class PluginTestCase(unittest.TestCase):

    def setUp(self):
        super(PluginTestCase, self).setUp()
        self.rally = utils.Rally()

    def test_show_one(self):
        result = self.rally("plugin show Dummy.dummy")
        self.assertIn("NAME", result)
        self.assertIn("NAMESPACE", result)
        self.assertIn("Dummy.dummy", result)
        self.assertIn("MODULE", result)

    def test_show_multiple(self):
        result = self.rally("plugin show Dummy")
        self.assertIn("Multiple plugins found:", result)
        self.assertIn("Dummy.dummy", result)
        self.assertIn("Dummy.dummy_exception", result)
        self.assertIn("Dummy.dummy_random_fail_in_atomic", result)

    def test_show_not_found(self):
        name = "Dummy666666"
        result = self.rally("plugin show %s" % name)
        self.assertIn("There is no plugin: %s" % name, result)

    def test_show_not_found_in_specific_namespace(self):
        name = "Dummy"
        namespace = "non_existing"
        result = self.rally(
            "plugin show --name %(name)s --namespace %(namespace)s"
            % {"name": name, "namespace": namespace})
        self.assertIn(
            "There is no plugin: %(name)s in %(namespace)s namespace"
            % {"name": name, "namespace": namespace},
            result)

    def test_list(self):
        result = self.rally("plugin list Dummy")
        self.assertIn("Dummy.dummy", result)
        self.assertIn("Dummy.dummy_exception", result)
        self.assertIn("Dummy.dummy_random_fail_in_atomic", result)

    def test_list_not_found_namespace(self):
        result = self.rally("plugin list --namespace some")
        self.assertIn("There is no plugin namespace: some", result)

    def test_list_not_found_name(self):
        result = self.rally("plugin list Dummy2222")
        self.assertIn("There is no plugin: Dummy2222", result)
