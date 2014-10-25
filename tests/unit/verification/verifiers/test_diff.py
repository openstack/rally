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

from rally.verification.verifiers.tempest import diff
from tests.unit import test


class DiffTestCase(test.TestCase):

    def test_main(self):
        results1 = {'test.NONE': {'name': 'test.NONE',
                                  'output': 'test.NONE',
                                  'status': 'SKIPPED',
                                  'time': 0.000},
                    'test.one': {'name': 'test.one',
                                 'output': 'test.one',
                                 'status': 'OK',
                                 'time': 0.111},
                    'test.two': {'name': 'test.two',
                                 'output': 'test.two',
                                 'status': 'OK',
                                 'time': 0.222},
                    'test.three': {'name': 'test.three',
                                   'output': 'test.three',
                                   'status': 'FAILED',
                                   'time': 0.333},
                    'test.four': {'name': 'test.four',
                                  'output': 'test.four',
                                  'status': 'OK',
                                  'time': 0.444},
                    'test.five': {'name': 'test.five',
                                  'output': 'test.five',
                                  'status': 'OK',
                                  'time': 0.555}
                    }

        results2 = {'test.one': {'name': 'test.one',
                                 'output': 'test.one',
                                 'status': 'FAIL',
                                 'time': 0.1111},
                    'test.two': {'name': 'test.two',
                                 'output': 'test.two',
                                 'status': 'OK',
                                 'time': 0.222},
                    'test.three': {'name': 'test.three',
                                   'output': 'test.three',
                                   'status': 'OK',
                                   'time': 0.3333},
                    'test.four': {'name': 'test.four',
                                  'output': 'test.four',
                                  'status': 'FAIL',
                                  'time': 0.4444},
                    'test.five': {'name': 'test.five',
                                  'output': 'test.five',
                                  'status': 'OK',
                                  'time': 0.555},
                    'test.six': {'name': 'test.six',
                                 'output': 'test.six',
                                 'status': 'OK',
                                 'time': 0.666}
                    }

        diff_ = diff.Diff(results1, results2, 0)
        assert len(diff_.diffs) == 8
        assert diff_.to_csv() != ''
        assert diff_.to_html() != ''
        assert diff_.to_json() != ''
