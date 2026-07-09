# Copyright 2013: Intel Inc.
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

import io
from unittest import mock

import ddt
import typer

from rally.cli import cliutils
from tests.unit import test


@ddt.ddt
class CliUtilsTestCase(test.TestCase):

    def test_print_dict(self):
        out = io.StringIO()
        dict = {"key": "value"}
        cliutils.print_dict(dict, out=out)
        self.assertEqual("+----------+-------+\n"
                         "| Property | Value |\n"
                         "+----------+-------+\n"
                         "| key      | value |\n"
                         "+----------+-------+\n",
                         out.getvalue())

    def test_print_dict_wrap(self):
        out = io.StringIO()
        dict = {"key1": "not wrapped",
                "key2": "this will be wrapped"}
        cliutils.print_dict(dict, wrap=16, out=out)
        self.assertEqual("+----------+--------------+\n"
                         "| Property | Value        |\n"
                         "+----------+--------------+\n"
                         "| key1     | not wrapped  |\n"
                         "| key2     | this will be |\n"
                         "|          | wrapped      |\n"
                         "+----------+--------------+\n",
                         out.getvalue())

    def test_print_dict_formatters_and_fields(self):
        out = io.StringIO()
        dict = {"key1": "value",
                "key2": "Value",
                "key3": "vvv"}
        formatters = {"foo": lambda x: x["key1"],
                      "bar": lambda x: x["key2"]}
        fields = ["foo", "bar"]
        cliutils.print_dict(dict, formatters=formatters, fields=fields,
                            out=out)
        self.assertEqual("+----------+-------+\n"
                         "| Property | Value |\n"
                         "+----------+-------+\n"
                         "| foo      | value |\n"
                         "| bar      | Value |\n"
                         "+----------+-------+\n",
                         out.getvalue())

    def test_print_dict_header(self):
        out = io.StringIO()
        dict = {"key": "value"}
        cliutils.print_dict(dict, table_label="Some Table", print_header=False,
                            out=out)
        self.assertEqual("+-------------+\n"
                         "| Some Table  |\n"
                         "+-----+-------+\n"
                         "| key | value |\n"
                         "+-----+-------+\n",
                         out.getvalue())

    def test_print_dict_objects(self):
        class SomeStruct(object):
            def __init__(self, a, b):
                self.a = a
                self.b = b

            @property
            def c(self):
                return self.a + self.b

            def foo(self):
                pass

            @classmethod
            def bar(cls):
                pass

            @staticmethod
            def foobar():
                pass

        out = io.StringIO()
        formatters = {"c": lambda x: "a + b = %s" % x.c}
        cliutils.print_dict(SomeStruct(1, 2), formatters=formatters, out=out)
        self.assertEqual("+----------+-----------+\n"
                         "| Property | Value     |\n"
                         "+----------+-----------+\n"
                         "| a        | 1         |\n"
                         "| b        | 2         |\n"
                         "| c        | a + b = 3 |\n"
                         "+----------+-----------+\n",
                         out.getvalue())

    def test_print_dict_with_spec_chars(self):
        out = io.StringIO()
        dict = {"key": "line1\r\nline2"}
        cliutils.print_dict(dict, out=out)
        self.assertEqual("+----------+-------+\n"
                         "| Property | Value |\n"
                         "+----------+-------+\n"
                         "| key      | line1 |\n"
                         "|          | line2 |\n"
                         "+----------+-------+\n",
                         out.getvalue())

    def test_make_header(self):
        h1 = cliutils.make_header("msg", size=4, symbol="=")
        self.assertEqual("====\nmsg\n====\n", h1)

    def test_make_table_header(self):
        actual = cliutils.make_table_header("Response Times (sec)", 40)
        expected = "\n".join(
            ("+--------------------------------------+",
             "|         Response Times (sec)         |",)
        )
        self.assertEqual(expected, actual)

        actual = cliutils.make_table_header("Response Times (sec)", 39)
        expected = "\n".join(
            ("+-------------------------------------+",
             "|        Response Times (sec)         |",)
        )
        self.assertEqual(expected, actual)

        self.assertRaises(ValueError, cliutils.make_table_header,
                          "Response Times (sec)", len("Response Times (sec)"))

    @ddt.data({"obj": mock.Mock(foo=6.56565), "args": ["foo", 3],
               "expected": 6.566},
              {"obj": mock.Mock(foo=6.56565), "args": ["foo"],
               "expected": 6.56565},
              {"obj": mock.Mock(foo=None), "args": ["foo"],
               "expected": "n/a"},
              {"obj": mock.Mock(foo="n/a"), "args": ["foo"],
               "expected": "n/a"},
              {"obj": mock.Mock(foo="n/a"), "args": ["foo", 3],
               "expected": "n/a"},
              {"obj": {"foo": 6.56565}, "args": ["foo", 3],
               "expected": 6.566},
              {"obj": {"foo": 6.56565}, "args": ["foo"],
               "expected": 6.56565},
              {"obj": {"foo": None}, "args": ["foo"],
               "expected": "n/a"},
              {"obj": {"foo": "n/a"}, "args": ["foo"],
               "expected": "n/a"},
              {"obj": {"foo": "n/a"}, "args": ["foo", 3],
               "expected": "n/a"},
              {"obj": object, "args": ["unexpected_field", 3],
               "expected": AttributeError},
              {"obj": {"foo": 42}, "args": ["unexpected_field", 3],
               "expected": KeyError})
    @ddt.unpack
    def test_pretty_float_formatter(self, obj, args, expected=None):
        formatter = cliutils.pretty_float_formatter(*args)
        if type(expected) is type and issubclass(expected, Exception):
            self.assertRaises(expected, formatter, obj)
        else:
            self.assertEqual(expected, formatter(obj))

    class TestObj(object):
        x = 1
        y = 2
        z = 3.142857142857143
        aOrB = 3  # mixed case field

    @ddt.data(
        {
            "input": {
                "objs": [TestObj()],
                "fields": ["x", "y"],
                "print_header": True,
                "print_border": True,
                "sortby_index": None
            },
            "expected": (
                "+---+---+\n"
                "| x | y |\n"
                "+---+---+\n"
                "| 1 | 2 |\n"
                "+---+---+")
        },
        {
            "input": {
                "objs": [TestObj()],
                "fields": ["z"],
                "print_header": True,
                "print_border": True,
                "sortby_index": None,
                "formatters": {"z": cliutils.pretty_float_formatter("z", 5)}
            },
            "expected": (
                "+---------+\n"
                "| z       |\n"
                "+---------+\n"
                "| 3.14286 |\n"
                "+---------+")
        },
        {
            "input": {
                "objs": [TestObj()],
                "fields": ["x"],
                "print_header": True,
                "print_border": True
            },
            "expected": (
                "+---+\n"
                "| x |\n"
                "+---+\n"
                "| 1 |\n"
                "+---+")
        },
        {
            "input": {
                "objs": [TestObj()],
                "fields": ["x", "y"],
                "print_header": True,
                "print_border": True
            },
            "expected": (
                "+---+---+\n"
                "| x | y |\n"
                "+---+---+\n"
                "| 1 | 2 |\n"
                "+---+---+")
        },
        {
            "input": {
                "objs": [TestObj()],
                "fields": ["x"],
                "print_header": False,
                "print_border": False
            },
            "expected": "1"
        },
        {
            "input": {
                "objs": [TestObj()],
                "fields": ["x", "y"],
                "print_header": False,
                "print_border": False
            },
            "expected": "1 2"
        },
        {
            "input": {
                "objs": [TestObj()],
                "fields": ["x"],
                "print_header": True,
                "print_border": False
            },
            "expected": "x \n1"
        },
        {
            "input": {
                "objs": [TestObj()],
                "fields": ["x", "y"],
                "print_header": True,
                "print_border": False
            },
            "expected": "x y \n1 2"
        },
        {
            "input": {
                "objs": [TestObj()],
                "fields": ["x"],
                "print_header": False,
                "print_border": True
            },
            "expected": (
                "+--+\n"
                "|1 |\n"
                "+--+")
        },
        {
            "input": {
                "objs": [TestObj()],
                "fields": ["x", "y"],
                "print_header": False,
                "print_border": True
            },
            "expected": (
                "+--+--+\n"
                "|1 |2 |\n"
                "+--+--+")
        },
        {
            "input": {
                "objs": [TestObj()],
                "fields": ["aOrB"],
                "print_header": True,
                "print_border": True,
                "mixed_case_fields": ["aOrB"]
            },
            "expected": (
                "+------+\n"
                "| aOrB |\n"
                "+------+\n"
                "| 3    |\n"
                "+------+")
        },
        {
            "input": {
                "objs": [TestObj()],
                "fields": ["aOrB"],
                "print_header": False,
                "print_border": True,
                "mixed_case_fields": ["aOrB"]
            },
            "expected": (
                "+--+\n"
                "|3 |\n"
                "+--+")
        },
        {
            "input": {
                "objs": [TestObj()],
                "fields": ["aOrB"],
                "print_header": True,
                "print_border": False,
                "mixed_case_fields": ["aOrB"]
            },
            "expected": "aOrB \n3"
        },
        {
            "input": {
                "objs": [TestObj()],
                "fields": ["aOrB"],
                "print_header": False,
                "print_border": False,
                "mixed_case_fields": ["aOrB"]
            },
            "expected": "3"
        },
        {
            "input": {
                "objs": [{"x": 1, "y": 2}],
                "fields": ["x", "y"],
                "print_header": True,
                "print_border": True,
                "sortby_index": None
            },
            "expected": (
                "+---+---+\n"
                "| x | y |\n"
                "+---+---+\n"
                "| 1 | 2 |\n"
                "+---+---+")
        },
        {
            "input": {
                "objs": [{"z": 3.142857142857143}],
                "fields": ["z"],
                "print_header": True,
                "print_border": True,
                "sortby_index": None,
                "formatters": {"z": cliutils.pretty_float_formatter("z", 5)}
            },
            "expected": (
                "+---------+\n"
                "| z       |\n"
                "+---------+\n"
                "| 3.14286 |\n"
                "+---------+")
        },
        {
            "input": {
                "objs": [{"x": 1}],
                "fields": ["x"],
                "print_header": True,
                "print_border": True
            },
            "expected": (
                "+---+\n"
                "| x |\n"
                "+---+\n"
                "| 1 |\n"
                "+---+")
        },
        {
            "input": {
                "objs": [{"x": 1, "y": 2}],
                "fields": ["x", "y"],
                "print_header": True,
                "print_border": True
            },
            "expected": (
                "+---+---+\n"
                "| x | y |\n"
                "+---+---+\n"
                "| 1 | 2 |\n"
                "+---+---+")
        },
        {
            "input": {
                "objs": [{"x": 1, "y": 2}, {"x": 2, "y": 3}],
                "fields": ["x", "y"],
                "print_header": True,
                "print_border": True,
                "print_row_border": True
            },
            "expected": (
                "+---+---+\n"
                "| x | y |\n"
                "+===+===+\n"
                "| 1 | 2 |\n"
                "+---+---+\n"
                "| 2 | 3 |\n"
                "+---+---+"
            )
        }
    )
    @ddt.unpack
    def test_print_list(self, input, expected):
        out = io.StringIO()
        input["out"] = out
        cliutils.print_list(**input)
        self.assertEqual(expected, out.getvalue().strip())

    def test_print_list_raises(self):
        out = io.StringIO()
        self.assertRaisesRegex(
            ValueError,
            "Field labels list.*has different number "
            "of elements than fields list",
            cliutils.print_list,
            [self.TestObj()], ["x"],
            field_labels=["x", "y"], sortby_index=None, out=out)


class IterCommandsTestCase(test.TestCase):

    def _build(self):
        app = typer.Typer()
        group = typer.Typer()

        @app.command()
        def top() -> None:
            pass

        @group.command()
        def leaf(uuid: str, detailed: bool = False) -> None:
            pass

        app.add_typer(group, name="grp")
        return typer.main.get_command(app)

    def test_iter_commands_yields_leaves_with_paths(self):
        command = self._build()

        result = {
            path: (leaf, params)
            for path, leaf, params in cliutils.iter_commands(command)
        }

        # groups are recursed into; only leaf commands are yielded, each with
        # its full path from the root
        self.assertEqual({("top",), ("grp", "leaf")}, set(result))

    def test_iter_commands_yields_leaf_params(self):
        command = self._build()

        params = {
            path: p for path, _leaf, p in cliutils.iter_commands(command)
        }

        opt_names = [name for param in params[("grp", "leaf")]
                     for name in param.opts]
        self.assertIn("--detailed", opt_names)
