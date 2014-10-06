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

from rally.verification.verifiers.tempest import json2html
from tests.unit import test


class Json2HtmlTestCase(test.TestCase):

    def test_main(self):

        data = {'tests': 4, 'skipped': 1, 'errors': 1, 'failures': 1,
                'success': 1, 'time': 22,
                'test_cases': {
                    'tp': {'name': 'tp', 'time': 2, 'status': 'OK',
                           'output': 'tp_ok'},
                    'ts': {'name': 'ts', 'time': 4, 'status': 'SKIP',
                           'output': 'ts_skip'},
                    'tf': {'name': 'tf', 'time': 6, 'status': 'FAIL',
                           'output': 'tf_fail',
                           'failure': {'type': 'tf', 'log': 'fail_log'}},
                    'te': {'name': 'te', 'time': 2, 'status': 'ERROR',
                           'output': 'te_error',
                           'failure': {'type': 'te', 'log': 'error+log'}}}}

        obj = json2html.HtmlOutput(data)
        self.assertEqual(obj.success_count, data['success'])
        self.assertEqual(obj.failure_count, data['failures'])
        self.assertEqual(obj.skip_count, data['skipped'])
        self.assertEqual(obj.error_count, data['errors'])

        report_attrs = obj._getReportAttributes()
        generator = 'json2html %s' % json2html.__version__
        heading = obj._generate_heading(report_attrs)
        report = obj._generate_report()
        with mock.patch('mako.template.Template') as mock_mako:
            obj.create_report()
            mock_mako().render.assert_called_once_with(
                title=json2html.DEFAULT_TITLE, generator=generator,
                heading=heading, report=report)
