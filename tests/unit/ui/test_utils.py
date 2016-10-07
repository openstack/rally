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

import jinja2

from rally.ui import utils
from tests.unit import test


class ModuleTestCase(test.TestCase):

    def test_get_template(self):
        template = utils.get_template("base.html")
        self.assertIsInstance(template,
                              jinja2.environment.Template)
        self.assertEqual("base.html", template.name)
        self.assertIn("include_raw_file", template.globals)

    def test_get_template_raises(self):
        self.assertRaises(jinja2.exceptions.TemplateNotFound,
                          utils.get_template, "nonexistent")
