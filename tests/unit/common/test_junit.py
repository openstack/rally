# Copyright 2015: eNovance
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

from rally.common import junit
from tests.unit import test


class JUnitTestCase(test.TestCase):
    def test_basic_testsuite(self):
        j = junit.JUnit("test")
        j.add_test("Foo.Bar", 3.14, outcome=junit.JUnit.SUCCESS)
        j.add_test("Foo.Baz", 13.37, outcome=junit.JUnit.FAILURE,
                   message="fail_message")
        j.add_test("Eggs.Spam", 42.00, outcome=junit.JUnit.ERROR)

        expected = """
<testsuite errors="1" failures="1" name="test" tests="3" time="58.51">
<testcase classname="Foo" name="Bar" time="3.14" />
<testcase classname="Foo" name="Baz" time="13.37">
<failure message="fail_message" /></testcase>
<testcase classname="Eggs" name="Spam" time="42.00">
<error message="" /></testcase></testsuite>"""
        self.assertEqual(expected.replace("\n", ""), j.to_xml())

    def test_empty_testsuite(self):
        j = junit.JUnit("test")
        expected = """
<testsuite errors="0" failures="0" name="test" tests="0" time="0.00" />"""
        self.assertEqual(expected.replace("\n", ""), j.to_xml())

    def test_invalid_outcome(self):
        j = junit.JUnit("test")
        self.assertRaises(ValueError, j.add_test, "Foo.Bar", 1.23,
                          outcome=1024)
