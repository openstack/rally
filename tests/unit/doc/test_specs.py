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

import glob
import os
import re

import docutils.core

from tests.unit import test


class TitlesTestCase(test.TestCase):

    specs_path = os.path.join(
        os.path.dirname(__file__),
        os.pardir, os.pardir, os.pardir,
        "doc", "specs")

    def _get_title(self, section_tree):
        section = {"subtitles": []}
        for node in section_tree:
            if node.tagname == "title":
                section["name"] = node.rawsource
            elif node.tagname == "section":
                subsection = self._get_title(node)
                section["subtitles"].append(subsection["name"])
        return section

    def _get_titles(self, spec):
        titles = {}
        for node in spec:
            if node.tagname == "section":
                # Note subsection subtitles are thrown away
                section = self._get_title(node)
                titles[section["name"]] = section["subtitles"]
        return titles

    def _check_titles(self, filename, expect, actual):
        missing_sections = [x for x in expect.keys() if x not in actual.keys()]
        extra_sections = [x for x in actual.keys() if x not in expect.keys()]

        msgs = []
        if missing_sections:
            msgs.append("Missing sections: %s" % missing_sections)
        if extra_sections:
            msgs.append("Extra sections: %s" % extra_sections)

        for section in expect.keys():
            missing_subsections = [x for x in expect[section]
                                   if x not in actual.get(section, {})]
            # extra subsections are allowed
            if missing_subsections:
                msgs.append("Section '%s' is missing subsections: %s"
                            % (section, missing_subsections))

        if msgs:
            self.fail("While checking '%s':\n  %s"
                      % (filename, "\n  ".join(msgs)))

    def _check_lines_wrapping(self, tpl, raw):
        for i, line in enumerate(raw.split("\n")):
            if "http://" in line or "https://" in line:
                continue
            self.assertTrue(
                len(line) < 80,
                msg="%s:%d: Line limited to a maximum of 79 characters." %
                (tpl, i+1))

    def _check_no_cr(self, tpl, raw):
        matches = re.findall("\r", raw)
        self.assertEqual(
            len(matches), 0,
            "Found %s literal carriage returns in file %s" %
            (len(matches), tpl))

    def _check_trailing_spaces(self, tpl, raw):
        for i, line in enumerate(raw.split("\n")):
            trailing_spaces = re.findall(" +$", line)
            self.assertEqual(
                len(trailing_spaces), 0,
                "Found trailing spaces on line %s of %s" % (i+1, tpl))

    def test_template(self):
        with open(os.path.join(self.specs_path, "template.rst")) as f:
            template = f.read()

        spec = docutils.core.publish_doctree(template)
        template_titles = self._get_titles(spec)

        for d in ["implemented", "in-progress"]:
            spec_dir = "%s/%s" % (self.specs_path, d)

            self.assertTrue(os.path.isdir(spec_dir),
                            "%s is not a directory" % spec_dir)
            for filename in glob.glob(spec_dir + "/*"):
                if filename.endswith("README.rst"):
                    continue

                self.assertTrue(
                    filename.endswith(".rst"),
                    "spec's file must have .rst ext. Found: %s" % filename)
                with open(filename) as f:
                    data = f.read()

                titles = self._get_titles(docutils.core.publish_doctree(data))
                self._check_titles(filename, template_titles, titles)
                self._check_lines_wrapping(filename, data)
                self._check_no_cr(filename, data)
                self._check_trailing_spaces(filename, data)
