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

import ddt
from keystoneclient import exceptions as keystone_exc
import mock
from oslo_config import cfg
import six
import sqlalchemy.exc

from rally.cli import cliutils
from rally.cli.commands import deployment
from rally.cli.commands import task
from rally.cli.commands import verify
from rally import exceptions
from tests.unit import test

CONF = cfg.CONF

FAKE_TASK_UUID = "bb0f621c-29bd-495c-9d7a-d844335ed0fa"


@ddt.ddt
class CliUtilsTestCase(test.TestCase):

    def setUp(self):
        super(CliUtilsTestCase, self).setUp()
        self.categories = {
            "deployment": deployment.DeploymentCommands,
            "task": task.TaskCommands,
            "verify": verify.VerifyCommands
        }

    def tearDown(self):
        self._unregister_opts()
        super(CliUtilsTestCase, self).tearDown()

    def test_print_dict(self):
        out = six.StringIO()
        dict = {"key": "value"}
        cliutils.print_dict(dict, out=out)
        self.assertEqual("+----------+-------+\n"
                         "| Property | Value |\n"
                         "+----------+-------+\n"
                         "| key      | value |\n"
                         "+----------+-------+\n",
                         out.getvalue())

    def test_print_dict_wrap(self):
        out = six.StringIO()
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
        out = six.StringIO()
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
        out = six.StringIO()
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

        out = six.StringIO()
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
        out = six.StringIO()
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
        self.assertEqual(h1, "====\nmsg\n====\n")

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
        if type(expected) == type and issubclass(expected, Exception):
            self.assertRaises(expected, formatter, obj)
        else:
            self.assertEqual(expected, formatter(obj))

    def test_process_keyestone_exc(self):

        @cliutils.process_keystone_exc
        def a(a):
            if a == 1:
                raise keystone_exc.Unauthorized()

            if a == 2:
                raise keystone_exc.AuthorizationFailure()

            if a == 3:
                raise keystone_exc.ConnectionRefused()

            return a

        self.assertEqual(1, a(1))
        self.assertEqual(1, a(2))
        self.assertEqual(1, a(3))
        self.assertEqual(4, a(4))

    def test__methods_of_with_class(self):
        class fake_class(object):
            def public(self):
                pass

            def _private(self):
                pass
        result = cliutils._methods_of(fake_class)
        self.assertEqual(1, len(result))
        self.assertEqual("public", result[0][0])

    def test__methods_of_with_object(self):
        class fake_class(object):
            def public(self):
                pass

            def _private(self):
                pass
        mock_obj = fake_class()
        result = cliutils._methods_of(mock_obj)
        self.assertEqual(1, len(result))
        self.assertEqual("public", result[0][0])

    def test__methods_of_empty_result(self):
        class fake_class(object):
            def _private(self):
                pass

            def _private2(self):
                pass
        mock_obj = fake_class()
        result = cliutils._methods_of(mock_obj)
        self.assertEqual(result, [])

    def _unregister_opts(self):
        CONF.reset()
        category_opt = cfg.SubCommandOpt("category",
                                         title="Command categories",
                                         help="Available categories"
                                         )
        CONF.unregister_opt(category_opt)

    @mock.patch("rally.api.API",
                side_effect=exceptions.RallyException("config_file"))
    def test_run_fails(self, mock_rally_api_api):
        ret = cliutils.run(["rally", "version"], self.categories)
        self.assertEqual(ret, 2)
        mock_rally_api_api.assert_called_once_with(
            config_args=["version"], skip_db_check=False)

    @mock.patch("rally.api.API._check_db_revision")
    def test_run_version(self, mock_api__check_db_revision):
        ret = cliutils.run(["rally", "version"], self.categories)
        self.assertEqual(ret, 0)

    def test_run_skip_db_check(self):
        ret = cliutils.run(["rally", "version"], self.categories,
                           skip_db_check=True)
        self.assertEqual(ret, 0)

    @mock.patch("rally.api.API._check_db_revision")
    def test_run_bash_completion(self, mock_api__check_db_revision):
        ret = cliutils.run(["rally", "bash-completion"], self.categories)
        self.assertEqual(ret, 0)

    @mock.patch("rally.api.API._check_db_revision")
    @mock.patch("rally.common.db.task_get",
                side_effect=exceptions.TaskNotFound(uuid=FAKE_TASK_UUID))
    def test_run_task_not_found(self, mock_task_get,
                                mock_api__check_db_revision):
        ret = cliutils.run(["rally", "task", "status", "%s" % FAKE_TASK_UUID],
                           self.categories)
        self.assertTrue(mock_task_get.called)
        self.assertEqual(ret, 1)

    @mock.patch("rally.api.API._check_db_revision")
    @mock.patch("rally.cli.cliutils.validate_args",
                side_effect=cliutils.MissingArgs("missing"))
    def test_run_task_failed(self, mock_validate_args,
                             mock_api__check_db_revision):
        ret = cliutils.run(["rally", "task", "status", "%s" % FAKE_TASK_UUID],
                           self.categories)
        self.assertTrue(mock_validate_args.called)
        self.assertEqual(ret, 1)

    @mock.patch("rally.api.API._check_db_revision")
    def test_run_failed_to_open_file(self, mock_api__check_db_revision):

        class FailuresCommands(object):

            def failed_to_open_file(self):
                raise IOError("No such file")

        ret = cliutils.run(["rally", "failure", "failed-to-open-file"],
                           {"failure": FailuresCommands})
        self.assertEqual(1, ret)

    @mock.patch("rally.api.API._check_db_revision")
    def test_run_sqlalchmey_operational_failure(self,
                                                mock_api__check_db_revision):

        class SQLAlchemyCommands(object):

            def operational_failure(self):
                raise sqlalchemy.exc.OperationalError("Can't open DB file")

        ret = cliutils.run(["rally", "failure", "operational-failure"],
                           {"failure": SQLAlchemyCommands})
        self.assertEqual(1, ret)

    class TestObj(object):
        x = 1
        y = 2
        z = 3.142857142857143
        aOrB = 3  # mixed case field

    @ddt.data(
        {"args": [[TestObj()], ["x", "y"]],
         "kwargs": {"print_header": True,
                    "print_border": True,
                    "sortby_index": None},
         "expected": ("+---+---+\n"
                      "| x | y |\n"
                      "+---+---+\n"
                      "| 1 | 2 |\n"
                      "+---+---+")},
        {"args": [[TestObj()], ["z"]],
         "kwargs": {"print_header": True,
                    "print_border": True,
                    "sortby_index": None,
                    "formatters": {"z": cliutils.pretty_float_formatter("z",
                                                                        5)}},
         "expected": ("+---------+\n"
                      "| z       |\n"
                      "+---------+\n"
                      "| 3.14286 |\n"
                      "+---------+")},
        {"args": [[TestObj()], ["x"]],
         "kwargs": {"print_header": True,
                    "print_border": True},
         "expected": ("+---+\n"
                      "| x |\n"
                      "+---+\n"
                      "| 1 |\n"
                      "+---+")},
        {"args": [[TestObj()], ["x", "y"]],
         "kwargs": {"print_header": True,
                    "print_border": True},
         "expected": ("+---+---+\n"
                      "| x | y |\n"
                      "+---+---+\n"
                      "| 1 | 2 |\n"
                      "+---+---+")},
        {"args": [[TestObj()], ["x"]],
         "kwargs": {"print_header": False,
                    "print_border": False},
         "expected": "1"},
        {"args": [[TestObj()], ["x", "y"]],
         "kwargs": {"print_header": False,
                    "print_border": False},
         "expected": "1 2"},
        {"args": [[TestObj()], ["x"]],
         "kwargs": {"print_header": True,
                    "print_border": False},
         "expected": "x \n1"},
        {"args": [[TestObj()], ["x", "y"]],
         "kwargs": {"print_header": True,
                    "print_border": False},
         "expected": "x y \n1 2"},
        {"args": [[TestObj()], ["x"]],
         "kwargs": {"print_header": False,
                    "print_border": True},
         "expected": ("+--+\n"
                      "|1 |\n"
                      "+--+")},
        {"args": [[TestObj()], ["x", "y"]],
         "kwargs": {"print_header": False,
                    "print_border": True},
         "expected": ("+--+--+\n"
                      "|1 |2 |\n"
                      "+--+--+")},
        {"args": [[TestObj()], ["aOrB"]],
         "kwargs": {"print_header": True,
                    "print_border": True,
                    "mixed_case_fields": ["aOrB"]},
         "expected": ("+------+\n"
                      "| aOrB |\n"
                      "+------+\n"
                      "| 3    |\n"
                      "+------+")},
        {"args": [[TestObj()], ["aOrB"]],
         "kwargs": {"print_header": False,
                    "print_border": True,
                    "mixed_case_fields": ["aOrB"]},
         "expected": ("+--+\n"
                      "|3 |\n"
                      "+--+")},
        {"args": [[TestObj()], ["aOrB"]],
         "kwargs": {"print_header": True,
                    "print_border": False,
                    "mixed_case_fields": ["aOrB"]},
         "expected": "aOrB \n3"},
        {"args": [[TestObj()], ["aOrB"]],
         "kwargs": {"print_header": False,
                    "print_border": False,
                    "mixed_case_fields": ["aOrB"]},
         "expected": "3"},
        {"args": [[{"x": 1, "y": 2}], ["x", "y"]],
         "kwargs": {"print_header": True,
                    "print_border": True,
                    "sortby_index": None},
         "expected": ("+---+---+\n"
                      "| x | y |\n"
                      "+---+---+\n"
                      "| 1 | 2 |\n"
                      "+---+---+")},
        {"args": [[{"z": 3.142857142857143}], ["z"]],
         "kwargs": {"print_header": True,
                    "print_border": True,
                    "sortby_index": None,
                    "formatters": {"z": cliutils.pretty_float_formatter("z",
                                                                        5)}},
         "expected": ("+---------+\n"
                      "| z       |\n"
                      "+---------+\n"
                      "| 3.14286 |\n"
                      "+---------+")},
        {"args": [[{"x": 1}], ["x"]],
         "kwargs": {"print_header": True,
                    "print_border": True},
         "expected": ("+---+\n"
                      "| x |\n"
                      "+---+\n"
                      "| 1 |\n"
                      "+---+")},
        {"args": [[{"x": 1, "y": 2}], ["x", "y"]],
         "kwargs": {"print_header": True,
                    "print_border": True},
         "expected": ("+---+---+\n"
                      "| x | y |\n"
                      "+---+---+\n"
                      "| 1 | 2 |\n"
                      "+---+---+")})
    @ddt.unpack
    def test_print_list(self, args, kwargs, expected):
        out = six.moves.StringIO()
        kwargs["out"] = out
        cliutils.print_list(*args, **kwargs)
        self.assertEqual(expected, out.getvalue().strip())

    def test_print_list_raises(self):
        out = six.moves.StringIO()
        self.assertRaisesRegexp(
            ValueError,
            "Field labels list.*has different number "
            "of elements than fields list",
            cliutils.print_list,
            [self.TestObj()], ["x"],
            field_labels=["x", "y"], sortby_index=None, out=out)

    def test_help_for_grouped_methods(self):
        class SomeCommand(object):
            @cliutils.help_group("1_manage")
            def install(self):
                pass

            @cliutils.help_group("1_manage")
            def uninstall(self):
                pass

            @cliutils.help_group("1_manage")
            def reinstall(self):
                pass

            @cliutils.help_group("2_launch")
            def run(self):
                pass

            @cliutils.help_group("2_launch")
            def rerun(self):
                pass

            @cliutils.help_group("3_results")
            def show(self):
                pass

            @cliutils.help_group("3_results")
            def list(self):
                pass

            def do_do_has_do_has_mesh(self):
                pass

        self.assertEqual(
            "\n\nCommands:\n"
            "   do-do-has-do-has-mesh   \n"
            "\n"
            "   install                 \n"
            "   reinstall               \n"
            "   uninstall               \n"
            "\n"
            "   rerun                   \n"
            "   run                     \n"
            "\n"
            "   list                    \n"
            "   show                    \n",
            cliutils._compose_category_description(SomeCommand))


