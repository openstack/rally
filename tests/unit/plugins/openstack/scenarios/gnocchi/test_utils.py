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

from rally.plugins.openstack.scenarios.gnocchi import utils
from tests.unit import test


class GnocchiBaseTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(GnocchiBaseTestCase, self).setUp()
        self.context = super(GnocchiBaseTestCase, self).get_test_context()
        self.context.update({
            "admin": {
                "id": "fake_user_id",
                "credential": mock.MagicMock()
            },
            "user": {
                "id": "fake_user_id",
                "credential": mock.MagicMock()
            },
            "tenant": {"id": "fake_tenant_id",
                       "name": "fake_tenant_name"}
        })
        patch = mock.patch(
            "rally.plugins.openstack.services.gnocchi.metric.GnocchiService")
        self.addCleanup(patch.stop)
        self.mock_service = patch.start()

    def test__gnocchi_base(self):
        base = utils.GnocchiBase(self.context)
        self.assertEqual(base.admin_gnocchi,
                         self.mock_service.return_value)
        self.assertEqual(base.gnocchi,
                         self.mock_service.return_value)
