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

import fnmatch
import io
import os
import re

import testtools


class TestFormat(testtools.TestCase):
    def _check_lines_wrapping(self, doc_file, raw):
        code_block = False
        text_inside_simple_tables = False
        lines = raw.split("\n")
        for i, line in enumerate(lines):
            if code_block:
                if not line or line.startswith(" "):
                    continue
                else:
                    code_block = False
            if "::" in line:
                code_block = True
            # simple style tables also can fit >=80 symbols
            # open simple style table
            if ("===" in line or "---" in line) and not lines[i - 1]:
                text_inside_simple_tables = True
            if "http://" in line or "https://" in line or ":ref:" in line:
                continue
            # Allow lines which do not contain any whitespace
            if re.match("\s*[^\s]+$", line):
                continue
            if not text_inside_simple_tables:
                self.assertTrue(
                    len(line) < 80,
                    msg="%s:%d: Line limited to a maximum of 79 characters." %
                    (doc_file, i + 1))
            # close simple style table
            if "===" in line and not lines[i + 1]:
                text_inside_simple_tables = False

    def _check_no_cr(self, doc_file, raw):
        matches = re.findall("\r", raw)
        self.assertEqual(
            len(matches), 0,
            "Found %s literal carriage returns in file %s" %
            (len(matches), doc_file))

    def _check_trailing_spaces(self, doc_file, raw):
        for i, line in enumerate(raw.split("\n")):
            trailing_spaces = re.findall("\s+$", line)
            self.assertEqual(
                len(trailing_spaces), 0,
                "Found trailing spaces on line %s of %s" % (i + 1, doc_file))

    def test_lines(self):

        files = []
        docs_dir = os.path.join(os.path.dirname(__file__), os.pardir,
                                os.pardir, os.pardir, "doc")
        for root, dirnames, filenames in os.walk(docs_dir):
            for filename in fnmatch.filter(filenames, "*.rst"):
                files.append(os.path.join(root, filename))

        for filename in files:
            with io.open(filename, encoding="utf-8") as f:
                data = f.read()

            self._check_lines_wrapping(filename, data)
            self._check_no_cr(filename, data)
            self._check_trailing_spaces(filename, data)
