# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Guidelines for writing new hacking checks

 - Use only for Rally specific tests. OpenStack general tests
   should be submitted to the common 'hacking' module.
 - Pick numbers in the range N3xx. Find the current test with
   the highest allocated number and then pick the next value.
 - Keep the test method code in the source file ordered based
   on the N3xx value.
 - List the new rule in the top level HACKING.rst file
 - Add test cases for each new rule to tests/test_hacking.py

"""

import re


re_assert_true_instance = re.compile(
    r"(.)*assertTrue\(isinstance\((\w|\.|\'|\"|\[|\])+, "
    r"(\w|\.|\'|\"|\[|\])+\)\)")
re_assert_equal_type = re.compile(
    r"(.)*assertEqual\(type\((\w|\.|\'|\"|\[|\])+\), "
    r"(\w|\.|\'|\"|\[|\])+\)")
re_assert_equal_end_with_none = re.compile(r"assertEqual\(.*?,\s+None\)$")
re_assert_equal_start_with_none = re.compile(r"assertEqual\(None,")
re_assert_true_false_with_in_or_not_in = re.compile(
    r"assert(True|False)\("
    r"(\w|[][.'\"])+( not)? in (\w|[][.'\",])+(, .*)?\)")
re_assert_true_false_with_in_or_not_in_spaces = re.compile(
    r"assert(True|False)\((\w|[][.'\"])+( not)? in [\[|'|\"](\w|[][.'\", ])+"
    r"[\[|'|\"](, .*)?\)")
re_assert_equal_in_end_with_true_or_false = re.compile(
    r"assertEqual\((\w|[][.'\"])+( not)? in (\w|[][.'\", ])+, (True|False)\)")
re_assert_equal_in_start_with_true_or_false = re.compile(
    r"assertEqual\((True|False), (\w|[][.'\"])+( not)? in (\w|[][.'\", ])+\)")
re_iteritems_method = re.compile(r"\.iteritems\(\)")
re_basestring_method = re.compile(r"(^|[\s,(\[=])basestring([\s,)\]]|$)")
re_StringIO_method = re.compile(r"StringIO\.StringIO\(")
re_urlparse_method = re.compile(r"(^|[\s=])urlparse\.")
re_itertools_imap_method = re.compile(r"(^|[\s=])itertools\.imap\(")
re_xrange_method = re.compile(r"(^|[\s=])xrange\(")
re_string_lower_upper_case_method = re.compile(
    r"(^|[(,\s=])string\.(lower|upper)case([)\[,\s]|$)")
re_next_on_iterator_method = re.compile(r"\.next\(\)")


def _parse_assert_mock_str(line):
    point = line.find('.assert_')

    if point != -1:
        end_pos = line[point:].find('(') + point
        return point, line[point + 1: end_pos], line[: point]
    else:
        return None, None, None


def check_assert_methods_from_mock(logical_line, filename):
    """Ensure that ``assert_*`` methods from ``mock`` library is used correctly

    N301 - base error number
    N302 - related to nonexistent "assert_called"
    N303 - related to nonexistent "assert_called_once"
    """

    correct_names = ["assert_any_call", "assert_called_once_with",
                     "assert_called_with", "assert_has_calls"]
    ignored_files = ["./tests/unit/test_hacking.py"]

    if filename.startswith("./tests") and filename not in ignored_files:
        pos, method_name, obj_name = _parse_assert_mock_str(logical_line)

        if pos:
            if method_name not in correct_names:
                error_number = "N301"
                msg = ("%(error_number)s:'%(method)s' is not present in `mock`"
                       " library. %(custom_msg)s For more details, visit "
                       "http://www.voidspace.org.uk/python/mock/ .")

                if method_name == "assert_called":
                    error_number = "N302"
                    custom_msg = ("Maybe, you should try to use "
                                  "'assertTrue(%s.called)' instead." %
                                  obj_name)
                elif method_name == "assert_called_once":
                    # For more details, see a bug in Rally:
                    #    https://bugs.launchpad.net/rally/+bug/1305991
                    error_number = "N303"
                    custom_msg = ("Maybe, you should try to use "
                                  "'assertEqual(1, %(obj_name)s.call_count)' "
                                  "or '%(obj_name)s.assert_called_once_with()'"
                                  " instead." % {"obj_name": obj_name})
                else:
                    custom_msg = ("Correct 'assert_*' methods: '%s'."
                                  % "', '".join(correct_names))

                yield (pos, msg % {
                    "error_number": error_number,
                    "method": method_name,
                    "custom_msg": custom_msg})


def check_import_of_logging(logical_line, filename):
    """Check correctness import of logging module

    N310
    """

    excluded_files = ["./rally/log.py", "./tests/unit/test_log.py"]

    forbidden_imports = ["from rally.openstack.common import log",
                         "import rally.openstack.common.log",
                         "import logging"]

    if filename not in excluded_files:
        for forbidden_import in forbidden_imports:
            if logical_line.startswith(forbidden_import):
                yield (0, "N310 Wrong module for logging is imported. Please "
                          "use `rally.log` instead.")


def no_translate_debug_logs(logical_line):
    """Check for 'LOG.debug(_('

    As per our translation policy,
    https://wiki.openstack.org/wiki/LoggingStandards#Log_Translation
    we shouldn't translate debug level logs.

    * This check assumes that 'LOG' is a logger.
    * Use filename so we can start enforcing this in specific folders instead
      of needing to do so all at once.

    N311
    """
    if logical_line.startswith("LOG.debug(_("):
        yield(0, "N311 Don't translate debug level logs")


def no_use_conf_debug_check(logical_line, filename):
    """Check for 'cfg.CONF.debug'

    Rally has two DEBUG level:
     - Full DEBUG, which include all debug-messages from all OpenStack services
     - Rally DEBUG, which include only Rally debug-messages
    so we should use custom check to know debug-mode, instead of CONF.debug

    N312
    """
    excluded_files = ["./rally/log.py"]

    point = logical_line.find("CONF.debug")
    if point != -1 and filename not in excluded_files:
        yield(point, "N312 Don't use `CONF.debug`. "
                     "Function `rally.log.is_debug` should be used instead.")


def assert_true_instance(logical_line):
    """Check for assertTrue(isinstance(a, b)) sentences

    N320
    """
    if re_assert_true_instance.match(logical_line):
        yield (0, "N320 assertTrue(isinstance(a, b)) sentences not allowed, "
                  "you should use assertIsInstance(a, b) instead.")


def assert_equal_type(logical_line):
    """Check for assertEqual(type(A), B) sentences

    N321
    """
    if re_assert_equal_type.match(logical_line):
        yield (0, "N321 assertEqual(type(A), B) sentences not allowed, "
                  "you should use assertIsInstance(a, b) instead.")


def assert_equal_none(logical_line):
    """Check for assertEqual(A, None) or assertEqual(None, A) sentences

    N322
    """
    res = (re_assert_equal_start_with_none.search(logical_line) or
           re_assert_equal_end_with_none.search(logical_line))
    if res:
        yield (0, "N322 assertEqual(A, None) or assertEqual(None, A) "
                  "sentences not allowed, you should use assertIsNone(A) "
                  "instead.")


def assert_true_or_false_with_in(logical_line):
    """Check assertTrue/False(A in/not in B) with collection contents

    Check for assertTrue/False(A in B), assertTrue/False(A not in B),
    assertTrue/False(A in B, message) or assertTrue/False(A not in B, message)
    sentences.

    N323
    """
    res = (re_assert_true_false_with_in_or_not_in.search(logical_line) or
           re_assert_true_false_with_in_or_not_in_spaces.search(logical_line))
    if res:
        yield (0, "N323 assertTrue/assertFalse(A in/not in B)sentences not "
                  "allowed, you should use assertIn(A, B) or assertNotIn(A, B)"
                  " instead.")


def assert_equal_in(logical_line):
    """Check assertEqual(A in/not in B, True/False) with collection contents

    Check for assertEqual(A in B, True/False), assertEqual(True/False, A in B),
    assertEqual(A not in B, True/False) or assertEqual(True/False, A not in B)
    sentences.

    N324
    """
    res = (re_assert_equal_in_end_with_true_or_false.search(logical_line) or
           re_assert_equal_in_start_with_true_or_false.search(logical_line))
    if res:
        yield (0, "N324: Use assertIn/NotIn(A, B) rather than "
                  "assertEqual(A in/not in B, True/False) when checking "
                  "collection contents.")


def check_iteritems_method(logical_line):
    """Check if iteritems is properly called for compatibility with Python 3

    The correct form is six.iteritems(dict) or dict.items(), instead of
    dict.iteritems()

    N330
    """
    res = re_iteritems_method.search(logical_line)
    if res:
        yield (0, "N330: Use six.iteritems(dict) or dict.items() rather than "
                  "dict.iteritems() to iterate a collection.")


def check_basestring_method(logical_line):
    """Check if basestring is properly called for compatibility with Python 3

    There is no global variable "basestring" in Python 3.The correct form
    is six.string_types, instead of basestring.

    N331
    """
    res = re_basestring_method.search(logical_line)
    if res:
        yield (0, "N331: Use six.string_types rather than basestring.")


def check_StringIO_method(logical_line):
    """Check if StringIO is properly called for compatibility with Python 3

    In Python 3, StringIO module is gone. The correct form is
    six.moves.StringIO instead of StringIO.StringIO.

    N332
    """
    res = re_StringIO_method.search(logical_line)
    if res:
        yield (0, "N332: Use six.moves.StringIO "
                  "rather than StringIO.StringIO.")


def check_urlparse_method(logical_line):
    """Check if urlparse is properly called for compatibility with Python 3

    The correct form is six.moves.urllib.parse instead of "urlparse".

    N333
    """
    res = re_urlparse_method.search(logical_line)
    if res:
        yield (0, "N333: Use six.moves.urllib.parse rather than urlparse.")


def check_itertools_imap_method(logical_line):
    """Check if itertools.imap is properly called for compatibility with Python 3

    The correct form is six.moves.map instead of itertools.imap.

    N334
    """
    res = re_itertools_imap_method.search(logical_line)
    if res:
        yield (0, "N334: Use six.moves.map rather than itertools.imap.")


def check_xrange_method(logical_line):
    """Check if xrange is properly called for compatibility with Python 3

    The correct form is six.moves.range instead of xrange.

    N335
    """
    res = re_xrange_method.search(logical_line)
    if res:
        yield (0, "N335: Use six.moves.range rather than xrange.")


def check_string_lower_upper_case_method(logical_line):
    """Check if string.lowercase and string.uppercase are properly called

    In Python 3, string.lowercase and string.uppercase are gone.
    The correct form is "string.ascii_lowercase" and "string.ascii_uppercase".

    N336
    """
    res = re_string_lower_upper_case_method.search(logical_line)
    if res:
        yield (0, "N336: Use string.ascii_lowercase or string.ascii_uppercase "
                  "rather than string.lowercase or string.uppercase.")


def check_next_on_iterator_method(logical_line):
    """Check if next() method on iterator objects are properly called

    Python 3 introduced a next() function to replace the next() method on
    iterator objects. Rather than calling the method on the iterator,
    the next() function is called with the iterable object as it's sole
    parameter, which calls the underlying __next__() method.

    N337
    """
    res = re_next_on_iterator_method.search(logical_line)
    if res:
        yield (0, "N337: Use next(iterator) rather than iterator.next().")


def check_no_direct_rally_objects_import(logical_line, filename):
    """Check if rally.objects are properly imported.

    If you import "from rally import objects" you are able to use objects
    directly like objects.Task.

    N340
    """
    if filename == "./rally/objects/__init__.py":
        return

    if (logical_line.startswith("from rally.objects")
       or logical_line.startswith("import rally.objects.")):
        yield (0, "N340: Import objects module: `from rally import objects`. "
                  "After that you can use directly objects e.g. objects.Task")


def factory(register):
    register(check_assert_methods_from_mock)
    register(check_import_of_logging)
    register(no_translate_debug_logs)
    register(no_use_conf_debug_check)
    register(assert_true_instance)
    register(assert_equal_type)
    register(assert_equal_none)
    register(assert_true_or_false_with_in)
    register(assert_equal_in)
    register(check_iteritems_method)
    register(check_basestring_method)
    register(check_StringIO_method)
    register(check_urlparse_method)
    register(check_itertools_imap_method)
    register(check_xrange_method)
    register(check_string_lower_upper_case_method)
    register(check_next_on_iterator_method)
    register(check_no_direct_rally_objects_import)