class ValidateArgsTest(test.TestCase):

    def test_lambda_no_args(self):
        cliutils.validate_args(lambda: None)

    def _test_lambda_with_args(self, *args, **kwargs):
        cliutils.validate_args(lambda x, y: None, *args, **kwargs)

    def test_lambda_positional_args(self):
        self._test_lambda_with_args(1, 2)

    def test_lambda_kwargs(self):
        self._test_lambda_with_args(x=1, y=2)

    def test_lambda_mixed_kwargs(self):
        self._test_lambda_with_args(1, y=2)

    def test_lambda_missing_args1(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_lambda_with_args)

    def test_lambda_missing_args2(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_lambda_with_args, 1)

    def test_lambda_missing_args3(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_lambda_with_args, y=2)

    def test_lambda_missing_args4(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_lambda_with_args, 1, x=2)

    def _test_lambda_with_default(self, *args, **kwargs):
        cliutils.validate_args(lambda x, y, z=3: None, *args, **kwargs)

    def test_lambda_positional_args_with_default(self):
        self._test_lambda_with_default(1, 2)

    def test_lambda_kwargs_with_default(self):
        self._test_lambda_with_default(x=1, y=2)

    def test_lambda_mixed_kwargs_with_default(self):
        self._test_lambda_with_default(1, y=2)

    def test_lambda_positional_args_all_with_default(self):
        self._test_lambda_with_default(1, 2, 3)

    def test_lambda_kwargs_all_with_default(self):
        self._test_lambda_with_default(x=1, y=2, z=3)

    def test_lambda_mixed_kwargs_all_with_default(self):
        self._test_lambda_with_default(1, y=2, z=3)

    def test_lambda_with_default_missing_args1(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_lambda_with_default)

    def test_lambda_with_default_missing_args2(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_lambda_with_default, 1)

    def test_lambda_with_default_missing_args3(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_lambda_with_default, y=2)

    def test_lambda_with_default_missing_args4(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_lambda_with_default, y=2, z=3)

    def test_function_no_args(self):
        def func():
            pass
        cliutils.validate_args(func)

    def _test_function_with_args(self, *args, **kwargs):
        def func(x, y):
            pass
        cliutils.validate_args(func, *args, **kwargs)

    def test_function_positional_args(self):
        self._test_function_with_args(1, 2)

    def test_function_kwargs(self):
        self._test_function_with_args(x=1, y=2)

    def test_function_mixed_kwargs(self):
        self._test_function_with_args(1, y=2)

    def test_function_missing_args1(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_function_with_args)

    def test_function_missing_args2(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_function_with_args, 1)

    def test_function_missing_args3(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_function_with_args, y=2)

    def _test_function_with_default(self, *args, **kwargs):
        def func(x, y, z=3):
            pass
        cliutils.validate_args(func, *args, **kwargs)

    def test_function_positional_args_with_default(self):
        self._test_function_with_default(1, 2)

    def test_function_kwargs_with_default(self):
        self._test_function_with_default(x=1, y=2)

    def test_function_mixed_kwargs_with_default(self):
        self._test_function_with_default(1, y=2)

    def test_function_positional_args_all_with_default(self):
        self._test_function_with_default(1, 2, 3)

    def test_function_kwargs_all_with_default(self):
        self._test_function_with_default(x=1, y=2, z=3)

    def test_function_mixed_kwargs_all_with_default(self):
        self._test_function_with_default(1, y=2, z=3)

    def test_function_with_default_missing_args1(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_function_with_default)

    def test_function_with_default_missing_args2(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_function_with_default, 1)

    def test_function_with_default_missing_args3(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_function_with_default, y=2)

    def test_function_with_default_missing_args4(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_function_with_default, y=2, z=3)

    def test_bound_method_no_args(self):
        class Foo(object):
            def bar(self):
                pass
        cliutils.validate_args(Foo().bar)

    def _test_bound_method_with_args(self, *args, **kwargs):
        class Foo(object):
            def bar(self, x, y):
                pass
        cliutils.validate_args(Foo().bar, *args, **kwargs)

    def test_bound_method_positional_args(self):
        self._test_bound_method_with_args(1, 2)

    def test_bound_method_kwargs(self):
        self._test_bound_method_with_args(x=1, y=2)

    def test_bound_method_mixed_kwargs(self):
        self._test_bound_method_with_args(1, y=2)

    def test_bound_method_missing_args1(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_bound_method_with_args)

    def test_bound_method_missing_args2(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_bound_method_with_args, 1)

    def test_bound_method_missing_args3(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_bound_method_with_args, y=2)

    def _test_bound_method_with_default(self, *args, **kwargs):
        class Foo(object):
            def bar(self, x, y, z=3):
                pass
        cliutils.validate_args(Foo().bar, *args, **kwargs)

    def test_bound_method_positional_args_with_default(self):
        self._test_bound_method_with_default(1, 2)

    def test_bound_method_kwargs_with_default(self):
        self._test_bound_method_with_default(x=1, y=2)

    def test_bound_method_mixed_kwargs_with_default(self):
        self._test_bound_method_with_default(1, y=2)

    def test_bound_method_positional_args_all_with_default(self):
        self._test_bound_method_with_default(1, 2, 3)

    def test_bound_method_kwargs_all_with_default(self):
        self._test_bound_method_with_default(x=1, y=2, z=3)

    def test_bound_method_mixed_kwargs_all_with_default(self):
        self._test_bound_method_with_default(1, y=2, z=3)

    def test_bound_method_with_default_missing_args1(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_bound_method_with_default)

    def test_bound_method_with_default_missing_args2(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_bound_method_with_default, 1)

    def test_bound_method_with_default_missing_args3(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_bound_method_with_default, y=2)

    def test_bound_method_with_default_missing_args4(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_bound_method_with_default, y=2, z=3)

    def test_unbound_method_no_args(self):
        class Foo(object):
            def bar(self):
                pass
        cliutils.validate_args(Foo.bar, Foo())

    def _test_unbound_method_with_args(self, *args, **kwargs):
        class Foo(object):
            def bar(self, x, y):
                pass
        cliutils.validate_args(Foo.bar, Foo(), *args, **kwargs)

    def test_unbound_method_positional_args(self):
        self._test_unbound_method_with_args(1, 2)

    def test_unbound_method_kwargs(self):
        self._test_unbound_method_with_args(x=1, y=2)

    def test_unbound_method_mixed_kwargs(self):
        self._test_unbound_method_with_args(1, y=2)

    def test_unbound_method_missing_args1(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_unbound_method_with_args)

    def test_unbound_method_missing_args2(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_unbound_method_with_args, 1)

    def test_unbound_method_missing_args3(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_unbound_method_with_args, y=2)

    def _test_unbound_method_with_default(self, *args, **kwargs):
        class Foo(object):
            def bar(self, x, y, z=3):
                pass
        cliutils.validate_args(Foo.bar, Foo(), *args, **kwargs)

    def test_unbound_method_positional_args_with_default(self):
        self._test_unbound_method_with_default(1, 2)

    def test_unbound_method_kwargs_with_default(self):
        self._test_unbound_method_with_default(x=1, y=2)

    def test_unbound_method_mixed_kwargs_with_default(self):
        self._test_unbound_method_with_default(1, y=2)

    def test_unbound_method_with_default_missing_args1(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_unbound_method_with_default)

    def test_unbound_method_with_default_missing_args2(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_unbound_method_with_default, 1)

    def test_unbound_method_with_default_missing_args3(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_unbound_method_with_default, y=2)

    def test_unbound_method_with_default_missing_args4(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_unbound_method_with_default, y=2, z=3)

    def test_class_method_no_args(self):
        class Foo(object):
            @classmethod
            def bar(cls):
                pass
        cliutils.validate_args(Foo.bar)

    def _test_class_method_with_args(self, *args, **kwargs):
        class Foo(object):
            @classmethod
            def bar(cls, x, y):
                pass
        cliutils.validate_args(Foo.bar, *args, **kwargs)

    def test_class_method_positional_args(self):
        self._test_class_method_with_args(1, 2)

    def test_class_method_kwargs(self):
        self._test_class_method_with_args(x=1, y=2)

    def test_class_method_mixed_kwargs(self):
        self._test_class_method_with_args(1, y=2)

    def test_class_method_missing_args1(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_class_method_with_args)

    def test_class_method_missing_args2(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_class_method_with_args, 1)

    def test_class_method_missing_args3(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_class_method_with_args, y=2)

    def _test_class_method_with_default(self, *args, **kwargs):
        class Foo(object):
            @classmethod
            def bar(cls, x, y, z=3):
                pass
        cliutils.validate_args(Foo.bar, *args, **kwargs)

    def test_class_method_positional_args_with_default(self):
        self._test_class_method_with_default(1, 2)

    def test_class_method_kwargs_with_default(self):
        self._test_class_method_with_default(x=1, y=2)

    def test_class_method_mixed_kwargs_with_default(self):
        self._test_class_method_with_default(1, y=2)

    def test_class_method_with_default_missing_args1(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_class_method_with_default)

    def test_class_method_with_default_missing_args2(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_class_method_with_default, 1)

    def test_class_method_with_default_missing_args3(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_class_method_with_default, y=2)

    def test_class_method_with_default_missing_args4(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_class_method_with_default, y=2, z=3)

    def test_static_method_no_args(self):
        class Foo(object):
            @staticmethod
            def bar():
                pass
        cliutils.validate_args(Foo.bar)

    def _test_static_method_with_args(self, *args, **kwargs):
        class Foo(object):
            @staticmethod
            def bar(x, y):
                pass
        cliutils.validate_args(Foo.bar, *args, **kwargs)

    def test_static_method_positional_args(self):
        self._test_static_method_with_args(1, 2)

    def test_static_method_kwargs(self):
        self._test_static_method_with_args(x=1, y=2)

    def test_static_method_mixed_kwargs(self):
        self._test_static_method_with_args(1, y=2)

    def test_static_method_missing_args1(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_static_method_with_args)

    def test_static_method_missing_args2(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_static_method_with_args, 1)

    def test_static_method_missing_args3(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_static_method_with_args, y=2)

    def _test_static_method_with_default(self, *args, **kwargs):
        class Foo(object):
            @staticmethod
            def bar(x, y, z=3):
                pass
        cliutils.validate_args(Foo.bar, *args, **kwargs)

    def test_static_method_positional_args_with_default(self):
        self._test_static_method_with_default(1, 2)

    def test_static_method_kwargs_with_default(self):
        self._test_static_method_with_default(x=1, y=2)

    def test_static_method_mixed_kwargs_with_default(self):
        self._test_static_method_with_default(1, y=2)

    def test_static_method_with_default_missing_args1(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_static_method_with_default)

    def test_static_method_with_default_missing_args2(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_static_method_with_default, 1)

    def test_static_method_with_default_missing_args3(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_static_method_with_default, y=2)

    def test_static_method_with_default_missing_args4(self):
        self.assertRaises(cliutils.MissingArgs,
                          self._test_static_method_with_default, y=2, z=3)

    def test_alias_decorator(self):
        alias_fn = mock.Mock(name="alias_fn")
        cmd_name = "test-command"
        wrapped = cliutils.alias(cmd_name)
        self.assertEqual(wrapped(alias_fn).alias, cmd_name)


class CategoryParserTestCase(test.TestCase):

    def setUp(self):
        super(CategoryParserTestCase, self).setUp()
        self.categoryParser = cliutils.CategoryParser()

    def test_format_help(self):
        self.assertIsNotNone(self.categoryParser.format_help())
