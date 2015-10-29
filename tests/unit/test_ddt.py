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
import os

from tests.unit import test


class DDTDecoratorChecker(ast.NodeVisitor):
    """Visit an AST tree looking for classes lacking the ddt.ddt decorator.

    DDT uses decorators on test case functions to supply different
    test data, but if the class that those functions are members of is
    not decorated with @ddt.ddt, then the data expansion never happens
    and the tests are incomplete. This is very easy to miss both when
    writing and when reviewing code, so this visitor ensures that
    every class that contains a function decorated with a @ddt.*
    decorator is itself decorated with @ddt.ddt
    """
    def __init__(self):
        self.classes = []
        self.errors = {}

    @classmethod
    def _get_name(cls, node):
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return cls._get_name(node.value) + "." + node.attr
        return ""

    def _is_ddt(self, cls_node):
        return "ddt.ddt" in (self._get_name(d)
                             for d in cls_node.decorator_list)

    def visit_ClassDef(self, node):
        self.classes.append(node)
        self.generic_visit(node)
        self.classes.pop()

    def visit_FunctionDef(self, node):
        if not self.classes:
            # NOTE(stpierre): we only care about functions that are
            # defined inside of classes
            return
        cls = self.classes[-1]
        if cls.name in self.errors:
            # NOTE(stpierre): if this class already has been found to
            # be in error, ignore the rest of its functions
            return
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            funcname = self._get_name(decorator.func)
            if funcname.startswith("ddt."):
                if not self._is_ddt(cls):
                    msg = ("Class %s has functions that use DDT, "
                           "but is not decorated with `ddt.ddt`" %
                           cls.name)
                    self.errors[cls.name] = {
                        "lineno": node.lineno,
                        "message": msg
                    }


class DDTDecoratorCheckerTestCase(test.TestCase):
    tests_path = os.path.join(os.path.dirname(__file__))

    def test_ddt_class_decorator(self):
        """Classes with DDT-decorated functions have ddt.ddt class decorator.

        """
        errors = []

        for dirname, dirnames, filenames in os.walk(self.tests_path):
            for filename in filenames:
                if not (filename.startswith("test_") and
                        filename.endswith(".py")):
                    continue

                filename = os.path.relpath(os.path.join(dirname, filename))

                with open(filename, "rb") as fh:
                    try:
                        tree = ast.parse(fh.read(), filename)
                    except TypeError as err:
                        errors.append({"message": str(err),
                                       "filename": filename,
                                       "lineno": -1})

                visitor = DDTDecoratorChecker()
                visitor.visit(tree)
                errors.extend(
                    dict(filename=filename, **error)
                    for error in visitor.errors.values())

        if errors:
            msg = [""]
            for error in errors:
                msg.extend([
                    "Errors at %(filename)s line %(lineno)d: %(message)s" % {
                        "message": error["message"],
                        "filename": error["filename"],
                        "lineno": error["lineno"]},
                    ""])
            self.fail("\n".join(msg))
