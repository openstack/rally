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

    def test_create_and_list_volume(self):
        scenario = volumes.CinderVolumes()
        scenario._create_volume = mock.MagicMock()
        scenario._list_volumes = mock.MagicMock()
        scenario.create_and_list_volume(1, True, fakearg="f")
        scenario._create_volume.assert_called_once_with(1, fakearg="f")
        scenario._list_volumes.assert_called_once_with(True)

    def test_create_and_delete_volume(self):
        fake_volume = mock.MagicMock()

        scenario = volumes.CinderVolumes()
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)
        scenario.sleep_between = mock.MagicMock()
        scenario._delete_volume = mock.MagicMock()

        scenario.create_and_delete_volume(1, 10, 20, fakearg="f")

        scenario._create_volume.assert_called_once_with(1, fakearg="f")
        scenario.sleep_between.assert_called_once_with(10, 20)
        scenario._delete_volume.assert_called_once_with(fake_volume)

    def test_create_volume(self):
        fake_volume = mock.MagicMock()
        scenario = volumes.CinderVolumes()
        scenario._create_volume = mock.MagicMock(return_value=fake_volume)

        scenario.create_volume(1, fakearg="f")
        scenario._create_volume.assert_called_once_with(1, fakearg="f")

    def test_create_and_delete_snapshot(self):
        fake_snapshot = mock.MagicMock()
        scenario = volumes.CinderVolumes(
            context={"user": {"tenant_id": "fake"},
                     "volumes": [{"tenant_id": "fake", "volume_id": "uuid"}]})
        scenario._create_snapshot = mock.MagicMock(return_value=fake_snapshot)
        scenario.sleep_between = mock.MagicMock()
        scenario._delete_snapshot = mock.MagicMock()

        scenario.create_and_delete_snapshot(False, 10, 20, fakearg="f")

        scenario._create_snapshot.assert_called_once_with("uuid", force=False,
                                                          fakearg="f")
        scenario.sleep_between.assert_called_once_with(10, 20)
        scenario._delete_snapshot.assert_called_once_with(fake_snapshot)
