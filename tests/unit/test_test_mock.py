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

import mock

from tests.unit import test
from tests.unit import test_mock


class VariantsTestCase(test.TestCase):
    def setUp(self):
        self.variants = test_mock.Variants(["test", "foo", "bar"])
        super(VariantsTestCase, self).setUp()

    def test_print(self):
        self.assertEqual(
            "{'mock_test', 'mock_foo', 'mock_bar'}",
            repr(self.variants)
        )

    def test_print_long(self):
        variants = test_mock.Variants(["test", "foo", "bar", "buz"])
        self.assertEqual(
            "{'mock_test', 'mock_foo', 'mock_bar', ...}",
            repr(variants)
        )

    def test_equal(self):
        self.assertEqual(["test", "foo", "bar"], self.variants)
        self.assertEqual(self.variants, self.variants)

        mock_variants = mock.Mock(variants=["test", "foo", "bar"])
        self.assertEqual(mock_variants, self.variants)

        self.assertNotEqual(["abc"], self.variants)

    def test_contains(self):
        self.assertIn("test", self.variants)
        self.assertNotIn("abc", self.variants)


class FuncMockArgsDecoratorsCheckerTestCase(test.TestCase):
    code = """
@mock.patch("os.path.join")
@mock.patch("pkg.module1.OtherObject.method")
@mock.patch("pkg.module2.MyClassObject.method")
@mock.patch.object(pkg.SomeKindOfObject, "abc")
@mock.patch.object(pkg.MyClassObject, "abc")
def test_func(self, mock_args, mock_args2, mock_some_longer_args):
    pass
"""
    code_mock_decorators = [
        ["abc", "my_class_object_abc", "pkg_my_class_object_abc"],
        ["some_kind_of_object_abc", "pkg_some_kind_of_object_abc"],
        [
            "method",
            "my_class_object_method",
            "module2_my_class_object_method",
            "pkg_module2_my_class_object_method"
        ],
        [
            "other_object_method",
            "module1_other_object_method",
            "pkg_module1_other_object_method",
        ],
        [
            "join",
            "path_join",
            "os_path_join"
        ],
    ]
    code_mock_args = ["args", "args2", "some_longer_args"]

    def setUp(self):
        super(FuncMockArgsDecoratorsCheckerTestCase, self).setUp()
        self.visitor = test_mock.FuncMockArgsDecoratorsChecker()
        self.visitor.classname_python = ""
        self.visitor.globals_["EXPR"] = "expression"
        self.tree = self._parse_expr(self.code)

    def _parse_expr(self, code):
        firstbody = ast.parse(code).body[0]
        if isinstance(firstbody, ast.Expr):
            return firstbody.value
        return firstbody

    def test__get_name(self):
        self.assertEqual(
            "os.path.join",
            self.visitor._get_name(self._parse_expr("os.path.join"))
        )

    def test__get_value_str(self):
        self.assertEqual(
            "not.your.fault",
            self.visitor._get_value(self._parse_expr("'not.your.fault'"))
        )

    def test__get_value_mod(self):
        self.assertEqual(
            "some.crazy.mod.expression",
            self.visitor._get_value(
                self._parse_expr("'some.crazy.mod.%s' % EXPR")
            )
        )

    def test__get_value_add(self):
        self.assertEqual(
            "expression.some.crazy.add",
            self.visitor._get_value(
                self._parse_expr("EXPR + '.some.crazy.add'")
            )
        )

    def test__get_value_global(self):
        self.assertEqual(
            "expression",
            self.visitor._get_value(
                self._parse_expr("EXPR")
            )
        )

    def test__get_value_none(self):
        self.assertRaises(
            ValueError,
            self.visitor._get_value,
            ast.parse("import abc")
        )

    def test__get_value_asserts(self):
        self.assertRaises(
            ValueError,
            self.visitor._get_value,
            self._parse_expr("EXPR % 'abc'")
        )

        self.assertRaises(
            ValueError,
            self.visitor._get_value,
            self._parse_expr("'abc' + EXPR")
        )

    def test__camelcase_to_python_camel(self):
        self.assertEqual(
            "some_class_name",
            self.visitor._camelcase_to_python("SomeClassName")
        )

    def test__camelcase_to_python_python(self):
        self.assertEqual(
            "some_python_name",
            self.visitor._camelcase_to_python("some_python_name")
        )

    def test__get_mocked_class_value_variants_matches_class(self):
        self.visitor.classname_python = "foo_class"
        self.assertEqual(
            ["mocked_obj", "foo_class_mocked_obj"],
            self.visitor._get_mocked_class_value_variants(
                class_name="FooClass",
                mocked_name="MockedObj"
            )
        )

    def test__get_mocked_class_value_variants_different_class(self):
        self.visitor.classname_python = "foo_class"
        self.assertEqual(
            ["bar_class_mocked_obj"],
            self.visitor._get_mocked_class_value_variants(
                class_name="BarClass",
                mocked_name="MockedObj"
            )
        )

    def test__add_pkg_optional_prefixes(self):
        self.assertEqual(
            ["foo", "bar", "bar_class_bar", "pkg_bar_class_bar",
             "some_pkg_bar_class_bar"],
            self.visitor._add_pkg_optional_prefixes(
                "some.pkg.BarClass".split("."),
                ["foo", "bar"]
            )
        )

    def test__get_mocked_name_variants_single(self):
        self.assertEqual(
            ["foo_bar"],
            self.visitor._get_mocked_name_variants(
                "FooBar"
            )
        )

        self.assertEqual(
            ["foobar"],
            self.visitor._get_mocked_name_variants(
                "foobar"
            )
        )

    def test__get_mocked_name_variants_classname(self):
        self.visitor.classname_python = "foo_bar"
        self.assertEqual(
            ["method", "foo_bar_method", "pkg_foo_bar_method"],
            self.visitor._get_mocked_name_variants(
                "pkg.FooBar.method"
            )
        )

        self.visitor.classname_python = ""
        self.assertEqual(
            ["foo_bar_method", "pkg_foo_bar_method"],
            self.visitor._get_mocked_name_variants(
                "pkg.FooBar.method"
            )
        )

    def test__get_mocked_name_variants_pkg(self):
        self.assertEqual(
            ["method", "pkg_method", "long_pkg_method",
             "some_long_pkg_method"],
            self.visitor._get_mocked_name_variants(
                "some.long.pkg.method"
            )
        )

    def test__get_mock_decorators_variants(self):
        self.visitor.classname_python = "my_class_object"
        self.assertEqual(
            self.code_mock_decorators,
            self.visitor._get_mock_decorators_variants(self.tree)
        )

    def test__get_mock_args(self):
        self.assertEqual(
            self.code_mock_args,
            self.visitor._get_mock_args(self.tree)
        )

    def test_visit_Assign(self):
        self.visitor.globals_ = {}

        self.visitor.visit_Assign(
            self._parse_expr("ABC = '20' + '40'")
        )
        self.assertEqual(
            {"ABC": "2040"},
            self.visitor.globals_
        )

        self.visitor.visit_Assign(
            self._parse_expr("abc = 20 + 40")
        )
        self.assertEqual(
            {"ABC": "2040", "abc": 60},
            self.visitor.globals_
        )

    def test_visit_ClassDef(self):
        self.visitor.visit_ClassDef(
            self._parse_expr("class MyObject(object): pass")
        )
        self.assertEqual(
            "my_object",
            self.visitor.classname_python
        )

        self.visitor.visit_ClassDef(
            self._parse_expr("class YourObjectTestCase(object): pass")
        )
        self.assertEqual(
            "your_object",
            self.visitor.classname_python
        )

    def test_visit_FunctionDef_empty_decs(self):
        self.visitor._get_mock_decorators_variants = mock.Mock(
            return_value=[]
        )

        self.assertIsNone(self.visitor.visit_FunctionDef(self.tree))
        self.assertEqual([], self.visitor.errors)

        self.visitor._get_mock_decorators_variants.assert_called_once_with(
            self.tree
        )

    def test_visit_FunctionDef_good(self):
        self.visitor._get_mock_decorators_variants = mock.Mock(
            return_value=[
                ["foo", "foo_bar", "pkg_foo_bar"]
            ]
        )
        self.visitor._get_mock_args = mock.Mock(
            return_value=["pkg_foo_bar"]
        )

        self.assertIsNone(self.visitor.visit_FunctionDef(self.tree))
        self.assertEqual([], self.visitor.errors)

        self.visitor._get_mock_decorators_variants.assert_called_once_with(
            self.tree
        )
        self.visitor._get_mock_args.assert_called_once_with(
            self.tree
        )

    def test_visit_FunctionDef_misnamed(self):
        variants = test_mock.Variants(
            ["foo", "foo_bar", "pkg_foo_bar", "a"]
        )
        self.visitor._get_mock_decorators_variants = mock.Mock(
            return_value=[variants]
        )
        self.visitor._get_mock_args = mock.Mock(
            return_value=["bar_foo_misnamed"]
        )

        self.assertIsNone(self.visitor.visit_FunctionDef(self.tree))
        self.assertEqual(
            [
                {
                    "lineno": 2,
                    "messages": [
                        "Argument 'bar_foo_misnamed' misnamed; should be "
                        "either of %s that is derived from the mock decorator "
                        "args.\n" % variants
                    ],
                    "mismatch_pairs": [
                        ("bar_foo_misnamed", variants)
                    ]
                }
            ],
            self.visitor.errors)

        self.visitor._get_mock_decorators_variants.assert_called_once_with(
            self.tree
        )
        self.visitor._get_mock_args.assert_called_once_with(
            self.tree
        )

    def test_visit_FunctionDef_mismatch_args(self):
        variants = test_mock.Variants(
            ["foo", "foo_bar", "pkg_foo_bar", "a"]
        )
        self.visitor._get_mock_decorators_variants = mock.Mock(
            return_value=[variants]
        )
        self.visitor._get_mock_args = mock.Mock(
            return_value=["bar_foo_misnamed", "mismatched"]
        )

        self.assertIsNone(self.visitor.visit_FunctionDef(self.tree))
        self.assertEqual(
            [
                {
                    "lineno": 2,
                    "messages": [
                        "Argument 'bar_foo_misnamed' misnamed; should be "
                        "either of %s that is derived from the mock decorator "
                        "args.\n" % variants,
                        "Missing or malformed decorator for 'mismatched' "
                        "argument."
                    ],
                    "args": self.visitor._get_mock_args.return_value,
                    "decs": [variants]
                }
            ],
            self.visitor.errors)

        self.visitor._get_mock_decorators_variants.assert_called_once_with(
            self.tree
        )
        self.visitor._get_mock_args.assert_called_once_with(
            self.tree
        )

    def test_visit_FunctionDef_mismatch_decs(self):
        variants = test_mock.Variants(
            ["foo", "foo_bar", "pkg_foo_bar", "a"]
        )
        self.visitor._get_mock_decorators_variants = mock.Mock(
            return_value=[variants]
        )
        self.visitor._get_mock_args = mock.Mock(
            return_value=[]
        )

        self.assertIsNone(self.visitor.visit_FunctionDef(self.tree))
        self.assertEqual(
            [
                {
                    "lineno": 2,
                    "messages": [
                        "Missing or malformed argument for {'mock_foo', "
                        "'mock_foo_bar', 'mock_pkg_foo_bar', ...} decorator."
                    ],
                    "args": self.visitor._get_mock_args.return_value,
                    "decs": [variants]
                }
            ],
            self.visitor.errors)

        self.visitor._get_mock_decorators_variants.assert_called_once_with(
            self.tree
        )
        self.visitor._get_mock_args.assert_called_once_with(
            self.tree
        )

    def test_visit(self):
        self.visitor.classname_python = "my_class_object"
        self.visitor.visit(self.tree)

        self.assertEqual(
            self.code_mock_args,
            self.visitor.errors[0]["args"]
        )

        self.assertEqual(
            self.code_mock_decorators,
            self.visitor.errors[0]["decs"]
        )

        self.assertEqual(2, self.visitor.errors[0]["lineno"])

    def test_visit_ok(self):
        self.visitor.classname_python = "my_class_object"
        self.visitor.visit(
            self._parse_expr(
                """
class MyClassObjectTestCase(object):
    @mock.patch("foo.bar.MyClassObject.yep")
    @mock.patch("foo.bar.ClassName.ok")
    @mock.patch.object(pkg.FooClass, "method")
    def test_mockings(self, mock_pkg_foo_class_method, mock_class_name_ok,
                      mock_yep):
        pass
""")
        )

        self.assertEqual(
            [],
            self.visitor.errors
        )
