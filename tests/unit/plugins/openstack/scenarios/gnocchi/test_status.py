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

from rally.plugins.openstack.scenarios.gnocchi import status
from tests.unit import test


class GnocchiStatusTestCase(test.ScenarioTestCase):

    def get_test_context(self):
        context = super(GnocchiStatusTestCase, self).get_test_context()
        context.update({
            "admin": {
                "user_id": "fake",
                "credential": mock.MagicMock()
            }
        })
        return context

    def setUp(self):
        super(GnocchiStatusTestCase, self).setUp()
        patch = mock.patch(
            "rally.plugins.openstack.services.gnocchi.metric.GnocchiService")
        self.addCleanup(patch.stop)
        self.mock_metric = patch.start()

    def test_get_status(self):
        metric_service = self.mock_metric.return_value
        status.GetStatus(self.context).run(False)
        metric_service.get_status.assert_called_once_with(False)
