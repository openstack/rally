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


"""Scenarios for Ceilometer Resource API."""


@validation.required_services(consts.Service.CEILOMETER)
@validation.required_contexts("ceilometer")
@validation.required_openstack(users=True)
@scenario.configure(name="CeilometerResource.list_resources")
class ListResources(ceiloutils.CeilometerScenario):

    def run(self, metadata_query=None, start_time=None,
            end_time=None, limit=None):
        """Check all available queries for list resource request.

        This scenario fetches list of all resources using GET /v2/resources.

        :param metadata_query: dict with metadata fields and values for query
        :param start_time: lower bound of resource timestamp in isoformat
        :param end_time: upper bound of resource timestamp in isoformat
        :param limit: count of resources in response
        """
        scenario = ListMatchedResources(self.context)
        scenario.run(filter_by_project_id=True)
        scenario.run(filter_by_user_id=True)
        scenario.run(filter_by_resource_id=True)
        if metadata_query:
            scenario.run(metadata_query=metadata_query)
        if start_time:
            scenario.run(start_time=start_time)
        if end_time:
            scenario.run(end_time=end_time)
        if start_time and end_time:
            scenario.run(start_time=start_time, end_time=end_time)
        if limit:
            scenario.run(limit=limit)


@validation.required_services(consts.Service.CEILOMETER)
@validation.required_openstack(users=True)
@scenario.configure(name="CeilometerResource.get_tenant_resources")
class GetTenantResources(ceiloutils.CeilometerScenario):

    def run(self):
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


@validation.required_services(consts.Service.CEILOMETER)
@validation.required_contexts("ceilometer")
@validation.required_openstack(users=True)
@scenario.configure(name="CeilometerResource.list_matched_resources")
class ListMatchedResources(ceiloutils.CeilometerScenario):

    def run(self, filter_by_user_id=False, filter_by_project_id=False,
            filter_by_resource_id=False, metadata_query=None, start_time=None,
            end_time=None, limit=None):
        """Get resources that matched fields from context and args.

        :param filter_by_user_id: flag for query by user_id
        :param filter_by_project_id: flag for query by project_id
        :param filter_by_resource_id: flag for query by resource_id
        :param metadata_query: dict with metadata fields and values for query
        :param start_time: lower bound of resource timestamp in isoformat
        :param end_time: upper bound of resource timestamp in isoformat
        :param limit: count of resources in response
        """

        query = self._make_general_query(filter_by_project_id,
                                         filter_by_user_id,
                                         filter_by_resource_id,
                                         metadata_query)
        query += self._make_timestamp_query(start_time, end_time)
        self._list_resources(query, limit)