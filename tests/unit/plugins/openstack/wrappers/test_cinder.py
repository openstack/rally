# Copyright 2014: Mirantis Inc.
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

from rally import exceptions
from rally.plugins.openstack.wrappers import cinder as cinder_wrapper
from tests.unit import test


class CinderWrapperTestBase(object):
    def test_wrap(self):
        client = mock.MagicMock()
        client.version = "dummy"
        self.assertRaises(exceptions.InvalidArgumentsException,
                          cinder_wrapper.wrap, client)


class CinderV1WrapperTestCase(test.TestCase, CinderWrapperTestBase):
    def setUp(self):
        super(CinderV1WrapperTestCase, self).setUp()
        self.client = mock.MagicMock()
        self.client.choose_version.return_value = "1"
        self.wrapped_client = cinder_wrapper.wrap(self.client)

    def test_create_volume(self):
        self.wrapped_client.create_volume(1, display_name="fake_vol")
        self.client.return_value.volumes.create.assert_called_once_with(
            1, display_name="fake_vol")

    def test_update_volume(self):
        self.wrapped_client.update_volume("fake_id", display_name="fake_vol",
                                          display_description="_updated")
        self.client.return_value.volumes.update.assert_called_once_with(
            "fake_id", display_name="fake_vol", display_description="_updated")

    def test_create_snapshot(self):
        self.wrapped_client.create_snapshot("fake_id",
                                            display_name="fake_snap")
        (self.client.return_value.volume_snapshots.create.
         assert_called_once_with("fake_id", display_name="fake_snap"))


class CinderV2WrapperTestCase(test.TestCase, CinderWrapperTestBase):
    def setUp(self):
        super(CinderV2WrapperTestCase, self).setUp()
        self.client = mock.MagicMock()
        self.client.choose_version.return_value = "2"
        self.wrapped_client = cinder_wrapper.wrap(self.client)

    def test_create_volume(self):
        self.wrapped_client.create_volume(1, name="fake_vol")
        self.client.return_value.volumes.create.assert_called_once_with(
            1, name="fake_vol")

    def test_create_snapshot(self):
        self.wrapped_client.create_snapshot("fake_id", name="fake_snap")
        (self.client.return_value.volume_snapshots.create.
         assert_called_once_with("fake_id", name="fake_snap"))

    def test_update_volume(self):
        self.wrapped_client.update_volume("fake_id", name="fake_vol",
                                          description="_updated")
        self.client.return_value.volumes.update.assert_called_once_with(
            "fake_id", name="fake_vol", description="_updated")
