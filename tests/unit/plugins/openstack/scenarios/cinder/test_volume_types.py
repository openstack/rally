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

from rally.plugins.openstack.scenarios.cinder import volume_types
from tests.unit import test


class CinderVolumeTypesTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(CinderVolumeTypesTestCase, self).setUp()
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

    def test_create_and_get_volume_type(self):
        mock_service = self.mock_cinder.return_value
        scenario = volume_types.CreateAndGetVolumeType(self._get_context())
        scenario.run(fakeargs="f")
        mock_service.create_volume_type.assert_called_once_with(fakeargs="f")
        mock_service.get_volume_type.assert_called_once_with(
            mock_service.create_volume_type.return_value)

    def test_create_and_delete_volume_type(self):
        mock_service = self.mock_cinder.return_value
        scenario = volume_types.CreateAndDeleteVolumeType(self._get_context())
        scenario.run(fakeargs="fakeargs")
        mock_service.create_volume_type.assert_called_once_with(
            fakeargs="fakeargs")
        mock_service.delete_volume_type.assert_called_once_with(
            mock_service.create_volume_type.return_value)

    def test_create_and_delete_encryption_type(self):
        mock_service = self.mock_cinder.return_value
        context = self._get_context()
        context.update({
            "volume_types": [{"id": "fake_id",
                              "name": "fake_name"}]})
        scenario = volume_types.CreateAndDeleteEncryptionType(context)
        scenario.run(create_specs="fakecreatespecs")
        mock_service.create_encryption_type.assert_called_once_with(
            "fake_id", specs="fakecreatespecs")
        mock_service.delete_encryption_type.assert_called_once_with(
            "fake_id")

    def test_create_volume_type_and_encryption_type(self):
        mock_service = self.mock_cinder.return_value
        scenario = volume_types.CreateVolumeTypeAndEncryptionType(
            self._get_context())
        scenario.run(specs="fakespecs", fakeargs="fakeargs")
        mock_service.create_volume_type.assert_called_once_with(
            fakeargs="fakeargs")
        mock_service.create_encryption_type.assert_called_once_with(
            mock_service.create_volume_type.return_value,
            specs="fakespecs")

    def test_create_and_list_encryption_type(self):
        mock_service = self.mock_cinder.return_value
        scenario = volume_types.CreateAndListEncryptionType(
            self._get_context())
        scenario.run(specs="fakespecs", search_opts="fakeopts",
                     fakeargs="fakeargs")
        mock_service.create_volume_type.assert_called_once_with(
            fakeargs="fakeargs")
        mock_service.create_encryption_type.assert_called_once_with(
            mock_service.create_volume_type.return_value,
            specs="fakespecs")
        mock_service.list_encryption_type.assert_called_once_with(
            "fakeopts")

    def test_create_and_set_volume_type_keys(self):
        mock_service = self.mock_cinder.return_value
        volume_type_key = {"volume_backend_name": "LVM_iSCSI"}
        scenario = volume_types.CreateAndSetVolumeTypeKeys(
            self._get_context())
        scenario.run(volume_type_key, fakeargs="fakeargs")

        mock_service.create_volume_type.assert_called_once_with(
            fakeargs="fakeargs")
        mock_service.set_volume_type_keys.assert_called_once_with(
            mock_service.create_volume_type.return_value,
            metadata=volume_type_key)
