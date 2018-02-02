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

from rally.plugins.openstack.scenarios.gnocchi import capabilities
from tests.unit import test


class GnocchiCapabilitiesTestCase(test.ScenarioTestCase):

    def get_test_context(self):
        context = super(GnocchiCapabilitiesTestCase, self).get_test_context()
        context.update({
            "user": {
                "user_id": "fake",
                "credential": mock.MagicMock()
            },
            "tenant": {"id": "fake"}
        })
        return context

    def setUp(self):
        super(GnocchiCapabilitiesTestCase, self).setUp()
        patch = mock.patch(
            "rally.plugins.openstack.services.gnocchi.metric.GnocchiService")
        self.addCleanup(patch.stop)
        self.mock_metric = patch.start()

    def test__list_capabilities(self):
        metric_service = self.mock_metric.return_value
        capabilities.ListCapabilities(self.context).run()
        metric_service.list_capabilities.assert_called_once_with()
