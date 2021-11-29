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

from rally.utils import encodeutils
from tests.unit import test


def b(s):
    return s.encode("latin-1")


class EncodeUtilsTestCase(test.TestCase):

    def test_safe_decode(self):
        safe_decode = encodeutils.safe_decode
        self.assertRaises(TypeError, safe_decode, True)
        self.assertEqual("ni\xf1o",
                         safe_decode(b("ni\xc3\xb1o"), incoming="utf-8"))
        self.assertEqual("strange",
                         safe_decode(b("\x80strange"), errors="ignore"))

        self.assertEqual("\xc0",
                         safe_decode(b("\xc0"), incoming="iso-8859-1"))

        # Forcing incoming to ascii so it falls back to utf-8
        self.assertEqual("ni\xf1o",
                         safe_decode(b("ni\xc3\xb1o"), incoming="ascii"))

        self.assertEqual("foo", safe_decode(b"foo"))

    def test_safe_encode_none_instead_of_text(self):
        self.assertRaises(TypeError, encodeutils.safe_encode, None)

    def test_safe_encode_bool_instead_of_text(self):
        self.assertRaises(TypeError, encodeutils.safe_encode, True)

    def test_safe_encode_int_instead_of_text(self):
        self.assertRaises(TypeError, encodeutils.safe_encode, 1)

    def test_safe_encode_list_instead_of_text(self):
        self.assertRaises(TypeError, encodeutils.safe_encode, [])

    def test_safe_encode_dict_instead_of_text(self):
        self.assertRaises(TypeError, encodeutils.safe_encode, {})

    def test_safe_encode_tuple_instead_of_text(self):
        self.assertRaises(TypeError, encodeutils.safe_encode, ("foo", "bar",))

    def test_safe_encode_force_incoming_utf8_to_ascii(self):
        # Forcing incoming to ascii so it falls back to utf-8
        self.assertEqual(
            b("ni\xc3\xb1o"),
            encodeutils.safe_encode(b("ni\xc3\xb1o"), incoming="ascii"),
        )

    def test_safe_encode_same_encoding_different_cases(self):
        with mock.patch.object(encodeutils, "safe_decode", mock.Mock()):
            utf8 = encodeutils.safe_encode(
                "foo\xf1bar", encoding="utf-8")
            self.assertEqual(
                encodeutils.safe_encode(utf8, "UTF-8", "utf-8"),
                encodeutils.safe_encode(utf8, "utf-8", "UTF-8"),
            )
            self.assertEqual(
                encodeutils.safe_encode(utf8, "UTF-8", "utf-8"),
                encodeutils.safe_encode(utf8, "utf-8", "utf-8"),
            )
            encodeutils.safe_decode.assert_has_calls([])

    def test_safe_encode_different_encodings(self):
        text = "foo\xc3\xb1bar"
        result = encodeutils.safe_encode(
            text=text, incoming="utf-8", encoding="iso-8859-1")
        self.assertNotEqual(text, result)

        self.assertNotEqual(b("foo\xf1bar"), result)
