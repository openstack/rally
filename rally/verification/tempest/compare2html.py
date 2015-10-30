# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""Output verification comparison results in html."""

from rally.ui import utils as ui_utils

__description__ = "List differences between two verification runs"
__title__ = "Verification Comparison"
__version__ = "0.1"


def create_report(results):
    template_kw = {
        "heading": {
            "title": __title__,
            "description": __description__,
            "parameters": [("Difference Count", len(results))]
        },
        "generator": "compare2html %s" % __version__,
        "results": results
    }

    template = ui_utils.get_template("verification/compare.mako")
    output = template.render(**template_kw)

    return output.encode("utf8")
