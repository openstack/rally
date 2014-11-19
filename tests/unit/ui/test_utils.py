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


import mock

from rally.ui import utils
from tests.unit import test


class PlotTestCase(test.TestCase):

    def test_lookup(self):
        self.assertIsInstance(utils.lookup, utils.mako.lookup.TemplateLookup)
        self.assertIsInstance(utils.lookup.get_template("/base.mako"),
                              utils.mako.lookup.Template)
        self.assertRaises(
            utils.mako.lookup.exceptions.TopLevelLookupException,
            utils.lookup.get_template, "absent_template")

    @mock.patch("rally.ui.utils.lookup")
    def test_get_template(self, mock_lookup):
        mock_lookup.get_template.return_value = "foo_template"
        template = utils.get_template("foo_path")
        self.assertEqual(template, "foo_template")
        mock_lookup.get_template.assert_called_once_with("foo_path")
