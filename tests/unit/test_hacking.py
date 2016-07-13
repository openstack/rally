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

import tokenize

import ddt
import six

from tests.hacking import checks
from tests.unit import test


@ddt.ddt
class HackingTestCase(test.TestCase):

    def test__parse_assert_mock_str(self):
        pos, method, obj = checks._parse_assert_mock_str(
            "mock_clients.fake().quotas.delete.assert_called_once()")
        self.assertEqual("assert_called_once", method)
        self.assertEqual("mock_clients.fake().quotas.delete", obj)

    def test__parse_assert_mock_str_no_assert(self):
        pos, method, obj = checks._parse_assert_mock_str(
            "mock_clients.fake().quotas.delete.")
        self.assertIsNone(pos)
        self.assertIsNone(method)
        self.assertIsNone(obj)

    @ddt.data(
        {"line": "fdafadfdas  # noqa", "result": []},
        {"line": "  # fdafadfdas", "result": []},
        {"line": "  ", "result": []},
        {"line": "otherstuff", "result": [42]}
    )
    @ddt.unpack
    def test_skip_ignored_lines(self, line, result):

        @checks.skip_ignored_lines
        def any_gen(physical_line, logical_line, file_name):
            yield 42

        self.assertEqual(result, list(any_gen(line, line, "f")))

    def test_correct_usage_of_assert_from_mock(self):
        correct_method_names = ["assert_any_call", "assert_called_once_with",
                                "assert_called_with", "assert_has_calls"]
        for name in correct_method_names:
            line = "some_mock.%s(asd)" % name
            self.assertEqual(0, len(
                list(checks.check_assert_methods_from_mock(
                    line, line, "./tests/fake/test"))))

    def test_wrong_usage_of_broad_assert_from_mock(self):
        fake_method = "rtfm.assert_something()"

        actual_number, actual_msg = next(checks.check_assert_methods_from_mock(
            fake_method, fake_method, "./tests/fake/test"))
        self.assertEqual(4, actual_number)
        self.assertTrue(actual_msg.startswith("N301"))

    def test_wrong_usage_of_assert_called_from_mock(self):
        fake_method = "rtfm.assert_called()"

        actual_number, actual_msg = next(checks.check_assert_methods_from_mock(
            fake_method, fake_method, "./tests/fake/test"))
        self.assertEqual(4, actual_number)
        self.assertTrue(actual_msg.startswith("N302"))

    def test_wrong_usage_of_assert_called_once_from_mock(self):
        fake_method = "rtfm.assert_called_once()"

        actual_number, actual_msg = next(checks.check_assert_methods_from_mock(
            fake_method, fake_method, "./tests/fake/test"))
        self.assertEqual(4, actual_number)
        self.assertTrue(actual_msg.startswith("N303"))

    def _assert_good_samples(self, checker, samples, module_file="f"):
        for s in samples:
            self.assertEqual([], list(checker(s, s, module_file)), s)

    def _assert_bad_samples(self, checker, samples, module_file="f"):
        for s in samples:
            self.assertEqual(1, len(list(checker(s, s, module_file))), s)

    def test_check_wrong_logging_import(self):
        bad_imports = ["from oslo_log import log",
                       "import oslo_log",
                       "import logging"]
        good_imports = ["from rally.common import logging",
                        "from rally.common.logging",
                        "import rally.common.logging"]

        for bad in bad_imports:
            checkres = checks.check_import_of_logging(bad, bad, "fakefile")
            self.assertIsNotNone(next(checkres))

        for bad in bad_imports:
            checkres = checks.check_import_of_logging(
                bad, bad, "./rally/common/logging.py")
            self.assertEqual([], list(checkres))

        for good in good_imports:
            checkres = checks.check_import_of_logging(good, good, "fakefile")
            self.assertEqual([], list(checkres))

    def test_no_translate_debug_logs(self):

        bad_samples = ["LOG.debug(_('foo'))"]
        self._assert_bad_samples(checks.no_translate_debug_logs, bad_samples)
        good_samples = ["LOG.debug('foo')", "LOG.info(_('foo'))"]
        self._assert_good_samples(checks.no_translate_debug_logs, good_samples)

    def test_no_use_conf_debug_check(self):
        bad_samples = [
            "if CONF.debug:",
            "if cfg.CONF.debug"
        ]
        self._assert_bad_samples(checks.no_use_conf_debug_check, bad_samples)

        good_samples = ["if logging.is_debug()"]
        self._assert_good_samples(checks.no_use_conf_debug_check, good_samples)

    @ddt.data(
        {
            "line": "self.assertTrue(isinstance(e, exception.BuildAbortExc))",
            "result": 1
        },
        {
            "line": "self.assertTrue()",
            "result": 0
        }
    )
    @ddt.unpack
    def test_assert_true_instance(self, line, result):
        self.assertEqual(
            result, len(list(checks.assert_true_instance(line, line, "f"))))

    @ddt.data(
        {
            "line": "self.assertEqual(type(als['QuicAssist']), list)",
            "result": 1
        },
        {
            "line": "self.assertTrue()",
            "result": 0
        }
    )
    @ddt.unpack
    def test_assert_equal_type(self, line, result):
        self.assertEqual(
            len(list(checks.assert_equal_type(line, line, "f"))), result)

    @ddt.data(
        {"line": "self.assertEqual(A, None)", "result": 1},
        {"line": "self.assertEqual(None, A)", "result": 1},
        {"line": "self.assertIsNone()", "result": 0}
    )
    @ddt.unpack
    def test_assert_equal_none(self, line, result):

        self.assertEqual(
            len(list(checks.assert_equal_none(line, line, "f"))), result)

    @ddt.data(
        {"line": "self.assertNotEqual(A, None)", "result": 1},
        {"line": "self.assertNotEqual(None, A)", "result": 1},
        {"line": "self.assertIsNotNone()", "result": 0}
    )
    @ddt.unpack
    def test_assert_not_equal_none(self, line, result):

        self.assertEqual(
            len(list(checks.assert_not_equal_none(line, line, "f"))), result)

    def test_assert_true_or_false_with_in_or_not_in(self):
        good_lines = [
            "self.assertTrue(any(A > 5 for A in B))",
            "self.assertTrue(any(A > 5 for A in B), 'some message')",
            "self.assertFalse(some in list1 and some2 in list2)"
        ]
        self._assert_good_samples(checks.assert_true_or_false_with_in,
                                  good_lines)

        bad_lines = [
            "self.assertTrue(A in B)",
            "self.assertFalse(A in B)",
            "self.assertTrue(A not in B)",
            "self.assertFalse(A not in B)",
            "self.assertTrue(A in B, 'some message')",
            "self.assertFalse(A in B, 'some message')",
            "self.assertTrue(A not in B, 'some message')",
            "self.assertFalse(A not in B, 'some message')",
            "self.assertTrue(A in 'some string with spaces')",
            "self.assertTrue(A in 'some string with spaces')",
            "self.assertTrue(A in ['1', '2', '3'])",
            "self.assertTrue(A in [1, 2, 3])"
        ]
        self._assert_bad_samples(checks.assert_true_or_false_with_in,
                                 bad_lines)

    def test_assert_equal_in(self):
        good_lines = [
            "self.assertEqual(any(a==1 for a in b), True)",
            "self.assertEqual(True, any(a==1 for a in b))",
            "self.assertEqual(any(a==1 for a in b), False)",
            "self.assertEqual(False, any(a==1 for a in b))"
        ]
        self._assert_good_samples(checks.assert_equal_in, good_lines)

        bad_lines = [
            "self.assertEqual(a in b, True)",
            "self.assertEqual(a not in b, True)",
            "self.assertEqual('str' in 'string', True)",
            "self.assertEqual('str' not in 'string', True)",
            "self.assertEqual(True, a in b)",
            "self.assertEqual(True, a not in b)",
            "self.assertEqual(True, 'str' in 'string')",
            "self.assertEqual(True, 'str' not in 'string')",
            "self.assertEqual(a in b, False)",
            "self.assertEqual(a not in b, False)",
            "self.assertEqual('str' in 'string', False)",
            "self.assertEqual('str' not in 'string', False)",
            "self.assertEqual(False, a in b)",
            "self.assertEqual(False, a not in b)",
            "self.assertEqual(False, 'str' in 'string')",
            "self.assertEqual(False, 'str' not in 'string')",
        ]
        self._assert_bad_samples(checks.assert_equal_in, bad_lines)

    def test_check_no_direct_rally_objects_import(self):
        bad_imports = ["from rally.common.objects import task",
                       "import rally.common.objects.task"]

        self._assert_bad_samples(checks.check_no_direct_rally_objects_import,
                                 bad_imports)

        self._assert_good_samples(
            checks.check_no_direct_rally_objects_import,
            bad_imports,
            module_file="./rally/common/objects/__init__.py")

        good_imports = ["from rally.common import objects"]
        self._assert_good_samples(checks.check_no_direct_rally_objects_import,
                                  good_imports)

    def test_check_no_oslo_deprecated_import(self):
        bad_imports = ["from oslo.config",
                       "import oslo.config",
                       "from oslo.db",
                       "import oslo.db",
                       "from oslo.i18n",
                       "import oslo.i18n",
                       "from oslo.serialization",
                       "import oslo.serialization",
                       "from oslo.utils",
                       "import oslo.utils"]

        self._assert_bad_samples(checks.check_no_oslo_deprecated_import,
                                 bad_imports)

    def test_check_quotas(self):
        bad_lines = [
            "a = '1'",
            "a = \"a\" + 'a'",
            "'",
            "\"\"\"\"\"\" + ''''''"
        ]
        self._assert_bad_samples(checks.check_quotes, bad_lines)

        good_lines = [
            "\"'a'\" + \"\"\"a'''fdfd'''\"\"\"",
            "\"fdfdfd\" + \"''''''\"",
            "a = ''   # noqa "
        ]
        self._assert_good_samples(checks.check_quotes, good_lines)

    def test_check_no_constructor_data_struct(self):
        bad_struct = [
            "= dict()",
            "= list()"
        ]
        self._assert_bad_samples(checks.check_no_constructor_data_struct,
                                 bad_struct)

        good_struct = [
            "= []",
            "= {}",
        ]
        self._assert_good_samples(checks.check_no_constructor_data_struct,
                                  good_struct)

    def test_check_dict_formatting_in_string(self):
        bad = [
            "\"%(a)s\" % d",
            "\"Split across \"\n\"multiple lines: %(a)f\" % d",
            "\"%(a)X split across \"\n\"multiple lines\" % d",
            "\"%(a)-5.2f: Split %(\"\n\"a)#Lu stupidly\" % d",
            "\"Comment between \"  # wtf\n\"split lines: %(a) -6.2f\" % d",
            "\"Two strings\" + \" added: %(a)-6.2f\" % d",
            "\"half legit (%(a)s %(b)s)\" % d + \" half bogus: %(a)s\" % d",
            "(\"Parenthesized: %(a)s\") % d",
            "(\"Parenthesized \"\n\"concatenation: %(a)s\") % d",
            "(\"Parenthesized \" + \"addition: %(a)s\") % d",
            "\"Complete %s\" % (\"foolisness: %(a)s%(a)s\" % d)",
            "\"Modulus %(a)s\" % {\"a\": (5 % 3)}"
        ]
        for sample in bad:
            sample = "print(%s)" % sample
            tokens = tokenize.generate_tokens(
                six.moves.StringIO(sample).readline)
            self.assertEqual(
                1,
                len(list(checks.check_dict_formatting_in_string(sample,
                                                                tokens))))

        sample = "print(\"%(a)05.2lF\" % d + \" added: %(a)s\" % d)"
        tokens = tokenize.generate_tokens(six.moves.StringIO(sample).readline)
        self.assertEqual(
            2,
            len(list(checks.check_dict_formatting_in_string(sample, tokens))))

        good = [
            "\"This one is okay: %(a)s %(b)s\" % d",
            "\"So is %(a)s\"\n\"this one: %(b)s\" % d"
        ]
        for sample in good:
            sample = "print(%s)" % sample
            tokens = tokenize.generate_tokens(
                six.moves.StringIO(sample).readline)
            self.assertEqual(
                [],
                list(checks.check_dict_formatting_in_string(sample, tokens)))

    @ddt.data(
        "text = unicode('sometext')",
        "text = process(unicode('sometext'))"
    )
    def test_check_using_unicode(self, line):

        checkres = checks.check_using_unicode(line, line, "fakefile")
        self.assertIsNotNone(next(checkres))
        self.assertEqual([], list(checkres))

    def test_check_raises(self):
        checkres = checks.check_raises(
            "text = :raises: Exception if conditions", "fakefile")
        self.assertIsNotNone(checkres)

        checkres = checks.check_raises(
            "text = :raises Exception: if conditions", "fakefile")
        self.assertIsNone(checkres)

    def test_check_db_imports_of_cli(self):
        line = "from rally.common import db"

        next(checks.check_db_imports_in_cli(
            line, line, "./rally/cli/filename"))

        checkres = checks.check_db_imports_in_cli(
            line, line, "./filename")
        self.assertRaises(StopIteration, next, checkres)

    def test_check_objects_imports_of_cli(self):
        line = "from rally.common import objects"

        next(checks.check_objects_imports_in_cli(
            line, line, "./rally/cli/filename"))

        checkres = checks.check_objects_imports_in_cli(
            line, line, "./filename")
        self.assertRaises(StopIteration, next, checkres)

    @ddt.data(
        "class Oldstype():",
        "class Oldstyle:"
    )
    def test_check_old_type_class(self, line):
        checkres = checks.check_old_type_class(line, line, "fakefile")
        self.assertIsNotNone(next(checkres))
        self.assertEqual([], list(checkres))

    def test_check_datetime_alias(self):
        lines = ["import datetime as date",
                 "import datetime",
                 "import datetime as dto",
                 "from datetime import datetime as dtime"]

        for line in lines:
            checkres = checks.check_datetime_alias(line, line, "fakefile")
            self.assertIsNotNone(next(checkres))
            self.assertEqual([], list(checkres))

        line = "import datetime as dt"
        checkres = checks.check_datetime_alias(line, line, "fakefile")
