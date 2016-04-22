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

import ddt
import mock

from rally.plugins.openstack.scenarios.magnum import bays
from tests.unit import test


@ddt.ddt
class MagnumBaysTestCase(test.ScenarioTestCase):

    @staticmethod
    def _get_context():
        context = test.get_test_context()
        context.update({
            "tenant": {
                "id": "rally_tenant_id",
                "baymodel": "rally_baymodel_uuid"
            }
        })
        return context

    @ddt.data(
        {"kwargs": {}},
        {"kwargs": {"fakearg": "f"}})
    def test_list_bays(self, kwargs):
        scenario = bays.ListBays()
        scenario._list_bays = mock.Mock()

        scenario.run(**kwargs)

        scenario._list_bays.assert_called_once_with(**kwargs)

    def test_create_bay_with_existing_baymodel_and_list_bays(self):
        scenario = bays.CreateAndListBays()
        kwargs = {"baymodel_uuid": "existing_baymodel_uuid",
                  "fakearg": "f"}
        fake_bay = mock.Mock()
        scenario._create_bay = mock.Mock(return_value=fake_bay)
        scenario._list_bays = mock.Mock()

        scenario.run(2, **kwargs)

        scenario._create_bay.assert_called_once_with(
            "existing_baymodel_uuid", 2, **kwargs)
        scenario._list_bays.assert_called_once_with(**kwargs)

    def test_create_and_list_bays(self):
        context = self._get_context()
        scenario = bays.CreateAndListBays(context)
        fake_bay = mock.Mock()
        kwargs = {"fakearg": "f"}
        scenario._create_bay = mock.Mock(return_value=fake_bay)
        scenario._list_bays = mock.Mock()

        scenario.run(2, **kwargs)

        scenario._create_bay.assert_called_once_with(
            "rally_baymodel_uuid", 2, **kwargs)
        scenario._list_bays.assert_called_once_with(**kwargs)
