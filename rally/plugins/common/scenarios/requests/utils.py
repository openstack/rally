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

import requests

from rally.common.i18n import _
from rally.task import atomic
from rally.task import scenario


class RequestScenario(scenario.Scenario):
    """Base class for Request scenarios with basic atomic actions."""

    @atomic.action_timer("requests.check_request")
    def _check_request(self, url, method, status_code, **kwargs):
        """Compare request status code with specified code

        :param status_code: Expected status code of request
        :param url: Uniform resource locator
        :param method: Type of request method (GET | POST ..)
        :param kwargs: Optional additional request parameters
        :raises ValueError: if return http status code
                            not equal to expected status code
        """

        resp = requests.request(method, url, **kwargs)
        if status_code != resp.status_code:
            error_msg = _("Expected HTTP request code is `%s` actual `%s`")
            raise ValueError(
                error_msg % (status_code, resp.status_code))
