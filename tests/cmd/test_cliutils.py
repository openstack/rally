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

from rally.cmd import cliutils
from tests import test


class CliUtilsTestCase(test.TestCase):

    def test_pretty_float_formatter_rounding(self):
        test_table_rows = {"test_header": 6.56565}
        self.__dict__.update(**test_table_rows)

        formatter = cliutils.pretty_float_formatter("test_header", 3)
        return_value = formatter(self)

        self.assertEqual(return_value, 6.566)

    def test_pretty_float_formatter_nonrounding(self):
        test_table_rows = {"test_header": 6.56565}
        self.__dict__.update(**test_table_rows)

        formatter = cliutils.pretty_float_formatter("test_header")
        return_value = formatter(self)

        self.assertEqual(return_value, 6.56565)

    def test_pretty_float_formatter_none_value(self):
        test_table_rows = {"test_header": None}
        self.__dict__.update(**test_table_rows)

        formatter = cliutils.pretty_float_formatter("test_header")
        return_value = formatter(self)

        self.assertEqual(return_value, "n/a")
