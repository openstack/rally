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
from rally.plugins.openstack.scenarios.cinder import volume_types
from tests.unit import test

CINDER_V2_PATH = ("rally.plugins.openstack.services.storage"
                  ".cinder_v2.CinderV2Service")


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
        description = "rally tests creating types"
        is_public = False
        scenario.run(description=description, is_public=is_public)
        mock_service.create_volume_type.assert_called_once_with(
            description=description, is_public=is_public)
        mock_service.get_volume_type.assert_called_once_with(
            mock_service.create_volume_type.return_value)

    def test_create_and_delete_volume_type(self):
        mock_service = self.mock_cinder.return_value
        scenario = volume_types.CreateAndDeleteVolumeType(self._get_context())
        description = "rally tests creating types"
        is_public = False
        scenario.run(description=description, is_public=is_public)
        mock_service.create_volume_type.assert_called_once_with(
            description=description, is_public=is_public)
        mock_service.delete_volume_type.assert_called_once_with(
            mock_service.create_volume_type.return_value)

    def test_create_and_delete_encryption_type(self):
        mock_service = self.mock_cinder.return_value
        context = self._get_context()
        context.update({
            "volume_types": [{"id": "fake_id",
                              "name": "fake_name"}],
            "iteration": 1})
        scenario = volume_types.CreateAndDeleteEncryptionType(
            context)

        # case: create_specs is None
        specs = {
            "provider": "prov",
            "cipher": "cip",
            "key_size": "ks",
            "control_location": "cl"
        }
        scenario.run(create_specs=None, provider="prov", cipher="cip",
                     key_size="ks", control_location="cl")
        mock_service.create_encryption_type.assert_called_once_with(
            "fake_id", specs=specs)
        mock_service.delete_encryption_type.assert_called_once_with(
            "fake_id")

        # case: create_specs is not None
        scenario.run(create_specs="fakecreatespecs", provider="prov",
                     cipher="cip", key_size="ks", control_location="cl")
        mock_service.create_encryption_type.assert_called_with(
            "fake_id", specs="fakecreatespecs")
        mock_service.delete_encryption_type.assert_called_with(
            "fake_id")

    def test_create_get_and_delete_encryption_type(self):
        mock_service = self.mock_cinder.return_value
        context = self._get_context()
        context.update({
            "volume_types": [{"id": "fake_id",
                              "name": "fake_name"}],
            "iteration": 1})
        scenario = volume_types.CreateGetAndDeleteEncryptionType(
            context)

        specs = {
            "provider": "prov",
            "cipher": "cip",
            "key_size": "ks",
            "control_location": "cl"
        }
        scenario.run(provider="prov", cipher="cip",
                     key_size="ks", control_location="cl")
        mock_service.create_encryption_type.assert_called_once_with(
            "fake_id", specs=specs)
        mock_service.get_encryption_type.assert_called_once_with(
            "fake_id")
        mock_service.delete_encryption_type.assert_called_once_with(
            "fake_id")

    def test_create_and_list_volume_types(self):
        mock_service = self.mock_cinder.return_value
        fake_type = mock.Mock()
        pool_list = [mock.Mock(), mock.Mock(), fake_type]
        description = "rally tests creating types"
        is_public = False

        scenario = volume_types.CreateAndListVolumeTypes(self._get_context())
        mock_service.create_volume_type.return_value = fake_type
        mock_service.list_types.return_value = pool_list
        scenario.run(description=description, is_public=is_public)

        mock_service.create_volume_type.assert_called_once_with(
            description=description, is_public=is_public)
        mock_service.list_types.assert_called_once_with()

    def test_create_and_list_volume_types_with_fails(self):
        # Negative case: type isn't listed
        mock_service = self.mock_cinder.return_value
        fake_type = mock.Mock()
        pool_list = [mock.Mock(), mock.Mock(), mock.Mock()]
        description = "rally tests creating types"
        is_public = False

        scenario = volume_types.CreateAndListVolumeTypes(self._get_context())
        mock_service.create_volume_type.return_value = fake_type
        mock_service.list_types.return_value = pool_list
        self.assertRaises(rally_exceptions.RallyAssertionError,
                          scenario.run,
                          description=description, is_public=is_public)

        mock_service.create_volume_type.assert_called_once_with(
            description=description, is_public=is_public)
        mock_service.list_types.assert_called_once_with()

    @mock.patch("%s.create_volume_type" % CINDER_V2_PATH)
    @mock.patch("%s.update_volume_type" % CINDER_V2_PATH)
    def test_create_and_update_volume_type(self, mock_update_volume_type,
                                           mock_create_volume_type):
        scenario = volume_types.CreateAndUpdateVolumeType(self._get_context())
        fake_type = mock.MagicMock()
        fake_type.name = "any"
        create_description = "test create"
        update_description = "test update"
        mock_create_volume_type.return_value = fake_type
        scenario.run(description=create_description,
                     update_description=update_description)

        mock_create_volume_type.assert_called_once_with(
            description=create_description,
            is_public=True)
        mock_update_volume_type.assert_called_once_with(
            fake_type, name="any",
            description=update_description,
            is_public=None)

    def test_create_volume_type_and_encryption_type(self):
        mock_service = self.mock_cinder.return_value
        scenario = volume_types.CreateVolumeTypeAndEncryptionType(
            self._get_context())
        description = "rally tests creating types"
        is_public = False
        # case: create_specs is None
        specs = {
            "provider": "prov",
            "cipher": "cip",
            "key_size": "ks",
            "control_location": "cl"
        }
        scenario.run(create_specs=None, provider="prov", cipher="cip",
                     key_size="ks", control_location="cl",
                     description=description, is_public=is_public)
        mock_service.create_volume_type.assert_called_once_with(
            description=description, is_public=is_public)
        mock_service.create_encryption_type.assert_called_once_with(
            mock_service.create_volume_type.return_value, specs=specs)

        # case: create_specs is not None
        scenario.run(create_specs="fakecreatespecs", provider="prov",
                     cipher="cip", key_size="ks", control_location="cl",
                     description=description, is_public=is_public)
        mock_service.create_volume_type.assert_called_with(
            description=description, is_public=is_public)
        mock_service.create_encryption_type.assert_called_with(
            mock_service.create_volume_type.return_value,
            specs="fakecreatespecs")

    def test_create_and_list_encryption_type(self):
        mock_service = self.mock_cinder.return_value
        context = self._get_context()
        context.update({
            "volume_types": [{"id": "fake_id",
                              "name": "fake_name"}],
            "iteration": 1})
        scenario = volume_types.CreateAndListEncryptionType(
            context)

        # case: create_specs is None
        specs = {
            "provider": "prov",
            "cipher": "cip",
            "key_size": "ks",
            "control_location": "cl"
        }
        scenario.run(create_specs=None, provider="prov", cipher="cip",
                     key_size="ks", control_location="cl",
                     search_opts="fakeopts")
        mock_service.create_encryption_type.assert_called_once_with(
            "fake_id", specs=specs)
        mock_service.list_encryption_type.assert_called_once_with(
            "fakeopts")

        # case: create_specs is not None
        scenario.run(create_specs="fakecreatespecs", provider="prov",
                     cipher="cip", key_size="ks", control_location="cl",
                     search_opts="fakeopts")
        mock_service.create_encryption_type.assert_called_with(
            "fake_id", specs="fakecreatespecs")
        mock_service.list_encryption_type.assert_called_with(
            "fakeopts")

    def test_create_and_set_volume_type_keys(self):
        mock_service = self.mock_cinder.return_value
        volume_type_key = {"volume_backend_name": "LVM_iSCSI"}
        description = "rally tests creating types"
        is_public = False
        scenario = volume_types.CreateAndSetVolumeTypeKeys(
            self._get_context())
        scenario.run(volume_type_key, description=description,
                     is_public=is_public)

        mock_service.create_volume_type.assert_called_once_with(
            description=description, is_public=is_public)
        mock_service.set_volume_type_keys.assert_called_once_with(
            mock_service.create_volume_type.return_value,
            metadata=volume_type_key)

    def test_create_and_update_encryption_type(self):
        mock_service = self.mock_cinder.return_value
        context = self._get_context()
        context.update({
            "volume_types": [{"id": "fake_id",
                              "name": "fake_name"}],
            "iteration": 1})
        scenario = volume_types.CreateAndUpdateEncryptionType(
            context)

        create_specs = {
            "provider": "create_prov",
            "cipher": "create_cip",
            "key_size": "create_ks",
            "control_location": "create_cl"
        }
        update_specs = {
            "provider": "update_prov",
            "cipher": "update_cip",
            "key_size": "update_ks",
            "control_location": "update_cl"
        }
        scenario.run(create_provider="create_prov", create_cipher="create_cip",
                     create_key_size="create_ks",
                     create_control_location="create_cl",
                     update_provider="update_prov", update_cipher="update_cip",
                     update_key_size="update_ks",
                     update_control_location="update_cl")
        mock_service.create_encryption_type.assert_called_once_with(
            "fake_id", specs=create_specs)
        mock_service.update_encryption_type.assert_called_once_with(
            "fake_id", specs=update_specs)

    @mock.patch("%s.list_type_access" % CINDER_V2_PATH)
    @mock.patch("%s.add_type_access" % CINDER_V2_PATH)
    @mock.patch("%s.create_volume_type" % CINDER_V2_PATH)
    def test_create_volume_type_add_and_list_type_access(
        self, mock_create_volume_type, mock_add_type_access,
            mock_list_type_access):
        scenario = volume_types.CreateVolumeTypeAddAndListTypeAccess(
            self._get_context())
        fake_type = mock.Mock()
        mock_create_volume_type.return_value = fake_type

        scenario.run(description=None, is_public=False)
        mock_create_volume_type.assert_called_once_with(
            description=None, is_public=False)
        mock_add_type_access.assert_called_once_with(fake_type, project="fake")
        mock_list_type_access.assert_called_once_with(fake_type)
