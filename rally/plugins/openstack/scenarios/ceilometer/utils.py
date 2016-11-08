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

import datetime as dt

import six

from rally import exceptions
from rally.plugins.openstack import scenario
from rally.task import atomic
from rally.task import utils as bench_utils


class CeilometerScenario(scenario.OpenStackScenario):
    """Base class for Ceilometer scenarios with basic atomic actions."""

    def _make_samples(self, count=1, interval=0, counter_name="cpu_util",
                      counter_type="gauge", counter_unit="%", counter_volume=1,
                      project_id=None, user_id=None, source=None,
                      timestamp=None, metadata_list=None, batch_size=None):
        """Prepare and return a list of samples.

        :param count: specifies number of samples in array
        :param interval: specifies interval between timestamps of near-by
        samples
        :param counter_name: specifies name of the counter
        :param counter_type: specifies type of the counter
        :param counter_unit: specifies unit of the counter
        :param counter_volume: specifies volume of the counter
        :param project_id: specifies project id for samples
        :param user_id: specifies user id for samples
        :param source: specifies source for samples
        :param timestamp: specifies timestamp for samples
        :param metadata_list: specifies list of resource metadata
        :param batch_size: specifies number of samples to store in one query
        :returns: generator that produces lists of samples
        """
        batch_size = batch_size or count
        sample = {
            "counter_name": counter_name,
            "counter_type": counter_type,
            "counter_unit": counter_unit,
            "counter_volume": counter_volume,
            "resource_id": self.generate_random_name()
        }
        opt_fields = {
            "project_id": project_id,
            "user_id": user_id,
            "source": source,
            "timestamp": timestamp,
        }
        for k, v in opt_fields.items():
            if v:
                sample.update({k: v})
        len_meta = len(metadata_list) if metadata_list else 0
        now = timestamp or dt.datetime.utcnow()
        samples = []
        for i in six.moves.xrange(count):
            if i and not (i % batch_size):
                yield samples
                samples = []
            sample_item = dict(sample)
            sample_item["timestamp"] = (
                now - dt.timedelta(seconds=(interval * i))
            ).isoformat()
            if metadata_list:
                # NOTE(idegtiarov): Adding more than one template of metadata
                # required it's proportional distribution among whole samples.
                sample_item["resource_metadata"] = metadata_list[
                    i * len_meta // count
                ]
            samples.append(sample_item)
        yield samples

    def _make_query_item(self, field, op="eq", value=None):
        """Create a SimpleQuery item for requests.

        :param field: filtered field
        :param op: operator for filtering
        :param value: matched value

        :returns: dict with field, op and value keys for query
        """
        return {"field": field, "op": op, "value": value}

    def _make_general_query(self, filter_by_project_id=None,
                            filter_by_user_id=None,
                            filter_by_resource_id=None,
                            metadata_query=None):
        """Create a SimpleQuery for the list benchmarks.

        :param filter_by_project_id: add a project id to query
        :param filter_by_user_id: add a user id to query
        :param filter_by_resource_id: add a resource id to query
        :param metadata_query: metadata dict that will add to query

        :returns: SimpleQuery with specified items

        """
        query = []
        metadata_query = metadata_query or {}

        if filter_by_user_id:
            query.append(self._make_query_item("user_id", "eq",
                                               self.context["user"]["id"]))
        if filter_by_project_id:
            query.append(self._make_query_item(
                "project_id", "eq", self.context["tenant"]["id"]))
        if filter_by_resource_id:
            query.append(self._make_query_item(
                "resource_id", "eq", self.context["tenant"]["resources"][0]))

        for key, value in metadata_query.items():
            query.append(self._make_query_item("metadata.%s" % key,
                                               value=value))
        return query

    def _make_timestamp_query(self, start_time=None, end_time=None):
        """Create ceilometer query for timestamp range.

        :param start_time: start datetime in isoformat
        :param end_time: end datetime in isoformat
        :returns: query with timestamp range
        """
        query = []
        if end_time and start_time and end_time < start_time:
            msg = "End time should be great or equal than start time"
            raise exceptions.InvalidArgumentsException(msg)
        if start_time:
            query.append(self._make_query_item("timestamp", ">=", start_time))
        if end_time:
            query.append(self._make_query_item("timestamp", "<=", end_time))
        return query

    def _make_profiler_key(self, method, query=None, limit=None):
        """Create key for profiling method with query.

        :param method: Original profiler tag for method
        :param query: ceilometer query which fields will be added to key
        :param limit: if it exists `limit` will be added to key
        :returns: profiler key that includes method and queried fields
        """
        query = query or []
        limit_line = limit and "limit" or ""
        fields_line = "&".join("%s" % a["field"] for a in query)
        key_identifiers = "&".join(x for x in (limit_line, fields_line) if x)
        key = ":".join(x for x in (method, key_identifiers) if x)
        return key

    def _get_alarm_dict(self, **kwargs):
        """Prepare and return an alarm dict for creating an alarm.

        :param kwargs: optional parameters to create alarm
        :returns: alarm dictionary used to create an alarm
        """
        alarm_id = self.generate_random_name()
        alarm = {"alarm_id": alarm_id,
                 "name": alarm_id,
                 "description": "Test Alarm"}

        alarm.update(kwargs)
        return alarm

    @atomic.action_timer("ceilometer.list_alarms")
    def _list_alarms(self, alarm_id=None):
        """List alarms.

        List alarm matching alarm_id. It fetches all alarms
        if alarm_id is None.

        :param alarm_id: specifies id of the alarm
        :returns: list of alarms
        """
        if alarm_id:
            return self.clients("ceilometer").alarms.get(alarm_id)
        else:
            return self.clients("ceilometer").alarms.list()

    @atomic.action_timer("ceilometer.get_alarm")
    def _get_alarm(self, alarm_id):
        """Get detailed information of an alarm.

        :param alarm_id: Specifies id of the alarm
        :returns: If alarm_id is existed and correct, returns
                  detailed information of an alarm, else returns None
        """
        return self.clients("ceilometer").alarms.get(alarm_id)

    @atomic.action_timer("ceilometer.create_alarm")
    def _create_alarm(self, meter_name, threshold, kwargs):
        """Create an alarm.

        :param meter_name: specifies meter name of the alarm
        :param threshold: specifies alarm threshold
        :param kwargs: contains optional features of alarm to be created
        :returns: alarm
        """
        alarm_dict = self._get_alarm_dict(**kwargs)
        alarm_dict.update({"meter_name": meter_name,
                           "threshold": threshold})
        alarm = self.clients("ceilometer").alarms.create(**alarm_dict)
        return alarm

    @atomic.action_timer("ceilometer.delete_alarm")
    def _delete_alarm(self, alarm_id):
        """Delete an alarm.

        :param alarm_id: specifies id of the alarm
        """
        self.clients("ceilometer").alarms.delete(alarm_id)

    @atomic.action_timer("ceilometer.update_alarm")
    def _update_alarm(self, alarm_id, alarm_dict_delta):
        """Update an alarm.

        :param alarm_id: specifies id of the alarm
        :param alarm_dict_delta: features of alarm to be updated
        """
        self.clients("ceilometer").alarms.update(alarm_id, **alarm_dict_delta)

    @atomic.action_timer("ceilometer.get_alarm_history")
    def _get_alarm_history(self, alarm_id):
        """Assemble the alarm history requested.

        :param alarm_id: specifies id of the alarm
        :returns: list of alarm changes
        """
        return self.clients("ceilometer").alarms.get_history(alarm_id)

    @atomic.action_timer("ceilometer.get_alarm_state")
    def _get_alarm_state(self, alarm_id):
        """Get the state of the alarm.

        :param alarm_id: specifies id of the alarm
        :returns: state of the alarm
        """
        return self.clients("ceilometer").alarms.get_state(alarm_id)

    @atomic.action_timer("ceilometer.set_alarm_state")
    def _set_alarm_state(self, alarm, state, timeout):
        """Set the state of the alarm.

        :param alarm: alarm instance
        :param state: an alarm state to be set
        :param timeout: The number of seconds for which to attempt a
                         successful check of the alarm state.
        :returns: alarm in the set state
        """
        self.clients("ceilometer").alarms.set_state(alarm.alarm_id, state)
        return bench_utils.wait_for(alarm,
                                    ready_statuses=[state],
                                    update_resource=bench_utils
                                    .get_from_manager(),
                                    timeout=timeout, check_interval=1)

    @atomic.action_timer("ceilometer.list_events")
    def _list_events(self):
        """Get list of user's events.

        It fetches all events.
        :returns: list of events
        """
        return self.admin_clients("ceilometer").events.list()

    @atomic.action_timer("ceilometer.get_event")
    def _get_event(self, event_id):
        """Get event with specific id.

        Get event matching event_id.

        :param event_id: specifies id of the event
        :returns: event
        """
        return self.admin_clients("ceilometer").events.get(event_id)

    @atomic.action_timer("ceilometer.list_event_types")
    def _list_event_types(self):
        """Get list of all event types.

        :returns: list of event types
        """
        return self.admin_clients("ceilometer").event_types.list()

    @atomic.action_timer("ceilometer.list_event_traits")
    def _list_event_traits(self, event_type, trait_name):
        """Get list of event traits.

        :param event_type: specifies the type of event
        :param trait_name: specifies trait name
        :returns: list of event traits
        """
        return self.admin_clients("ceilometer").traits.list(event_type,
                                                            trait_name)

    @atomic.action_timer("ceilometer.list_event_trait_descriptions")
    def _list_event_trait_descriptions(self, event_type):
        """Get list of event trait descriptions.

        :param event_type: specifies the type of event
        :returns: list of event trait descriptions
        """
        return self.admin_clients("ceilometer").trait_descriptions.list(
            event_type)

    def _list_samples(self, query=None, limit=None):
        """List all Samples.

        :param query: optional param that specify query
        :param limit: optional param for maximum number of samples returned
        :returns: list of samples
        """
        key = self._make_profiler_key("ceilometer.list_samples", query,
                                      limit)
        with atomic.ActionTimer(self, key):
            return self.clients("ceilometer").new_samples.list(q=query,
                                                               limit=limit)

    @atomic.action_timer("ceilometer.get_resource")
    def _get_resource(self, resource_id):
        """Retrieve details about one resource."""
        return self.clients("ceilometer").resources.get(resource_id)

    @atomic.action_timer("ceilometer.get_stats")
    def _get_stats(self, meter_name, query=None, period=None, groupby=None,
                   aggregates=None):
        """Get stats for a specific meter.

        :param meter_name: Name of ceilometer meter
        :param query: list of queries
        :param period: the length of the time range covered by these stats
        :param groupby: the fields used to group the samples
        :param aggregates: function for samples aggregation

        :returns: list of statistics data
        """
        return self.clients("ceilometer").statistics.list(meter_name, q=query,
                                                          period=period,
                                                          groupby=groupby,
                                                          aggregates=aggregates
                                                          )

    @atomic.action_timer("ceilometer.create_meter")
    def _create_meter(self, **kwargs):
        """Create a new meter.

        :param kwargs: Contains the optional attributes for meter creation
        :returns: Newly created meter
        """
        name = self.generate_random_name()
        samples = self.clients("ceilometer").samples.create(
            counter_name=name, **kwargs)
        return samples[0]

    @atomic.action_timer("ceilometer.query_alarms")
    def _query_alarms(self, filter, orderby, limit):
        """Query alarms with specific parameters.

        If no input params are provided, it returns all the results
        in the database.

        :param limit: optional param for maximum number of results returned
        :param orderby: optional param for specifying ordering of results
        :param filter: optional filter query
        :returns: queried alarms
        """
        return self.clients("ceilometer").query_alarms.query(
            filter, orderby, limit)

    @atomic.action_timer("ceilometer.query_alarm_history")
    def _query_alarm_history(self, filter, orderby, limit):
        """Query history of an alarm.

        If no input params are provided, it returns all the results
        in the database.

        :param limit: optional param for maximum number of results returned
        :param orderby: optional param for specifying ordering of results
        :param filter: optional filter query
        :returns: alarm history
        """
        return self.clients("ceilometer").query_alarm_history.query(
            filter, orderby, limit)

    @atomic.action_timer("ceilometer.create_sample")
    def _create_sample(self, counter_name, counter_type, counter_unit,
                       counter_volume, resource_id=None, **kwargs):
        """Create a Sample with specified parameters.

        :param counter_name: specifies name of the counter
        :param counter_type: specifies type of the counter
        :param counter_unit: specifies unit of the counter
        :param counter_volume: specifies volume of the counter
        :param resource_id: specifies resource id for the sample created
        :param kwargs: contains optional parameters for creating a sample
        :returns: created sample
        """
        kwargs.update({"counter_name": counter_name,
                       "counter_type": counter_type,
                       "counter_unit": counter_unit,
                       "counter_volume": counter_volume,
                       "resource_id": resource_id if resource_id
                       else self.generate_random_name()})
        return self.clients("ceilometer").samples.create(**kwargs)

    @atomic.action_timer("ceilometer.create_samples")
    def _create_samples(self, samples):
        """Create Samples with specified parameters.

        :param samples: a list of samples to create
        :returns: created list samples
        """
        return self.clients("ceilometer").samples.create_list(samples)

    @atomic.action_timer("ceilometer.query_samples")
    def _query_samples(self, filter, orderby, limit):
        """Query samples with specified parameters.

        If no input params are provided, it returns all the results
        in the database.

        :param limit: optional param for maximum number of results returned
        :param orderby: optional param for specifying ordering of results
        :param filter: optional filter query
        :returns: queried samples
        """
        return self.clients("ceilometer").query_samples.query(
            filter, orderby, limit)

    def _list_resources(self, query=None, limit=None):
        """List all resources.

        :param query: query list for Ceilometer api
        :param limit: count of returned resources
        :returns: list of all resources
        """

        key = self._make_profiler_key("ceilometer.list_resources", query,
                                      limit)
        with atomic.ActionTimer(self, key):
            return self.clients("ceilometer").resources.list(q=query,
                                                             limit=limit)

    def _list_meters(self, query=None, limit=None):
        """Get list of user's meters.

        :param query: query list for Ceilometer api
        :param limit: count of returned meters
        :returns: list of all meters
        """

        key = self._make_profiler_key("ceilometer.list_meters", query,
                                      limit)
        with atomic.ActionTimer(self, key):
            return self.clients("ceilometer").meters.list(q=query,
                                                          limit=limit)
