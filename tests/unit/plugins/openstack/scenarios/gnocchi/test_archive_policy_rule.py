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

from rally.plugins.openstack.scenarios.gnocchi import archive_policy_rule
from tests.unit import test


class GnocchiArchivePolicyRuleTestCase(test.ScenarioTestCase):

    def get_test_context(self):
        context = super(GnocchiArchivePolicyRuleTestCase,
                        self).get_test_context()
        context.update({
            "admin": {
                "user_id": "fake",
                "credential": mock.MagicMock()
            },
            "user": {
                "user_id": "fake",
                "credential": mock.MagicMock()
            },
            "tenant": {"id": "fake"}
        })
        return context

    def setUp(self):
        super(GnocchiArchivePolicyRuleTestCase, self).setUp()
        patch = mock.patch(
            "rally.plugins.openstack.services.gnocchi.metric.GnocchiService")
        self.addCleanup(patch.stop)
        self.mock_metric = patch.start()

    def test_list_archive_policy_rule(self):
        metric_service = self.mock_metric.return_value
        scenario = archive_policy_rule.ListArchivePolicyRule(self.context)
        scenario.run()
        metric_service.list_archive_policy_rule.assert_called_once_with()

    def test_create_archive_policy_rule(self):
        metric_service = self.mock_metric.return_value
        scenario = archive_policy_rule.CreateArchivePolicyRule(self.context)
        scenario.generate_random_name = mock.MagicMock(return_value="name")
        scenario.run(metric_pattern="foo_pat*", archive_policy_name="foo_pol")
        metric_service.create_archive_policy_rule.assert_called_once_with(
            "name", metric_pattern="foo_pat*", archive_policy_name="foo_pol")

    def test_create_delete_archive_policy_rule(self):
        metric_service = self.mock_metric.return_value
        scenario = archive_policy_rule.CreateDeleteArchivePolicyRule(
            self.context)
        scenario.generate_random_name = mock.MagicMock(return_value="name")
        scenario.run(metric_pattern="foo_pat*", archive_policy_name="foo_pol")
        metric_service.create_archive_policy_rule.assert_called_once_with(
            "name", metric_pattern="foo_pat*", archive_policy_name="foo_pol")
        metric_service.delete_archive_policy_rule.assert_called_once_with(
            "name")
