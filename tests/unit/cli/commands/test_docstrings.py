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

import inspect

from rally.cli import main
from rally.common.plugin import info
from tests.unit import test


class DocstringsTestCase(test.TestCase):

    @staticmethod
    def _get_all_category_methods(category):
        all_methods = inspect.getmembers(
            category,
            predicate=lambda x: inspect.ismethod(x) or inspect.isfunction(x))
        return [m for m in all_methods if not m[0].startswith("_")]

    def test_params(self):
        for category in main.categories.values():
            all_methods = self._get_all_category_methods(category)
            for name, method in all_methods:
                m_info = info.parse_docstring(method.__doc__)
                if m_info["params"]:
                    print(m_info)
                    self.fail("The description of parameters for CLI methods "
                              "should be transmitted as a 'help' argument of "
                              "`rally.cli.cliutils.arg` decorator. You should "
                              "remove descriptions from docstring of "
                              "`%s.%s.%s`" % (category.__module__,
                                              category.__class__,
                                              name))
