# Copyright 2015: Mirantis Inc.
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

from rally.common.plugin import info
from tests.unit import test


class DocstringTestCase(test.TestCase):

    def test_parse_complete_docstring(self):
        docstring = """One-line description.

Multi-
line-
description.

:param p1: Param 1 description.
:param p2: Param 2
           description.
:returns: Return value
          description.
"""

        expected = {
            "short_description": "One-line description.",
            "long_description": "Multi-\nline-\ndescription.",
            "params": [{"name": "p1", "doc": "Param 1 description.\n"},
                       {"name": "p2", "doc": "Param 2\n           "
                                             "description.\n"}],
            "returns": "Return value\ndescription."
        }
        self.assertEqual(expected, info.parse_docstring(docstring))

    def test_parse_incomplete_docstring(self):
        docstring = """One-line description.

:param p1: Param 1 description.
:param p2: Param 2
           description.
"""

        expected = {
            "short_description": "One-line description.",
            "long_description": "",
            "params": [{"name": "p1", "doc": "Param 1 description.\n"},
                       {"name": "p2", "doc": "Param 2\n           "
                                             "description."}],
            "returns": ""
        }
        self.assertEqual(expected, info.parse_docstring(docstring))

    def test_parse_docstring_with_no_params(self):
        docstring = """One-line description.

Multi-
line-
description.

:returns: Return value
          description.
"""

        expected = {
            "short_description": "One-line description.",
            "long_description": "Multi-\nline-\ndescription.",
            "params": [],
            "returns": "Return value\ndescription."
        }
        self.assertEqual(expected, info.parse_docstring(docstring))

    def test_parse_docstring_short_only(self):
        docstring = """One-line description."""

        expected = {
            "short_description": "One-line description.",
            "long_description": "",
            "params": [],
            "returns": ""
        }
        self.assertEqual(expected, info.parse_docstring(docstring))
