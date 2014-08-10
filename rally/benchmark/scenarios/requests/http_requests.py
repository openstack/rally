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

from rally.benchmark.scenarios import base as scenario_base
from rally import exceptions
from rally.openstack.common.gettextutils import _


class WrongStatusException(exceptions.RallyException):
    msg_fmt = _("Requests scenario exception: '%(message)s'")


class Requests(scenario_base.Scenario):
    """This class should contain all the http_request scenarios."""

    @scenario_base.scenario()
    def check_response(self, url, response=None):
        """Standard way to benchmark web services.

        This benchmark is used to GET a URL and check it with expected
        Response.

        :param url: URL to be fetched
        :param response: Expected Response Code
        """
        resp = requests.head(url)
        if response and response != resp.status_code:
            error = "Expected Response and Actual Response not equal"
            raise WrongStatusException(error)
