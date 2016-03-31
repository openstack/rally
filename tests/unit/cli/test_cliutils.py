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
from six import moves
import sqlalchemy.exc

from rally.cli import cliutils
from rally.cli.commands import deployment
from rally.cli.commands import show
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
            "show": show.ShowCommands,
            "task": task.TaskCommands,
            "verify": verify.VerifyCommands
        }

    def tearDown(self):
        self._unregister_opts()
        super(CliUtilsTestCase, self).tearDown()

    @mock.patch("rally.cli.cliutils.os.path")
    def test_find_config_files(self, mock_os_path):

        mock_os_path.expanduser.return_value = "expanduser"
        mock_os_path.abspath.return_value = "abspath"
        mock_os_path.isfile.return_value = True

        result = cliutils.find_config_files(["path1", "path2"])
        mock_os_path.expanduser.assert_called_once_with("path1")
        mock_os_path.abspath.assert_called_once_with(
            mock_os_path.expanduser.return_value)
        mock_os_path.isfile.assert_called_once_with(
            mock_os_path.abspath.return_value + "/rally.conf")
        self.assertEqual([mock_os_path.abspath.return_value + "/rally.conf"],
                         result)

        mock_os_path.isfile.return_value = False

        result = cliutils.find_config_files(["path1", "path2"])
        self.assertIsNone(result)

    def test_make_header(self):
        h1 = cliutils.make_header("msg", size=4, symbol="=")
        self.assertEqual(h1, "====\n msg\n====\n")

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

    @mock.patch("rally.cli.cliutils.CONF", config_file=None,
                side_effect=cfg.ConfigFilesNotFoundError("config_file"))
    def test_run_fails(self, mock_cliutils_conf):
        ret = cliutils.run(["rally", "show", "flavors"], self.categories)
        self.assertEqual(ret, 2)

    def test_run_version(self):
        ret = cliutils.run(["rally", "version"], self.categories)
        self.assertEqual(ret, 0)

    def test_run_bash_completion(self):
        ret = cliutils.run(["rally", "bash-completion"], self.categories)
        self.assertEqual(ret, 0)

    def test_run_show(self):
        ret = cliutils.run(["rally", "show", "keypairs"], self.categories)
        self.assertEqual(ret, 1)

    @mock.patch("rally.common.db.task_get",
                side_effect=exceptions.TaskNotFound(uuid=FAKE_TASK_UUID))
    def test_run_task_not_found(self, mock_task_get):
        ret = cliutils.run(["rally", "task", "status", "%s" % FAKE_TASK_UUID],
                           self.categories)
        self.assertTrue(mock_task_get.called)
        self.assertEqual(ret, 1)

    @mock.patch("rally.cli.cliutils.validate_args",
                side_effect=cliutils.MissingArgs("missing"))
    def test_run_show_fails(self, mock_validate_args):
        ret = cliutils.run(["rally", "show", "keypairs"], self.categories)
        self.assertTrue(mock_validate_args.called)
        self.assertEqual(ret, 1)

    def test_run_failed_to_open_file(self):

        class FailuresCommands(object):

            def failed_to_open_file(self):
                raise IOError("No such file")

        ret = cliutils.run(["rally", "failure", "failed_to_open_file"],
                           {"failure": FailuresCommands})
        self.assertEqual(1, ret)

    def test_run_sqlalchmey_operational_failure(self):

        class SQLAlchemyCommands(object):

            def operational_failure(self):
                raise sqlalchemy.exc.OperationalError("Can't open DB file")

        ret = cliutils.run(["rally", "failure", "operational_failure"],
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
        out = moves.StringIO()
        kwargs["out"] = out
        cliutils.print_list(*args, **kwargs)
        self.assertEqual(expected, out.getvalue().strip())

    def test_print_list_raises(self):
        out = moves.StringIO()
        self.assertRaisesRegexp(
            ValueError,
            "Field labels list.*has different number "
            "of elements than fields list",
            cliutils.print_list,
            [self.TestObj()], ["x"],
            field_labels=["x", "y"], sortby_index=None, out=out)


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
