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

import testtools

from tests.functional import utils


class PluginTestCase(testtools.TestCase):

    def test_show_one(self):
        rally = utils.Rally()
        result = rally("plugin show Dummy.dummy")
        self.assertIn("NAME", result)
        self.assertIn("PLATFORM", result)
        self.assertIn("Dummy.dummy", result)
        self.assertIn("MODULE", result)

    def test_show_multiple(self):
        rally = utils.Rally()
        result = self.assertRaises(utils.RallyCliError,
                                   rally, "plugin show Dummy")
        self.assertIn("Multiple plugins found:", result.output)
        self.assertIn("Dummy.dummy", result.output)
        self.assertIn("Dummy.dummy_exception", result.output)
        self.assertIn("Dummy.dummy_random_fail_in_atomic", result.output)

    def test_show_not_found(self):
        rally = utils.Rally()
        name = "Dummy666666"
        result = self.assertRaises(utils.RallyCliError,
                                   rally, "plugin show %s" % name)
        self.assertIn("Plugin %s not found" % name, result.output)

    def test_show_not_found_in_specific_platform(self):
        rally = utils.Rally()
        name = "Dummy"
        platform = "non_existing"
        result = self.assertRaises(
            utils.RallyCliError,
            rally, "plugin show --name %(name)s --platform %(platform)s"
                   % {"name": name, "platform": platform})
        self.assertIn(
            "Plugin %(name)s@%(platform)s not found"
            % {"name": name, "platform": platform},
            result.output)

    def test_list(self):
        rally = utils.Rally()
        result = rally("plugin list Dummy")
        self.assertIn("Dummy.dummy", result)
        self.assertIn("Dummy.dummy_exception", result)
        self.assertIn("Dummy.dummy_random_fail_in_atomic", result)

    def test_list_not_found_platform(self):
        rally = utils.Rally()
        result = rally("plugin list --platform some")
        self.assertIn("Platform some not found", result)

    def test_list_not_found_name(self):
        rally = utils.Rally()
        result = rally("plugin list Dummy2222")
        self.assertIn("Plugin Dummy2222 not found", result)
