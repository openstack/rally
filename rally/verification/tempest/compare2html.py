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

import os

__description__ = "List differences between two verification runs"
__title__ = "Verification Comparison"
__version__ = "0.1"


def create_report(results):
    import mako.template

    template_kw = {
        "heading": {
            "title": __title__,
            "description": __description__,
            "parameters": [("Difference Count", len(results))]
        },
        "generator": "compare2html %s" % __version__,
        "results": results
    }

    template_path = os.path.join(os.path.dirname(__file__),
                                 "report_templates",
                                 "compare.mako")

    with open(template_path) as f:
        template = mako.template.Template(f.read(), strict_undefined=True)
        output = template.render(**template_kw)
        return output.encode("utf8")
