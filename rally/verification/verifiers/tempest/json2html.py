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

import os

import mako.template

__version__ = '0.1'


STATUS = {0: 'pass', 1: 'fail', 2: 'error', 3: 'skip'}

DEFAULT_TITLE = 'Unit Test Report'
DEFAULT_DESCRIPTION = ''


class HtmlOutput(object):
    """Output test results in html."""

    def __init__(self, result):
        self.success_count = result['success']
        self.failure_count = result['failures']
        self.error_count = result['errors']
        self.skip_count = result['skipped']
        self.total = result['tests']
        self.result = result['test_cases']
        self.abspath = os.path.dirname(__file__)

    def create_report(self):
        report_attrs = self._getReportAttributes()
        generator = 'json2html %s' % __version__
        heading = self._generate_heading(report_attrs)
        report = self._generate_report()
        with open("%s/report_templates/main.mako" % self.abspath) as main:
            template = mako.template.Template(main.read())
            output = template.render(title=DEFAULT_TITLE, generator=generator,
                                     heading=heading, report=report)
        return output.encode('utf8')

    def _getReportAttributes(self):
        """Return report attributes as a list of (name, value)."""
        status = []
        if self.success_count:
            status.append('Pass %s' % self.success_count)
        if self.failure_count:
            status.append('Failure %s' % self.failure_count)
        if self.error_count:
            status.append('Error %s' % self.error_count)
        if self.skip_count:
            status.append('Skip %s' % self.skip_count)
        if status:
            status = ' '.join(status)
        else:
            status = 'none'
        return [
            ('Status', status),
        ]

    def _generate_heading(self, report_attrs):
        return dict(title=DEFAULT_TITLE, parameters=report_attrs,
                    description=DEFAULT_DESCRIPTION)

    def _generate_report(self):
        rows = []
        sortedResult = self._sortResult(self.result)
        ne = self.error_count
        nf = self.failure_count
        cid = "c1"

        test_class = dict(
            style=(ne > 0 and 'errorClass' or nf > 0
                   and 'failClass' or 'passClass'),
            desc = "",
            count = self.total,
            Pass = self.success_count,
            fail = nf,
            error = ne,
            skipped = self.skip_count,
            cid = cid
        )

        for tid, name in enumerate(sortedResult):
            n = self.result[name]['status']
            o = self.result[name]['output']
            f = self.result[name].get('failure')
            e = ''
            if f:
                e = f['log']
            self._generate_report_test(rows, cid, tid, n, name, o, e)

        return dict(test_class=test_class, tests_list=rows,
                    count=str(self.success_count + self.failure_count +
                              self.error_count + self.skip_count),
                    Pass=str(self.success_count),
                    fail=str(self.failure_count),
                    error=str(self.error_count),
                    skip=str(self.skip_count))

    def _sortResult(self, results):
        # unittest does not seems to run in any particular order.
        # Here at least we want to group them together by class.
        return sorted(results)

    def _generate_report_test(self, rows, cid, tid, n, name, o, e):
        # e.g. 'pt1.1', 'ft1.1', etc
        # ptx.x for passed/skipped tests and ftx.x for failed/errored tests.
        status_map = {'OK': 0, 'SKIP': 3, 'FAIL': 1, 'ERROR': 2}
        n = status_map[n]
        tid = ((n == 0 or n == 3) and
               'p' or 'f') + 't%s.%s' % (cid, tid + 1)
        desc = name

        row = dict(
            tid=tid,
            Class=((n == 0 or n == 3) and 'hiddenRow' or 'none'),
            style=(n == 2 and 'errorCase' or
                   (n == 1 and 'failCase' or 'none')),
            desc=desc,
            output=o + e,
            status=STATUS[n],
        )
        rows.append(row)


def main(result):
    return HtmlOutput(result).create_report()
