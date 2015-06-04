# Copyright (C) 2014 Yahoo! Inc. All Rights Reserved.
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

from rally.benchmark.scenarios import base
from rally.plugins.openstack.scenarios.authenticate import authenticate
from tests.unit import test


AUTHENTICATE_MODULE = (
    "rally.plugins.openstack.scenarios.authenticate.authenticate")


class AuthenticateTestCase(test.TestCase):

    @mock.patch(AUTHENTICATE_MODULE + ".Authenticate.clients")
    def test_keystone(self, mock_clients):
        scenario = authenticate.Authenticate()
        scenario.keystone()
        mock_clients.assert_called_once_with("keystone")

    @mock.patch(AUTHENTICATE_MODULE + ".Authenticate.clients")
    def test_validate_glance(self, mock_clients):
        scenario = authenticate.Authenticate()
        mock_clients.return_value.images.list = mock.MagicMock()
        image_name = "__intentionally_non_existent_image___"
        with base.AtomicAction(scenario, "authenticate.validate_glance"):
            scenario.validate_glance(5)
        mock_clients.return_value.images.list.assert_called_with(
            name=image_name)
        self.assertEqual(mock_clients.return_value.images.list.call_count, 5)

    @mock.patch(AUTHENTICATE_MODULE + ".Authenticate.clients")
    def test_validate_nova(self, mock_clients):
        scenario = authenticate.Authenticate()
        mock_clients.return_value.flavors.list = mock.MagicMock()
        with base.AtomicAction(scenario, "authenticate.validate_nova"):
            scenario.validate_nova(5)
        self.assertEqual(mock_clients.return_value.flavors.list.call_count, 5)

    @mock.patch(AUTHENTICATE_MODULE + ".Authenticate.clients")
    def test_validate_cinder(self, mock_clients):
        scenario = authenticate.Authenticate()
        mock_clients.return_value.volume_types.list = mock.MagicMock()
        with base.AtomicAction(scenario, "authenticate.validate_cinder"):
            scenario.validate_cinder(5)
        self.assertEqual(mock_clients.return_value.volume_types.
                         list.call_count, 5)

    @mock.patch(AUTHENTICATE_MODULE + ".Authenticate.clients")
    def test_validate_neutron(self, mock_clients):
        scenario = authenticate.Authenticate()
        mock_clients.return_value.get_auth_info = mock.MagicMock()
        with base.AtomicAction(scenario, "authenticate.validate_neutron"):
            scenario.validate_neutron(5)
        self.assertEqual(mock_clients.return_value.get_auth_info.call_count, 5)

    @mock.patch(AUTHENTICATE_MODULE + ".Authenticate.clients")
    def test_validate_heat(self, mock_clients):
        scenario = authenticate.Authenticate()
        mock_clients.return_value.stacks.list = mock.MagicMock()
        with base.AtomicAction(scenario, "authenticate.validate_heat"):
            scenario.validate_heat(5)
        mock_clients.return_value.stacks.list.assert_called_with(limit=0)
        self.assertEqual(mock_clients.return_value.stacks.list.call_count, 5)
