# Copyright 2017 Red Hat, Inc. <http://www.redhat.com>
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

from rally.task import atomic
from rally.task import service


class GnocchiService(service.Service):

    @atomic.action_timer("gnocchi.create_archive_policy")
    def create_archive_policy(self, name, definition=None,
                              aggregation_methods=None):
        """Create an archive policy.

        :param name: Archive policy name
        :param definition: Archive policy definition
        :param aggregation_methods: Aggregation method of the archive policy
        """
        archive_policy = {"name": name}
        archive_policy["definition"] = definition
        archive_policy["aggregation_methods"] = aggregation_methods
        return self._clients.gnocchi().archive_policy.create(
            archive_policy)

    @atomic.action_timer("gnocchi.delete_archive_policy")
    def delete_archive_policy(self, name):
        """Delete an archive policy.

        :param name: Archive policy name
        """
        return self._clients.gnocchi().archive_policy.delete(name)

    @atomic.action_timer("gnocchi.list_archive_policy")
    def list_archive_policy(self):
        """List archive policies."""
        return self._clients.gnocchi().archive_policy.list()

    @atomic.action_timer("gnocchi.create_archive_policy_rule")
    def create_archive_policy_rule(self, name, metric_pattern=None,
                                   archive_policy_name=None):
        """Create an archive policy rule.

        :param name: Archive policy rule name
        :param metric_pattern: Wildcard of metric name to match
        :param archive_policy_name: Archive policy name
        """
        archive_policy_rule = {"name": name}
        archive_policy_rule["metric_pattern"] = metric_pattern
        archive_policy_rule["archive_policy_name"] = archive_policy_name
        return self._clients.gnocchi().archive_policy_rule.create(
            archive_policy_rule)

    @atomic.action_timer("gnocchi.delete_archive_policy_rule")
    def delete_archive_policy_rule(self, name):
        """Delete an archive policy rule.

        :param name: Archive policy rule name
        """
        return self._clients.gnocchi().archive_policy_rule.delete(name)

    @atomic.action_timer("gnocchi.list_archive_policy_rule")
    def list_archive_policy_rule(self):
        """List archive policy rules."""
        return self._clients.gnocchi().archive_policy_rule.list()

    @atomic.action_timer("gnocchi.list_capabilities")
    def list_capabilities(self):
        """List capabilities."""
        return self._clients.gnocchi().capabilities.list()

    @atomic.action_timer("gnocchi.get_measures_aggregation")
    def get_measures_aggregation(self, metrics, aggregation=None,
                                 refresh=None):
        """Get measurements of aggregated metrics.

        :param metrics: Metric IDs or name
        :param aggregation: Granularity aggregation function to retrieve
        :param refresh: Force aggregation of all known measures
        """
        return self._clients.gnocchi().metric.aggregation(
            metrics=metrics, aggregation=aggregation, refresh=refresh)

    @atomic.action_timer("gnocchi.get_measures")
    def get_measures(self, metric, aggregation=None, refresh=None):
        """Get measurements of a metric.

        :param metric: Metric ID or name
        :param aggregation: Aggregation to retrieve
        :param refresh: Force aggregation of all known measures
        """
        return self._clients.gnocchi().metric.get_measures(
            metric=metric, aggregation=aggregation, refresh=refresh)

    @atomic.action_timer("gnocchi.create_metric")
    def create_metric(self, name, archive_policy_name=None, resource_id=None,
                      unit=None):
        """Create a metric.

        :param name: Metric name
        :param archive_policy_name: Archive policy name
        :param resource_id: The resource ID to attach the metric to
        :param unit: The unit of the metric
        """
        return self._clients.gnocchi().metric.create(
            name=name, archive_policy_name=archive_policy_name,
            resource_id=resource_id, unit=unit)

    @atomic.action_timer("gnocchi.delete_metric")
    def delete_metric(self, metric_id):
        """Delete a metric.

        :param metric_id: metric ID
        """
        return self._clients.gnocchi().metric.delete(metric_id)

    @atomic.action_timer("gnocchi.list_metric")
    def list_metric(self):
        """List metrics."""
        return self._clients.gnocchi().metric.list()

    @atomic.action_timer("gnocchi.create_resource")
    def create_resource(self, resource_type="generic"):
        """Create a resource.

        :param resource_type: Type of the resource
        """
        resource = {"id": self.generate_random_name()}
        return self._clients.gnocchi().resource.create(
            resource_type, resource)

    @atomic.action_timer("gnocchi.delete_resource")
    def delete_resource(self, resource_id):
        """Delete a resource.

        :param resource_id: ID of the resource
        """
        return self._clients.gnocchi().resource.delete(resource_id)

    @atomic.action_timer("gnocchi.list_resource")
    def list_resource(self, resource_type="generic"):
        """List resources."""
        return self._clients.gnocchi().resource.list(
            resource_type=resource_type)

    @atomic.action_timer("gnocchi.create_resource_type")
    def create_resource_type(self, name):
        """Create a resource type.

        :param name: Name of the resource type
        """
        resource_type = {"name": name or self.generate_random_name()}
        return self._clients.gnocchi().resource_type.create(
            resource_type)

    @atomic.action_timer("gnocchi.delete_resource_type")
    def delete_resource_type(self, resource_type):
        """Delete a resource type.

        :param resource_type: Resource type dict
        """
        return self._clients.gnocchi().resource_type.delete(resource_type)

    @atomic.action_timer("gnocchi.list_resource_type")
    def list_resource_type(self):
        """List resource types."""
        return self._clients.gnocchi().resource_type.list()

    @atomic.action_timer("gnocchi.get_status")
    def get_status(self, detailed=False):
        """Get the status of measurements processing.

        :param detailed: Get detailed status.
        """
        return self._clients.gnocchi().status.get(detailed)
