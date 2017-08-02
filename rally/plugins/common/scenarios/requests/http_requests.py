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

import random

from rally.plugins.common.scenarios.requests import utils
from rally.task import scenario


"""Scenarios for HTTP requests."""


@scenario.configure(name="HttpRequests.check_request")
class HttpRequestsCheckRequest(utils.RequestScenario):

    def run(self, url, method, status_code, **kwargs):
        """Standard way for testing web services using HTTP requests.

        This scenario is used to make request and check it with expected
        Response.

        :param url: url for the Request object
        :param method: method for the Request object
        :param status_code: expected response code
        :param kwargs: optional additional request parameters
        """

        self._check_request(url, method, status_code, **kwargs)


@scenario.configure(name="HttpRequests.check_random_request")
class HttpRequestsCheckRandomRequest(utils.RequestScenario):

    def run(self, requests, status_code):
        """Executes random HTTP requests from provided list.

        This scenario takes random url from list of requests, and raises
        exception if the response is not the expected response.

        :param requests: List of request dicts
        :param status_code: Expected Response Code it will
        be used only if we doesn't specified it in request proper
        """

        request = random.choice(requests)
        request.setdefault("status_code", status_code)
        self._check_request(**request)
