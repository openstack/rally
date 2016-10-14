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

    def test_create_and_delete_volume_type(self):
        scenario = volume_types.CreateAndDeleteVolumeType(self.context)
        scenario._create_volume_type = mock.Mock()
        scenario._delete_volume_type = mock.Mock()
        scenario.run(fakeargs="fakeargs")
        scenario._create_volume_type.assert_called_once_with(
            fakeargs="fakeargs")
        scenario._delete_volume_type.assert_called_once_with(
            scenario._create_volume_type.return_value)

    def test_create_volume_type_and_encryption_type(self):
        scenario = volume_types.CreateVolumeTypeAndEncryptionType(self.context)
        scenario._create_volume_type = mock.Mock()
        scenario._create_encryption_type = mock.Mock()
        scenario.run(specs="fakespecs", fakeargs="fakeargs")
        scenario._create_volume_type.assert_called_once_with(
            fakeargs="fakeargs")
        scenario._create_encryption_type.assert_called_once_with(
            scenario._create_volume_type.return_value, "fakespecs")
