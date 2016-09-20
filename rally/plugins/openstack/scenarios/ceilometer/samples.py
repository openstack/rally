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
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.ceilometer import utils as ceiloutils
from rally.task import validation


"""Scenarios for Ceilometer Samples API."""


@validation.required_services(consts.Service.CEILOMETER)
@validation.required_contexts("ceilometer")
@validation.required_openstack(users=True)
@scenario.configure(name="CeilometerSamples.list_matched_samples")
class ListMatchedSamples(ceiloutils.CeilometerScenario):

    def run(self, filter_by_resource_id=False, filter_by_project_id=False,
            filter_by_user_id=False, metadata_query=None, limit=None):
        """Get list of samples that matched fields from context and args.

        :param filter_by_user_id: flag for query by user_id
        :param filter_by_project_id: flag for query by project_id
        :param filter_by_resource_id: flag for query by resource_id
        :param metadata_query: dict with metadata fields and values for query
        :param limit: count of samples in response
        """
        query = self._make_general_query(filter_by_project_id,
                                         filter_by_user_id,
                                         filter_by_resource_id,
                                         metadata_query)
        self._list_samples(query, limit)


@validation.required_services(consts.Service.CEILOMETER)
@validation.required_contexts("ceilometer")
@validation.required_openstack(users=True)
@scenario.configure(name="CeilometerSamples.list_samples")
class ListSamples(ceiloutils.CeilometerScenario):

    def run(self, metadata_query=None, limit=None):
        """Fetch all available queries for list sample request.

        :param metadata_query: dict with metadata fields and values for query
        :param limit: count of samples in response
        """

        scenario = ListMatchedSamples(self.context)
        scenario.run(filter_by_project_id=True)
        scenario.run(filter_by_user_id=True)
        scenario.run(filter_by_resource_id=True)
        if metadata_query:
            scenario.run(metadata_query=metadata_query)
        if limit:
            scenario.run(limit=limit)