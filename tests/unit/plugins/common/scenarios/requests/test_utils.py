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

from rally.plugins.common.scenarios.requests import utils
from tests.unit import test


class RequestsTestCase(test.TestCase):

    @mock.patch("requests.request")
    def test__check_request(self, mock_request):
        mock_request.return_value = mock.MagicMock(status_code=200)
        scenario = utils.RequestScenario(test.get_test_context())
        scenario._check_request(status_code=200, url="sample", method="GET")

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "requests.check_request")
        mock_request.assert_called_once_with("GET", "sample")

    @mock.patch("requests.request")
    def test_check_wrong_request(self, mock_request):
        mock_request.return_value = mock.MagicMock(status_code=200)
        scenario = utils.RequestScenario(test.get_test_context())

        self.assertRaises(ValueError, scenario._check_request,
                          status_code=201, url="sample", method="GET")
