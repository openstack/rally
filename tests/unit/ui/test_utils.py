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

import mako
import mock

from rally.ui import utils
from tests.unit import test


class PlotTestCase(test.TestCase):

    def test_get_template(self):
        self.assertIsInstance(utils.get_template("task/report.mako"),
                              mako.template.Template)

    @mock.patch("rally.ui.utils.get_template")
    def test_main(self, mock_get_template):
        utils.main("render", "somepath", "a=1", "b=2")

        mock_get_template.assert_called_once_with("somepath")
        mock_get_template.return_value.render.assert_called_once_with(
            a="1", b="2"
        )

    def test_main_bad_input(self):
        self.assertRaises(ValueError, utils.main)
        self.assertRaises(ValueError, utils.main, "not_a_render")
        self.assertRaises(ValueError, utils.main, "render")
        self.assertRaises(ValueError, utils.main, "render", "path", "a 1")
