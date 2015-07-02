# Copyright 2015: Red Hat, Inc.
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

import sys

import testtools

from rally import exceptions
from rally.task import functional
from tests.unit import test


class FunctionalMixinTestCase(test.TestCase):

    def test_asserts(self):
        class A(functional.FunctionalMixin):
            def __init__(self):
                super(A, self).__init__()

        a = A()
        a.assertEqual(1, 1)
        self.assertRaises(exceptions.RallyAssertionError,
                          a.assertEqual, "a", "b")

        a.assertNotEqual(1, 2)
        self.assertRaises(exceptions.RallyAssertionError,
                          a.assertNotEqual, "a", "a")

        a.assertTrue(True)
        self.assertRaises(exceptions.RallyAssertionError,
                          a.assertTrue, False)

        a.assertFalse(False)
        self.assertRaises(exceptions.RallyAssertionError,
                          a.assertFalse, True)

        a.assertIs("a", "a")
        self.assertRaises(exceptions.RallyAssertionError,
                          a.assertIs, "a", "b")

        a.assertIsNot("a", "b")
        self.assertRaises(exceptions.RallyAssertionError,
                          a.assertIsNot, "a", "a")

        a.assertIsNone(None)
        self.assertRaises(exceptions.RallyAssertionError,
                          a.assertIsNone, "a")

        a.assertIsNotNone("a")
        self.assertRaises(exceptions.RallyAssertionError,
                          a.assertIsNotNone, None)

        a.assertIn("1", ["1", "2", "3"])
        self.assertRaises(exceptions.RallyAssertionError,
                          a.assertIn, "4", ["1", "2", "3"])

        a.assertNotIn("4", ["1", "2", "3"])
        self.assertRaises(exceptions.RallyAssertionError,
                          a.assertNotIn, "1", ["1", "2", "3"])

        a.assertIsInstance("a", str)
        self.assertRaises(exceptions.RallyAssertionError,
                          a.assertIsInstance, "a", int)

        a.assertIsNotInstance("a", int)
        self.assertRaises(exceptions.RallyAssertionError,
                          a.assertIsNotInstance, "a", str)

    @testtools.skipIf(sys.version_info < (2, 7),
                      "assertRaises as context not supported")
    def test_assert_with_custom_message(self):
        class A(functional.FunctionalMixin):
            def __init__(self):
                super(A, self).__init__()

        a = A()
        custom_message = "A custom message"
        assert_message = "Assertion error: .+\\. " + custom_message

        a.assertEqual(1, 1, "It's equal")
        message = self._catch_exception_message(a.assertEqual,
                                                "a", "b", custom_message)
        self.assertRegex(message, assert_message)

        a.assertNotEqual(1, 2)
        message = self._catch_exception_message(a.assertNotEqual,
                                                "a", "a", custom_message)
        self.assertRegex(message, assert_message)

        a.assertTrue(True)
        message = self._catch_exception_message(a.assertTrue,
                                                False, custom_message)
        self.assertRegex(message, assert_message)

        a.assertFalse(False)
        message = self._catch_exception_message(a.assertFalse,
                                                True, custom_message)
        self.assertRegex(message, assert_message)

        a.assertIs("a", "a")
        message = self._catch_exception_message(a.assertIs,
                                                "a", 1, custom_message)
        self.assertRegex(message, assert_message)

        a.assertIsNot("a", "b")
        message = self._catch_exception_message(a.assertIsNot,
                                                "a", "a", custom_message)
        self.assertRegex(message, assert_message)

        a.assertIsNone(None)
        message = self._catch_exception_message(a.assertIsNone,
                                                "a", custom_message)
        self.assertRegex(message, assert_message)

        a.assertIsNotNone("a")
        message = self._catch_exception_message(a.assertIsNotNone,
                                                None, custom_message)
        self.assertRegex(message, assert_message)

        a.assertIn("1", ["1", "2", "3"])
        message = self._catch_exception_message(a.assertIn,
                                                "1", ["2", "3", "4"],
                                                custom_message)
        self.assertRegex(message, assert_message)

        a.assertNotIn("4", ["1", "2", "3"])
        message = self._catch_exception_message(a.assertNotIn,
                                                "1", ["1", "2", "3"],
                                                custom_message)
        self.assertRegex(message, assert_message)

        a.assertIsInstance("a", str)
        message = self._catch_exception_message(a.assertIsInstance,
                                                "a", int, custom_message)
        self.assertRegex(message, assert_message)

        a.assertIsNotInstance("a", int)
        message = self._catch_exception_message(a.assertIsNotInstance,
                                                "a", str, custom_message)
        self.assertRegex(message, assert_message)

    def _catch_exception_message(self, func, *args):
        try:
            func(*args)
        except Exception as e:
            return str(e)
