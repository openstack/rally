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

import mock

from rally.plugins.openstack.services.gnocchi import metric
from tests.unit import test


class GnocchiServiceTestCase(test.TestCase):
    def setUp(self):
        super(GnocchiServiceTestCase, self).setUp()
        self.clients = mock.MagicMock()
        self.name_generator = mock.MagicMock()
        self.service = metric.GnocchiService(
            self.clients,
            name_generator=self.name_generator)

    def atomic_actions(self):
        return self.service._atomic_actions

    def test__create_archive_policy(self):
        definition = [{"granularity": "0:00:01", "timespan": "1:00:00"}]
        aggregation_methods = [
            "std", "count", "95pct", "min", "max", "sum", "median", "mean"]
        archive_policy = {"name": "fake_name"}
        archive_policy["definition"] = definition
        archive_policy["aggregation_methods"] = aggregation_methods

        self.assertEqual(
            self.service.create_archive_policy(
                name="fake_name",
                definition=definition,
                aggregation_methods=aggregation_methods),
            self.service._clients.gnocchi().archive_policy.create(
                archive_policy)
        )
        self._test_atomic_action_timer(self.atomic_actions(),
                                       "gnocchi.create_archive_policy")

    def test__delete_archive_policy(self):
        self.service.delete_archive_policy("fake_name")
        self.service._clients.gnocchi().archive_policy.delete \
            .assert_called_once_with("fake_name")
        self._test_atomic_action_timer(self.atomic_actions(),
                                       "gnocchi.delete_archive_policy")

    def test__list_archive_policy(self):
        self.assertEqual(
            self.service.list_archive_policy(),
            self.service._clients.gnocchi().archive_policy.list.return_value
        )
        self._test_atomic_action_timer(self.atomic_actions(),
                                       "gnocchi.list_archive_policy")

    def test__create_archive_policy_rule(self):
        archive_policy_rule = {"name": "fake_name"}
        archive_policy_rule["metric_pattern"] = "cpu_*"
        archive_policy_rule["archive_policy_name"] = "low"

        self.assertEqual(
            self.service.create_archive_policy_rule(
                name="fake_name",
                metric_pattern="cpu_*",
                archive_policy_name="low"),
            self.service._clients.gnocchi().archive_policy_rule.create(
                archive_policy_rule)
        )
        self._test_atomic_action_timer(self.atomic_actions(),
                                       "gnocchi.create_archive_policy_rule")

    def test__delete_archive_policy_rule(self):
        self.service.delete_archive_policy_rule("fake_name")
        self.service._clients.gnocchi().archive_policy_rule \
            .delete.assert_called_once_with("fake_name")
        self._test_atomic_action_timer(self.atomic_actions(),
                                       "gnocchi.delete_archive_policy_rule")

    def test__list_archive_policy_rule(self):
        self.assertEqual(
            self.service.list_archive_policy_rule(),
            self.service._clients.gnocchi().archive_policy_rule.list
            .return_value
        )
        self._test_atomic_action_timer(self.atomic_actions(),
                                       "gnocchi.list_archive_policy_rule")

    def test__list_capabilities(self):
        self.assertEqual(
            self.service.list_capabilities(),
            self.service._clients.gnocchi().capabilities.list.return_value
        )
        self._test_atomic_action_timer(self.atomic_actions(),
                                       "gnocchi.list_capabilities")

    def test__get_measures_aggregation(self):
        self.assertEqual(
            self.service.get_measures_aggregation(
                metrics=[1],
                aggregation="mean",
                refresh=False),
            self.service._clients.gnocchi().metric.aggregation(
                [1], "mean", False)
        )
        self._test_atomic_action_timer(self.atomic_actions(),
                                       "gnocchi.get_measures_aggregation")

    def test__get_measures(self):
        self.assertEqual(
            self.service.get_measures(
                metric=1,
                aggregation="mean",
                refresh=False),
            self.service._clients.gnocchi().metric.get_measures(
                1, "mean", False)
        )
        self._test_atomic_action_timer(self.atomic_actions(),
                                       "gnocchi.get_measures")

    def test__create_metric(self):
        metric = {"name": "fake_name"}
        metric["archive_policy_name"] = "fake_archive_policy"
        metric["unit"] = "fake_unit"
        metric["resource_id"] = "fake_resource_id"
        self.assertEqual(
            self.service.create_metric(
                name="fake_name",
                archive_policy_name="fake_archive_policy",
                unit="fake_unit",
                resource_id="fake_resource_id"),
            self.service._clients.gnocchi().metric.create(metric)
        )
        self._test_atomic_action_timer(self.atomic_actions(),
                                       "gnocchi.create_metric")

    def test__delete_metric(self):
        self.service.delete_metric("fake_metric_id")
        self.service._clients.gnocchi().metric.delete.assert_called_once_with(
            "fake_metric_id")
        self._test_atomic_action_timer(self.atomic_actions(),
                                       "gnocchi.delete_metric")

    def test__list_metric(self):
        self.assertEqual(
            self.service.list_metric(),
            self.service._clients.gnocchi().metric.list.return_value
        )
        self._test_atomic_action_timer(self.atomic_actions(),
                                       "gnocchi.list_metric")

    def test__create_resource(self):
        resource = {"id": "11111"}
        self.assertEqual(
            self.service.create_resource("fake_type"),
            self.service._clients.gnocchi().resource.create(
                "fake_type", resource)
        )
        self._test_atomic_action_timer(self.atomic_actions(),
                                       "gnocchi.create_resource")

    def test__delete_resource(self):
        self.service.delete_resource("fake_resource_id")
        self.service._clients.gnocchi().resource.delete \
            .assert_called_once_with("fake_resource_id")
        self._test_atomic_action_timer(self.atomic_actions(),
                                       "gnocchi.delete_resource")

    def test__list_resource(self):
        self.assertEqual(
            self.service.list_resource(),
            self.service._clients.gnocchi().resource.list.return_value
        )
        self._test_atomic_action_timer(self.atomic_actions(),
                                       "gnocchi.list_resource")

    def test__create_resource_type(self):
        resource_type = {"name": "fake_name"}
        self.assertEqual(
            self.service.create_resource_type("fake_name"),
            self.service._clients.gnocchi().resource_type.create(resource_type)
        )
        self._test_atomic_action_timer(self.atomic_actions(),
                                       "gnocchi.create_resource_type")

    def test__delete_resource_type(self):
        self.service.delete_resource_type("fake_resource_name")
        self.service._clients.gnocchi().resource_type.delete \
            .assert_called_once_with("fake_resource_name")
        self._test_atomic_action_timer(self.atomic_actions(),
                                       "gnocchi.delete_resource_type")

    def test__list_resource_type(self):
        self.assertEqual(
            self.service.list_resource_type(),
            self.service._clients.gnocchi().resource_type.list.return_value
        )
        self._test_atomic_action_timer(self.atomic_actions(),
                                       "gnocchi.list_resource_type")

    def test__get_status(self,):
        self.assertEqual(
            self.service.get_status(),
            self.service._clients.gnocchi().status.get.return_value
        )
        self._test_atomic_action_timer(self.atomic_actions(),
                                       "gnocchi.get_status")
