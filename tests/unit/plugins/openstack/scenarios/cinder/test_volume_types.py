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


class fake_type(object):
    name = "fake"


class CinderVolumeTypesTestCase(test.ScenarioTestCase):

    def _get_context(self):
        context = test.get_test_context()
        context.update({
            "volume_types": [{"id": "fake_id",
                              "name": "fake_name"}]})
        return context

    def test_create_and_delete_volume_type(self):
        scenario = volume_types.CreateAndDeleteVolumeType(self.context)
        scenario._create_volume_type = mock.Mock()
        scenario._delete_volume_type = mock.Mock()
        scenario.run(fakeargs="fakeargs")
        scenario._create_volume_type.assert_called_once_with(
            fakeargs="fakeargs")
        scenario._delete_volume_type.assert_called_once_with(
            scenario._create_volume_type.return_value)

    def test_create_and_delete_encryption_type(self):
        scenario = volume_types.CreateAndDeleteEncryptionType(
            self._get_context())
        scenario._create_encryption_type = mock.Mock()
        scenario._delete_encryption_type = mock.Mock()
        scenario.run(create_specs="fakecreatespecs")
        scenario._create_encryption_type.assert_called_once_with(
            "fake_id", "fakecreatespecs")
        scenario._delete_encryption_type.assert_called_once_with(
            "fake_id")

    def test_create_volume_type_and_encryption_type(self):
        scenario = volume_types.CreateVolumeTypeAndEncryptionType(self.context)
        scenario._create_volume_type = mock.Mock()
        scenario._create_encryption_type = mock.Mock()
        scenario.run(specs="fakespecs", fakeargs="fakeargs")
        scenario._create_volume_type.assert_called_once_with(
            fakeargs="fakeargs")
        scenario._create_encryption_type.assert_called_once_with(
            scenario._create_volume_type.return_value, "fakespecs")

    def test_create_and_list_encryption_type(self):
        scenario = volume_types.CreateAndListEncryptionType(self.context)
        scenario._create_volume_type = mock.Mock()
        scenario._create_encryption_type = mock.Mock()
        scenario._list_encryption_type = mock.Mock()
        scenario.run(specs="fakespecs", search_opts="fakeopts",
                     fakeargs="fakeargs")
        scenario._create_volume_type.assert_called_once_with(
            fakeargs="fakeargs")
        scenario._create_encryption_type.assert_called_once_with(
            scenario._create_volume_type.return_value, "fakespecs")
        scenario._list_encryption_type.assert_called_once_with(
            "fakeopts")

    def test_create_and_set_volume_type_keys(self):
        scenario = volume_types.CreateAndSetVolumeTypeKeys(self.context)

        volume_type = mock.MagicMock()
        volume_type_key = {"volume_backend_name": "LVM_iSCSI"}
        scenario._create_volume_type = mock.MagicMock()
        scenario._set_volume_type_keys = mock.MagicMock()

        scenario._create_volume_type.return_value = volume_type
        scenario.run(volume_type_key, fakeargs="fakeargs")

        scenario._create_volume_type.assert_called_once_with(
            fakeargs="fakeargs")
        scenario._set_volume_type_keys.assert_called_once_with(volume_type,
                                                               volume_type_key)
