# All Rights Reserved.
#
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

from rally import consts
from rally import exceptions
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.ceilometer import utils as ceiloutils
from rally.task import validation


class CeilometerResource(ceiloutils.CeilometerScenario):
    """Benchmark scenarios for Ceilometer Resource API."""

    @validation.required_services(consts.Service.CEILOMETER)
    @validation.required_openstack(users=True)
    @scenario.configure()
    def list_resources(self):
        """Fetch all resources.

        This scenario fetches list of all resources using GET /v2/resources.
        """
        self._list_resources()

    @validation.required_services(consts.Service.CEILOMETER)
    @validation.required_openstack(users=True)
    @scenario.configure()
    def get_tenant_resources(self):
        """Get all tenant resources.

        This scenario retrieves information about tenant resources using
        GET /v2/resources/(resource_id)
        """
        resources = self.context["tenant"].get("resources", [])
        if not resources:
            msg = ("No resources found for tenant: %s"
                   % self.context["tenant"].get("name"))
            raise exceptions.NotFoundException(message=msg)
        for res_id in resources:
            self._get_resource(res_id)
