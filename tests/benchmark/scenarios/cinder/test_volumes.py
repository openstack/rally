# Copyright 2013 Huawei Technologies Co.,LTD.
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

from rally.benchmark.scenarios.cinder import volumes
from tests import test


CINDER_VOLUMES = "rally.benchmark.scenarios.cinder.volumes.CinderVolumes"


class CinderServersTestCase(test.TestCase):

    @mock.patch(CINDER_VOLUMES + ".sleep_between")
    @mock.patch(CINDER_VOLUMES + "._delete_volume")
    @mock.patch(CINDER_VOLUMES + "._create_volume")
    def _verify_create_and_delete_volume(self, mock_create, mock_delete,
                                         mock_sleep):
        fake_volume = object()
        mock_create.return_value = fake_volume
        volumes.CinderVolumes.create_and_delete_volume(1, 10, 20,
                                                       fakearg="f")

        mock_create.assert_called_once_with(1, fakearg="f")
        mock_sleep.assert_called_once_with(10, 20)
        mock_delete.assert_called_once_with(fake_volume)

    def test_create_and_delete_volume(self):
        self._verify_create_and_delete_volume()
