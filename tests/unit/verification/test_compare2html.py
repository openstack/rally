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

import mock

from rally.verification.tempest import compare2html
from tests.unit import test


class Compare2HtmlTestCase(test.TestCase):

    @mock.patch("rally.ui.utils.get_template")
    def test_main(self, mock_get_template):
        results = [{"val2": 0.0111, "field": u"time", "val1": 0.0222,
                    "type": "CHANGED", "test_name": u"test.one"},
                   {"val2": 0.111, "field": u"time", "val1": 0.222,
                    "type": "CHANGED", "test_name": u"test.two"},
                   {"val2": 1.11, "field": u"time", "val1": 2.22,
                    "type": "CHANGED", "test_name": u"test.three"}]

        fake_template_kw = {
            "heading": {
                "title": compare2html.__title__,
                "description": compare2html.__description__,
                "parameters": [("Difference Count", len(results))]
            },
            "generator": "compare2html %s" % compare2html.__version__,
            "results": results
        }

        template_mock = mock.MagicMock()
        mock_get_template.return_value = template_mock
        output_mock = mock.MagicMock()
        template_mock.render.return_value = output_mock
        compare2html.create_report(results)

        mock_get_template.assert_called_once_with("verification/compare.mako")
        template_mock.render.assert_called_once_with(**fake_template_kw)
        output_mock.encode.assert_called_once_with("utf8")
