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

from rally.common import logging
from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.ceilometer import utils
from rally.task import validation


class CeilometerStats(utils.CeilometerScenario):
    """Benchmark scenarios for Ceilometer Stats API."""

    @logging.log_deprecated("Use 'get_stats' method, now samples are created"
                            "in context", "0.1.2")
    @validation.required_services(consts.Service.CEILOMETER)
    @validation.required_openstack(users=True)
    @scenario.configure()
    def create_meter_and_get_stats(self, **kwargs):
        """Create a meter and fetch its statistics.

        Meter is first created and then statistics is fetched for the same
        using GET /v2/meters/(meter_name)/statistics.

        :param kwargs: contains optional arguments to create a meter
        """
        meter = self._create_meter(**kwargs)
        self._get_stats(meter.counter_name)

    @validation.required_services(consts.Service.CEILOMETER)
    @validation.required_contexts("ceilometer")
    @validation.required_openstack(users=True)
    @scenario.configure()
    def get_stats(self, meter_name, filter_by_user_id=False,
                  filter_by_project_id=False, filter_by_resource_id=False,
                  metadata_query=None, period=None, groupby=None,
                  aggregates=None):
        """Fetch statistics for certain meter.

        Statistics is fetched for the using
        GET /v2/meters/(meter_name)/statistics.

        :param meter_name: meter to take statistic for
        :param filter_by_user_id: flag for query by user_id
        :param filter_by_project_id: flag for query by project_id
        :param filter_by_resource_id: flag for query by resource_id
        :param metadata_query: dict with metadata fields and values for query
        :param period: the length of the time range covered by these stats
        :param groupby: the fields used to group the samples
        :param aggregates: name of function for samples aggregation

        :returns: list of statistics data
        """
        query = self._make_general_query(filter_by_project_id,
                                         filter_by_user_id,
                                         filter_by_resource_id,
                                         metadata_query)
        self._get_stats(meter_name, query, period, groupby, aggregates)
