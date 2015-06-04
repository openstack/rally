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
import re

import six.moves

from tests.unit import test


class FuncMockArgsDecoratorsChecker(ast.NodeVisitor):
    """Recursively visit an AST looking for misusage of mocks in tests.

    The misusage being tested by this particular class is unmatched mocked
    object name against the argument names.

    The following is the correct usages::
        @mock.patch("module.abc")
        def test_foobar(self, mock_module_abc): # or `mock_abc'
            ...

        @mock.patch("pkg.ClassName.abc")
        def test_foobar(self, mock_class_name_abc):
            ...

        class FooClassNameTestCase(...):
            @mock.patch("pkg.FooClassName.abc")
            def test_foobar(self, mock_abc):
                # Iff the mocked object is inside the tested class then
                # the class name in mock argname is optional.
                ...

    While these are not::
        @mock.patch("module.abc")
        def test_foobar(self, m_abc):
            # must be prefixed with `mock_'

        @mock.patch("module.abc")
        def test_foobar(self, mock_cba):
            # must contain mocked object name (`mock_abc')

        @mock.patch("module.abc")
        def test_foobar(self, mock_modulewrong_abc):
            # must match the module `mock_module_abc'

        @mock.patch("ClassName.abc")
        def test_foobar(self, mock_class_abc):
            # must match the python-styled class name + method name
    """
    def __init__(self):
        self.errors = []
        self.globals_ = {}

    @classmethod
    def _get_name(cls, node):
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return cls._get_name(node.value) + "." + node.attr
        return ""

    def _get_value(self, node):
        """Get mock.patch string argument regexp.

        It is either a string (if we are lucky), string-format of
        ("%s.something" % GVAL) or (GVAL + ".something")
        """
        val = None
        if isinstance(node, ast.Str):
            val = node.s
        elif isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.Mod):
                val = node.left.s % self.globals_[node.right.id]
            elif isinstance(node.op, ast.Add):
                val = self.globals_[node.left.id] + node.right.s
        elif isinstance(node, ast.Name):
            val = self.globals_[node.id]

        if val is None:
            raise ValueError("Unable to find value in %s" % ast.dump(node))

        return val

    CAMELCASE_SPLIT_ANY_AND_CAPITAL = re.compile("(.)([A-Z][a-z]+)")
    CAMELCASE_SPLIT_LOWER_AND_CAPITAL = re.compile("([a-z0-9])([A-Z])")
    CAMELCASE_SPLIT_REPL = r"\1_\2"

    @classmethod
    def _camelcase_to_python(cls, name):
        for regexp in (cls.CAMELCASE_SPLIT_ANY_AND_CAPITAL,
                       cls.CAMELCASE_SPLIT_LOWER_AND_CAPITAL):
            name = regexp.sub(cls.CAMELCASE_SPLIT_REPL, name)
        return name.lower()

    def _get_mocked_class_value_regexp(self, class_name, mocked_name):
        class_name = self._camelcase_to_python(class_name)
        mocked_name = self._camelcase_to_python(mocked_name)

        if class_name == self.classname_python:
            # Optional, since class name of the mocked package is the same as
            # class name of the *TestCase
            return "(?:" + class_name + "_)?" + mocked_name

        # Full class name is required otherwise
        return class_name + "_" + mocked_name

    def _get_pkg_optional_regexp(self, tokens):
        pkg_regexp = ""
        for token in map(self._camelcase_to_python, tokens):
            pkg_regexp = ("(?:" + pkg_regexp + "_)?" + token
                          if pkg_regexp else token)
        return "(?:" + pkg_regexp + "_)?"

    def _get_mocked_name_regexp(self, name):
        tokens = name.split(".")
        if len(tokens) > 1:
            name = self._camelcase_to_python(tokens.pop())
            if tokens[-1][0].isupper():
                # Mocked something inside a class, check if we should require
                # the class name to be present in mock argument
                name = self._get_mocked_class_value_regexp(
                    class_name=tokens[-1],
                    mocked_name=name)
            pkg_regexp = self._get_pkg_optional_regexp(tokens)
            name = pkg_regexp + name
        return name

    def _get_mock_decorators_regexp(self, funccall):
        """Return all the mock.patch{,.object} decorated for function."""
        mock_decorators = []

        for decorator in reversed(funccall.decorator_list):
            if not isinstance(decorator, ast.Call):
                continue
            funcname = self._get_name(decorator.func)

            if funcname == "mock.patch":
                decname = self._get_value(decorator.args[0])
            elif funcname == "mock.patch.object":
                decname = (self._get_name(decorator.args[0]) + "." +
                           self._get_value(decorator.args[1]))
            else:
                continue

            decname = self._get_mocked_name_regexp(decname)

            mock_decorators.append(decname)

        return mock_decorators

    @staticmethod
    def _get_mock_args(node):
        """Return all the mock arguments."""
        args = []
        PREFIX_LENGTH = len("mock_")

        for arg in node.args.args:
            name = getattr(arg, "id", getattr(arg, "arg", None))
            if not name.startswith("mock_"):
                continue
            args.append(name[PREFIX_LENGTH:])

        return args

    def visit_Assign(self, node):
        """Catch all the globals."""
        self.generic_visit(node)

        if node.col_offset == 0:
            mnode = ast.Module(body=[node])
            code = compile(mnode, "<ast>", "exec")
            try:
                exec(code, self.globals_)
            except Exception:
                pass

    def visit_ClassDef(self, node):
        classname_camel = node.name
        if node.name.endswith("TestCase"):
            classname_camel = node.name[:-len("TestCase")]

        self.classname_python = self._camelcase_to_python(classname_camel)

        self.generic_visit(node)

    def check_name(self, arg, dec):
        return (arg is not None and dec is not None
                and (arg == dec or re.match(dec, arg)))

    def visit_FunctionDef(self, node):
        self.generic_visit(node)

        mock_decs = self._get_mock_decorators_regexp(node)

        if not mock_decs:
            return

        mock_args = self._get_mock_args(node)

        for arg, dec in six.moves.zip_longest(mock_args, mock_decs):
            if not self.check_name(arg, dec):
                self.errors.append({
                    "lineno": node.lineno,
                    "args": mock_args,
                    "decs": mock_decs
                })
                break


class MockUsageCheckerTestCase(test.TestCase):
    tests_path = os.path.join(os.path.dirname(__file__))

    def test_mock_decorators_and_args(self):
        """Ensure that mocked objects are called correctly in the arguments.

        See `FuncMockArgsDecoratorsChecker' docstring for details.
        """
        errors = []

        for dirname, dirnames, filenames in os.walk(self.tests_path):
            for filename in filenames:
                if (not filename.startswith("test_") or
                   not filename.endswith(".py")):
                    continue

                filename = os.path.relpath(os.path.join(dirname, filename))

                with open(filename, "rb") as fh:
                    tree = ast.parse(fh.read(), filename)

                visitor = FuncMockArgsDecoratorsChecker()
                visitor.visit(tree)
                errors.extend(
                    dict(filename=filename, **error)
                    for error in visitor.errors)

        self.assertEqual([], errors)
