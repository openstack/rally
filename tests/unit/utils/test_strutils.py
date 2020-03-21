# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
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

from unittest import mock
import uuid

import ddt

from rally.utils import strutils
from tests.unit import test


@ddt.ddt
class StrUtilsTestCase(test.TestCase):

    def test_is_uuid_like(self):
        self.assertTrue(strutils.is_uuid_like(str(uuid.uuid4())))
        self.assertTrue(strutils.is_uuid_like(
            "{12345678-1234-5678-1234-567812345678}"))
        self.assertTrue(strutils.is_uuid_like(
            "12345678123456781234567812345678"))
        self.assertTrue(strutils.is_uuid_like(
            "urn:uuid:12345678-1234-5678-1234-567812345678"))
        self.assertTrue(strutils.is_uuid_like(
            "urn:bbbaaaaa-aaaa-aaaa-aabb-bbbbbbbbbbbb"))
        self.assertTrue(strutils.is_uuid_like(
            "uuid:bbbaaaaa-aaaa-aaaa-aabb-bbbbbbbbbbbb"))
        self.assertTrue(strutils.is_uuid_like(
            "{}---bbb---aaa--aaa--aaa-----aaa---aaa--bbb-bbb---bbb-bbb-bb-{}"))

    def test_is_uuid_like_insensitive(self):
        self.assertTrue(strutils.is_uuid_like(str(uuid.uuid4()).upper()))

    def test_id_is_uuid_like(self):
        self.assertFalse(strutils.is_uuid_like(1234567))

    def test_name_is_uuid_like(self):
        self.assertFalse(strutils.is_uuid_like("asdasdasd"))

    @mock.patch("builtins.str")
    def test_bool_bool_from_string_no_text(self, mock_str):
        self.assertTrue(strutils.bool_from_string(True))
        self.assertFalse(strutils.bool_from_string(False))
        self.assertEqual(0, mock_str.call_count)

    def test_bool_bool_from_string(self):
        self.assertTrue(strutils.bool_from_string(True))
        self.assertFalse(strutils.bool_from_string(False))

    def test_bool_bool_from_string_default(self):
        self.assertTrue(strutils.bool_from_string("", default=True))
        self.assertFalse(strutils.bool_from_string("wibble", default=False))

    def _test_bool_from_string(self, c):
        self.assertTrue(strutils.bool_from_string(c("true")))
        self.assertTrue(strutils.bool_from_string(c("TRUE")))
        self.assertTrue(strutils.bool_from_string(c("on")))
        self.assertTrue(strutils.bool_from_string(c("On")))
        self.assertTrue(strutils.bool_from_string(c("yes")))
        self.assertTrue(strutils.bool_from_string(c("YES")))
        self.assertTrue(strutils.bool_from_string(c("yEs")))
        self.assertTrue(strutils.bool_from_string(c("1")))
        self.assertTrue(strutils.bool_from_string(c("T")))
        self.assertTrue(strutils.bool_from_string(c("t")))
        self.assertTrue(strutils.bool_from_string(c("Y")))
        self.assertTrue(strutils.bool_from_string(c("y")))

        self.assertFalse(strutils.bool_from_string(c("false")))
        self.assertFalse(strutils.bool_from_string(c("FALSE")))
        self.assertFalse(strutils.bool_from_string(c("off")))
        self.assertFalse(strutils.bool_from_string(c("OFF")))
        self.assertFalse(strutils.bool_from_string(c("no")))
        self.assertFalse(strutils.bool_from_string(c("0")))
        self.assertFalse(strutils.bool_from_string(c("42")))
        self.assertFalse(strutils.bool_from_string(c(
                         "This should not be True")))
        self.assertFalse(strutils.bool_from_string(c("F")))
        self.assertFalse(strutils.bool_from_string(c("f")))
        self.assertFalse(strutils.bool_from_string(c("N")))
        self.assertFalse(strutils.bool_from_string(c("n")))

        # Whitespace should be stripped
        self.assertTrue(strutils.bool_from_string(c(" 1 ")))
        self.assertTrue(strutils.bool_from_string(c(" true ")))
        self.assertFalse(strutils.bool_from_string(c(" 0 ")))
        self.assertFalse(strutils.bool_from_string(c(" false ")))

    def test_bool_from_string(self):
        self._test_bool_from_string(lambda s: s)

    def test_other_bool_from_string(self):
        self.assertFalse(strutils.bool_from_string(None))
        self.assertFalse(strutils.bool_from_string(mock.Mock()))

    def test_int_bool_from_string(self):
        self.assertTrue(strutils.bool_from_string(1))

        self.assertFalse(strutils.bool_from_string(-1))
        self.assertFalse(strutils.bool_from_string(0))
        self.assertFalse(strutils.bool_from_string(2))

    def test_strict_bool_from_string(self):
        # None isn"t allowed in strict mode
        exc = self.assertRaises(ValueError, strutils.bool_from_string, None,
                                strict=True)
        expected_msg = ("Unrecognized value 'None', acceptable values are:"
                        " '0', '1', 'f', 'false', 'n', 'no', 'off', 'on',"
                        " 't', 'true', 'y', 'yes'")
        self.assertEqual(expected_msg, str(exc))

        # Unrecognized strings aren't allowed
        self.assertFalse(strutils.bool_from_string("Other", strict=False))
        exc = self.assertRaises(ValueError, strutils.bool_from_string, "Other",
                                strict=True)
        expected_msg = ("Unrecognized value 'Other', acceptable values are:"
                        " '0', '1', 'f', 'false', 'n', 'no', 'off', 'on',"
                        " 't', 'true', 'y', 'yes'")
        self.assertEqual(expected_msg, str(exc))

        # Unrecognized numbers aren't allowed
        exc = self.assertRaises(ValueError, strutils.bool_from_string, 2,
                                strict=True)
        expected_msg = ("Unrecognized value '2', acceptable values are:"
                        " '0', '1', 'f', 'false', 'n', 'no', 'off', 'on',"
                        " 't', 'true', 'y', 'yes'")
        self.assertEqual(expected_msg, str(exc))

        # False-like values are allowed
        self.assertFalse(strutils.bool_from_string("f", strict=True))
        self.assertFalse(strutils.bool_from_string("false", strict=True))
        self.assertFalse(strutils.bool_from_string("off", strict=True))
        self.assertFalse(strutils.bool_from_string("n", strict=True))
        self.assertFalse(strutils.bool_from_string("no", strict=True))
        self.assertFalse(strutils.bool_from_string("0", strict=True))

        self.assertTrue(strutils.bool_from_string("1", strict=True))

        # Avoid font-similarity issues (one looks like lowercase-el, zero like
        # oh, etc...)
        for char in ("O", "o", "L", "l", "I", "i"):
            self.assertRaises(ValueError, strutils.bool_from_string, char,
                              strict=True)

    @ddt.data(
        {
            "num_float": 0,
            "num_str": "0.0"
        },
        {
            "num_float": 37,
            "num_str": "37.0"
        },
        {
            "num_float": 0.0000001,
            "num_str": "0.0"
        },
        {
            "num_float": 0.000000,
            "num_str": "0.0"
        },
        {
            "num_float": 1.0000001,
            "num_str": "1.0"
        },
        {
            "num_float": 1.0000011,
            "num_str": "1.000001"
        },
        {
            "num_float": 1.0000019,
            "num_str": "1.000002"
        }

    )
    @ddt.unpack
    def test_format_float_to_str(self, num_float, num_str):
        self.assertEqual(num_str, strutils.format_float_to_str(num_float))
