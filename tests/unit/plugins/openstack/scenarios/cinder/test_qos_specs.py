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

import mock

from rally import exceptions as rally_exceptions
from rally.plugins.openstack.scenarios.cinder import qos_specs
from tests.unit import test


class CinderQosTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(CinderQosTestCase, self).setUp()
        patch = mock.patch(
            "rally.plugins.openstack.services.storage.block.BlockStorage")
        self.addCleanup(patch.stop)
        self.mock_cinder = patch.start()

    def _get_context(self):
        context = test.get_test_context()
        context.update({
            "admin": {
                "id": "fake_user_id",
                "credential": mock.MagicMock()
            },
            "user": {"id": "fake_user_id",
                     "credential": mock.MagicMock()},
            "tenant": {"id": "fake", "name": "fake"}})
        return context

    def test_create_and_list_qos(self):
        mock_service = self.mock_cinder.return_value
        qos = mock.MagicMock()
        list_qos = [mock.MagicMock(),
                    mock.MagicMock(),
                    qos]

        specs = {"consumer": "both",
                 "write_iops_sec": "10",
                 "read_iops_sec": "1000"}

        scenario = qos_specs.CreateAndListQos(self._get_context())
        mock_service.create_qos.return_value = qos
        mock_service.list_qos.return_value = list_qos

        scenario.run(specs)
        mock_service.create_qos.assert_called_once_with(specs)
        mock_service.list_qos.assert_called_once_with()

    def test_create_and_list_qos_with_fails(self):
        mock_service = self.mock_cinder.return_value
        qos = mock.MagicMock()
        list_qos = [mock.MagicMock(),
                    mock.MagicMock(),
                    mock.MagicMock()]
        specs = {"consumer": "both",
                 "write_iops_sec": "10",
                 "read_iops_sec": "1000"}

        scenario = qos_specs.CreateAndListQos(self._get_context())
        mock_service.create_qos.return_value = qos
        mock_service.list_qos.return_value = list_qos

        self.assertRaises(rally_exceptions.RallyAssertionError,
                          scenario.run, specs)
        mock_service.create_qos.assert_called_once_with(specs)
        mock_service.list_qos.assert_called_once_with()

    def test_create_and_get_qos(self):
        mock_service = self.mock_cinder.return_value
        qos = mock.MagicMock()
        specs = {"consumer": "both",
                 "write_iops_sec": "10",
                 "read_iops_sec": "1000"}

        scenario = qos_specs.CreateAndGetQos(self._get_context())
        mock_service.create_qos.return_value = qos

        scenario.run(specs)
        mock_service.create_qos.assert_called_once_with(specs)
        mock_service.get_qos.assert_called_once_with(qos.id)
