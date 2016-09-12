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
import itertools
import os
import re

import six.moves

from tests.unit import test


class Variants(object):
    def __init__(self, variants, print_prefix="mock_"):
        self.variants = variants
        self.print_prefix = print_prefix

    def __repr__(self):
        variants = self.variants
        if len(variants) > 3:
            variants = variants[:3]
        variants = [repr(self.print_prefix + var) for var in variants]
        return "{" + ", ".join(variants) + (
            ", ...}" if len(self.variants) > 3 else "}")

    def __eq__(self, val):
        return getattr(val, "variants", val) == self.variants

    def __ne__(self, other):
        return not self.__eq__(other)

    def __contains__(self, val):
        return val in self.variants


def pairwise_isinstance(*args):
    return all(itertools.starmap(isinstance, args))


class FuncMockArgsDecoratorsChecker(ast.NodeVisitor):
    """Recursively visit an AST looking for misusage of mocks in tests.

    The misusage being tested by this particular class is unmatched mocked
    object name against the argument names.

    The following is the correct usages::
        @mock.patch("module.abc") # or
        # or @mock.patch(MODULE + ".abc")
        # or @mock.patch("%s.abc" % MODULE) where MODULE="module"
        def test_foobar(self, mock_module_abc): # or `mock_abc'
            ...

        @mock.patch("pkg.ClassName.abc") # or
        # or @mock.patch(CLASSNAME + ".abc")
        # or @mock.patch("%s.abc" % CLASSNAME) where CLASSNAME="pkg.ClassName"
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

    # NOTE(amaretskiy): Disable check if shortest variant is too long
    #                   because long name is not convenient and could
    #                   even be blocked by PEP8
    SHORTEST_VARIANT_LEN_LIMIT = 25

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
            if pairwise_isinstance(
                    (node.op, ast.Mod), (node.left, ast.Str),
                    (node.right, ast.Name)):
                val = node.left.s % self.globals_[node.right.id]
            elif pairwise_isinstance(
                    (node.op, ast.Add), (node.left, ast.Name),
                    (node.right, ast.Str)):
                val = self.globals_[node.left.id] + node.right.s
        elif isinstance(node, ast.Name):
            val = self.globals_[node.id]

        if val is None:
            raise ValueError(
                "Unable to find value in %s, only the following are parsed: "
                "GLOBAL, 'pkg.foobar', '%%s.foobar' %% GLOBAL or 'GLOBAL + "
                "'.foobar'"
                % ast.dump(node))

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

    def _get_mocked_class_value_variants(self, class_name, mocked_name):
        class_name = self._camelcase_to_python(class_name)
        mocked_name = self._camelcase_to_python(mocked_name)

        if class_name == self.classname_python:
            # Optional, since class name of the mocked package is the same as
            # class name of the *TestCase
            return [mocked_name, class_name + "_" + mocked_name]

        # Full class name is required otherwise
        return [class_name + "_" + mocked_name]

    def _add_pkg_optional_prefixes(self, tokens, variants):
        prefixed_variants = list(variants)
        for token in map(self._camelcase_to_python, reversed(tokens)):
            prefixed_variants.append(token + "_" + prefixed_variants[-1])
        return prefixed_variants

    def _get_mocked_name_variants(self, name):
        tokens = name.split(".")
        variants = [self._camelcase_to_python(tokens.pop())]
        if tokens:
            if tokens[-1][0].isupper():
                # Mocked something inside a class, check if we should require
                # the class name to be present in mock argument
                variants = self._get_mocked_class_value_variants(
                    class_name=tokens.pop(),
                    mocked_name=variants[0])
            variants = self._add_pkg_optional_prefixes(tokens, variants)
        return Variants(variants)

    def _get_mock_decorators_variants(self, funccall):
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

            mock_decorators.append(
                self._get_mocked_name_variants(decname)
            )

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
        self.globals_.pop("__builtins__", None)
        self.globals_.pop("builtins", None)

    def visit_ClassDef(self, node):
        classname_camel = node.name
        if node.name.endswith("TestCase"):
            classname_camel = node.name[:-len("TestCase")]

        self.classname_python = self._camelcase_to_python(classname_camel)

        self.generic_visit(node)

    def check_name(self, arg, dec_vars):
        return (dec_vars is not None and arg in dec_vars)

    def visit_FunctionDef(self, node):
        self.generic_visit(node)

        mock_decs = self._get_mock_decorators_variants(node)

        if not mock_decs:
            return

        mock_args = self._get_mock_args(node)

        error_msgs = []
        mismatched = False
        for arg, dec_vars in six.moves.zip_longest(mock_args, mock_decs):
            if not self.check_name(arg, dec_vars):
                if arg and dec_vars:
                    sorted_by_len = sorted(
                        dec_vars.variants, key=lambda i: len(i), reverse=True)
                    shortest_name = sorted_by_len.pop()
                    if len(shortest_name) <= self.SHORTEST_VARIANT_LEN_LIMIT:
                        error_msgs.append(
                            ("Argument '%(arg)s' misnamed; should be either "
                             "of %(dec)s that is derived from the mock "
                             "decorator args.\n") % {"arg": arg,
                                                     "dec": dec_vars})
                elif not arg:
                    error_msgs.append(
                        "Missing or malformed argument for %s decorator."
                        % dec_vars)
                    mismatched = True
                elif not dec_vars:
                    error_msgs.append(
                        "Missing or malformed decorator for '%s' argument."
                        % arg)
                    mismatched = True

        if error_msgs:
            if mismatched:
                self.errors.append({
                    "lineno": node.lineno,
                    "args": mock_args,
                    "decs": mock_decs,
                    "messages": error_msgs
                })
            else:
                self.errors.append({
                    "lineno": node.lineno,
                    "mismatch_pairs": list(zip(mock_args, mock_decs)),
                    "messages": error_msgs
                })


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

        if errors:
            print(FuncMockArgsDecoratorsChecker.__doc__)
            print(
                "\n\n"
                "The following errors were found during the described check:")
            for error in errors:
                print("\n\n"
                      "Errors at file %(filename)s line %(lineno)d:\n\n"
                      "%(message)s" % {
                          "message": "\n".join(error["messages"]),
                          "filename": error["filename"],
                          "lineno": error["lineno"]})

        # NOTE(pboldin): When the STDOUT is shuted the below is the last
        # resort to know what is wrong with the mock names.
        for error in errors:
            error["messages"] = [
                message.rstrip().replace("\n", "  ").replace("\t", "")
                for message in error["messages"]
            ]
        self.assertEqual([], errors)
