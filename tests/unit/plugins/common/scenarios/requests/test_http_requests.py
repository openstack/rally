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

from rally.plugins.common.scenarios.requests import http_requests
from tests.unit import test

SCN = "rally.plugins.common.scenarios"


class RequestScenarioTestCase(test.TestCase):

    @mock.patch("%s.requests.utils.RequestScenario._check_request" % SCN)
    def test_check_request(self, mock__check_request):
        Requests = http_requests.HttpRequestsCheckRequest(
            test.get_test_context())
        Requests.run("sample_url", "GET", 200)
        mock__check_request.assert_called_once_with("sample_url", "GET", 200)

    @mock.patch("%s.requests.utils.RequestScenario._check_request" % SCN)
    @mock.patch("%s.requests.http_requests.random.choice" % SCN)
    def test_check_random_request(self, mock_choice, mock__check_request):
        mock_choice.return_value = {"url": "sample_url"}
        Requests = http_requests.HttpRequestsCheckRandomRequest(
            test.get_test_context())
        Requests.run(status_code=200,
                     requests=[{"url": "sample_url"}])
        mock_choice.assert_called_once_with([{"url": "sample_url"}])
        mock__check_request.assert_called_once_with(
            status_code=200, url="sample_url")
