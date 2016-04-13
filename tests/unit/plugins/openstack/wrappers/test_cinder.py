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

import ddt
import mock

from rally import exceptions
from rally.plugins.openstack.wrappers import cinder as cinder_wrapper
from tests.unit import test


@ddt.ddt
class CinderWrapperTestCase(test.ScenarioTestCase):

    @ddt.data(
        {"version": "1", "expected_class": cinder_wrapper.CinderV1Wrapper},
        {"version": "2", "expected_class": cinder_wrapper.CinderV2Wrapper}
    )
    @ddt.unpack
    def test_wrap(self, version, expected_class):
        client = mock.MagicMock()
        client.choose_version.return_value = version
        self.assertIsInstance(cinder_wrapper.wrap(client, mock.Mock()),
                              expected_class)

    @mock.patch("rally.plugins.openstack.wrappers.cinder.LOG")
    def test_wrap_wrong_version(self, mock_log):
        client = mock.MagicMock()
        client.choose_version.return_value = "dummy"
        self.assertRaises(exceptions.InvalidArgumentsException,
                          cinder_wrapper.wrap, client, mock.Mock())
        self.assertTrue(mock_log.warning.mock_called)


class CinderV1WrapperTestCase(test.TestCase):
    def setUp(self):
        super(CinderV1WrapperTestCase, self).setUp()
        self.client = mock.MagicMock()
        self.client.choose_version.return_value = "1"
        self.owner = mock.Mock()
        self.wrapped_client = cinder_wrapper.wrap(self.client, self.owner)

    def test_create_volume(self):
        self.wrapped_client.create_volume(1, display_name="fake_vol")
        self.client.return_value.volumes.create.assert_called_once_with(
            1, display_name=self.owner.generate_random_name.return_value)

    def test_update_volume(self):
        self.wrapped_client.update_volume("fake_id", display_name="fake_vol",
                                          display_description="_updated")
        self.client.return_value.volumes.update.assert_called_once_with(
            "fake_id",
            display_name=self.owner.generate_random_name.return_value,
            display_description="_updated")

    def test_create_snapshot(self):
        self.wrapped_client.create_snapshot("fake_id",
                                            display_name="fake_snap")
        (self.client.return_value.volume_snapshots.create.
         assert_called_once_with(
             "fake_id",
             display_name=self.owner.generate_random_name.return_value))


class CinderV2WrapperTestCase(test.TestCase):
    def setUp(self):
        super(CinderV2WrapperTestCase, self).setUp()
        self.client = mock.MagicMock()
        self.client.choose_version.return_value = "2"
        self.owner = mock.Mock()
        self.wrapped_client = cinder_wrapper.wrap(self.client, self.owner)

    def test_create_volume(self):
        self.wrapped_client.create_volume(1, name="fake_vol")
        self.client.return_value.volumes.create.assert_called_once_with(
            1, name=self.owner.generate_random_name.return_value)

    def test_create_snapshot(self):
        self.wrapped_client.create_snapshot("fake_id", name="fake_snap")
        (self.client.return_value.volume_snapshots.create.
         assert_called_once_with(
             "fake_id",
             name=self.owner.generate_random_name.return_value))

    def test_update_volume(self):
        self.wrapped_client.update_volume("fake_id", name="fake_vol",
                                          description="_updated")
        self.client.return_value.volumes.update.assert_called_once_with(
            "fake_id", name=self.owner.generate_random_name.return_value,
            description="_updated")
