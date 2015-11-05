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

import ast

from tests.unit import test
from tests.unit import test_ddt


class DDTDecoratorCheckerTestCase(test.TestCase):

    def test_pass(self):
        code = """
@ddt.ddt
class Test(object):
    @ddt.data({})
    def test_func(self):
        pass
"""
        tree = ast.parse(code).body[0]
        visitor = test_ddt.DDTDecoratorChecker()
        visitor.visit(tree)
        self.assertEqual(visitor.errors, {})

    def test_fail(self):
        code = """
class Test(object):
    @ddt.data({})
    def test_func(self):
        pass
"""
        tree = ast.parse(code).body[0]
        visitor = test_ddt.DDTDecoratorChecker()
        visitor.visit(tree)
        self.assertEqual(
            visitor.errors,
            {"Test": {"lineno": 3,
                      "message": "Class Test has functions that use DDT, "
                      "but is not decorated with `ddt.ddt`"}})
