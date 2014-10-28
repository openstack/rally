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

from rally.benchmark.scenarios.zaqar import basic
from tests.unit import test

BASE = "rally.benchmark.scenarios.zaqar."
BASIC = BASE + "basic.ZaqarBasic."


class ZaqarBasicTestCase(test.TestCase):

    @mock.patch(BASIC + "_generate_random_name")
    def test_create_queue(self, mock_gen_name):
        scenario = basic.ZaqarBasic()
        mock_gen_name.return_value = "fizbit"
        scenario._queue_create = mock.MagicMock()
        scenario.create_queue(name_length=10)
        scenario._queue_create.assert_called_once_with(name_length=10)
