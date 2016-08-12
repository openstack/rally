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

import json

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.ceilometer import utils as ceiloutils
from rally.task import validation


@validation.required_services(consts.Service.CEILOMETER)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["ceilometer"]},
                    name="CeilometerQueries.create_and_query_alarms")
class CeilometerQueriesCreateAndQueryAlarms(ceiloutils.CeilometerScenario):
    """Benchmark scenarios for Ceilometer Queries API."""

    def run(self, meter_name, threshold, filter=None, orderby=None,
            limit=None, **kwargs):
        """Create an alarm and then query it with specific parameters.

        This scenario tests POST /v2/query/alarms
        An alarm is first created and then fetched using the input query.

        :param meter_name: specifies meter name of alarm
        :param threshold: specifies alarm threshold
        :param filter: optional filter query dictionary
        :param orderby: optional param for specifying ordering of results
        :param limit: optional param for maximum number of results returned
        :param kwargs: optional parameters for alarm creation
        """
        if filter:
            filter = json.dumps(filter)

        self._create_alarm(meter_name, threshold, kwargs)
        self._query_alarms(filter, orderby, limit)


@validation.required_services(consts.Service.CEILOMETER)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["ceilometer"]},
                    name="CeilometerQueries.create_and_query_alarm_history")
class CeilometerQueriesCreateAndQueryAlarmHistory(ceiloutils
                                                  .CeilometerScenario):
    """Benchmark scenarios for Ceilometer Queries API."""

    def run(self, meter_name, threshold, orderby=None, limit=None, **kwargs):
        """Create an alarm and then query for its history.

        This scenario tests POST /v2/query/alarms/history
        An alarm is first created and then its alarm_id is used to fetch the
        history of that specific alarm.

        :param meter_name: specifies meter name of alarm
        :param threshold: specifies alarm threshold
        :param orderby: optional param for specifying ordering of results
        :param limit: optional param for maximum number of results returned
        :param kwargs: optional parameters for alarm creation
        """
        alarm = self._create_alarm(meter_name, threshold, kwargs)
        alarm_filter = json.dumps({"=": {"alarm_id": alarm.alarm_id}})
        self._query_alarm_history(alarm_filter, orderby, limit)


@validation.required_services(consts.Service.CEILOMETER)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["ceilometer"]},
                    name="CeilometerQueries.create_and_query_samples")
class CeilometerQueriesCreateAndQuerySamples(ceiloutils.CeilometerScenario):
    """Benchmark scenarios for Ceilometer Queries API."""

    def run(self, counter_name, counter_type, counter_unit, counter_volume,
            resource_id, filter=None, orderby=None, limit=None, **kwargs):
        """Create a sample and then query it with specific parameters.

        This scenario tests POST /v2/query/samples
        A sample is first created and then fetched using the input query.

        :param counter_name: specifies name of the counter
        :param counter_type: specifies type of the counter
        :param counter_unit: specifies unit of the counter
        :param counter_volume: specifies volume of the counter
        :param resource_id: specifies resource id for the sample created
        :param filter: optional filter query dictionary
        :param orderby: optional param for specifying ordering of results
        :param limit: optional param for maximum number of results returned
        :param kwargs: parameters for sample creation
        """
        self._create_sample(counter_name, counter_type, counter_unit,
                            counter_volume, resource_id, **kwargs)

        if filter:
            filter = json.dumps(filter)
        self._query_samples(filter, orderby, limit)
