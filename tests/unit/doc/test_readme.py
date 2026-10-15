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

import io
import os

from docutils import core
from docutils import nodes
from docutils import utils

import rally
from tests.unit import test


ROOT_DIR = os.path.dirname(os.path.dirname(rally.__file__))


class ReadmeTestCase(test.TestCase):
    """README.rst is the PyPI description, rendered without Sphinx.

    PyPI runs plain docutils with raw HTML and file inclusion disabled, so
    any Sphinx-only directive or role (toctree, ref, ...) breaks the whole
    page, and paths relative to the repository lead nowhere.
    """

    def test_readme_renders_on_pypi(self) -> None:
        full_path = os.path.join(ROOT_DIR, "README.rst")
        with open(full_path) as f:
            text = f.read()

        warnings = io.StringIO()
        try:
            doctree = core.publish_doctree(
                text,
                source_path=full_path,
                settings_overrides={
                    "raw_enabled": False,
                    "file_insertion_enabled": False,
                    "halt_level": 2,
                    "warning_stream": warnings,
                },
            )
        except utils.SystemMessage as e:
            self.fail(f"{full_path} does not render with plain docutils "
                      f"(as PyPI does it): {e}")

        for node in doctree.findall(nodes.image):
            with self.subTest(image=node["uri"]):
                self.assertRegex(node["uri"], r"^https?://")
        for node in doctree.findall(nodes.reference):
            if "refuri" not in node:
                continue
            with self.subTest(link=node["refuri"]):
                self.assertRegex(node["refuri"], r"^(https?://|mailto:)")
