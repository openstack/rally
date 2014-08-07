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

from rally.benchmark.scenarios.authenticate import authenticate
from rally.benchmark.scenarios import base as scenario_base
from tests import fakes
from tests import test


class AuthenticateTestCase(test.TestCase):

    @mock.patch("rally.osclients")
    def test_keystone(self, mock_osclients):
        fc = fakes.FakeClients()
        mock_osclients.Clients.return_value = fc

        scenario = authenticate.Authenticate(admin_clients=mock_osclients,
                                             clients=mock_osclients)

        scenario.keystone()
        self.assertEqual(scenario._clients.keystone.call_count, 1)

    @mock.patch("rally.osclients")
    @mock.patch("rally.osclients")
    def test_validate_glance(self, mock_admin_clients, mock_users_clients):
        images_list = [mock.Mock(), mock.Mock()]
        fc = fakes.FakeClients()
        mock_admin_clients.Clients.return_value = fc
        mock_users_clients.Clients.return_value = fc
        scenario = authenticate.Authenticate(admin_clients=mock_admin_clients,
                                             clients=mock_users_clients)
        scenario._clients.glance.images.list = mock.MagicMock(
                                                return_value=images_list)
        image_name = "__intentionally_non_existent_image___"
        with scenario_base.AtomicAction(scenario,
                                        "authenticate.validate_glance"):
            scenario.validate_glance(5)
        scenario._clients.glance().images.list.assert_called_with(
                name=image_name)
        self.assertEqual(scenario._clients.glance().images.list.call_count, 5)

    @mock.patch("rally.osclients")
    @mock.patch("rally.osclients")
    def test_validate_nova(self, mock_admin_clients, mock_users_clients):
        flavors_list = [mock.Mock(), mock.Mock()]
        fc = fakes.FakeClients()
        mock_admin_clients.clients.return_value = fc
        mock_users_clients.clients.return_value = fc
        scenario = authenticate.Authenticate(admin_clients=mock_admin_clients,
                                             clients=mock_users_clients)
        scenario._clients.nova.flavors.list = mock.MagicMock(
                                                return_value=flavors_list)
        with scenario_base.AtomicAction(scenario,
                                        "authenticate.validate_nova"):
            scenario.validate_nova(5)
        self.assertEqual(scenario._clients.nova().flavors.list.call_count, 5)

    @mock.patch("rally.osclients")
    @mock.patch("rally.osclients")
    def test_validate_cinder(self, mock_admin_clients, mock_users_clients):
        volume_types_list = [mock.Mock(), mock.Mock()]
        fc = fakes.FakeClients()
        mock_admin_clients.clients.return_value = fc
        mock_users_clients.clients.return_value = fc
        scenario = authenticate.Authenticate(admin_clients=mock_admin_clients,
                                             clients=mock_users_clients)
        scenario._clients.cinder.volume_types.list = mock.MagicMock(
                                                return_value=volume_types_list)
        with scenario_base.AtomicAction(scenario,
                                        "authenticate.validate_cinder"):
            scenario.validate_cinder(5)
        self.assertEqual(scenario._clients.cinder().volume_types.
                         list.call_count, 5)

    @mock.patch("rally.osclients")
    @mock.patch("rally.osclients")
    def test_validate_neutron(self, mock_admin_clients, mock_users_clients):
        fc = fakes.FakeClients()
        mock_admin_clients.clients.return_value = fc
        mock_users_clients.clients.return_value = fc
        scenario = authenticate.Authenticate(admin_clients=mock_admin_clients,
                                             clients=mock_users_clients)
        scenario._clients.neutron.get_auth_info = mock.MagicMock()
        with scenario_base.AtomicAction(scenario,
                                        "authenticate.validate_neutron"):
            scenario.validate_neutron(5)
        self.assertEqual(scenario._clients.neutron().get_auth_info.call_count,
                         5)

    @mock.patch("rally.osclients")
    @mock.patch("rally.osclients")
    def test_validate_heat(self, mock_admin_clients, mock_users_clients):
        stacks_list = [mock.Mock(), mock.Mock()]
        fc = fakes.FakeClients()
        mock_admin_clients.clients.return_value = fc
        mock_users_clients.clients.return_value = fc
        scenario = authenticate.Authenticate(admin_clients=mock_admin_clients,
                                             clients=mock_users_clients)
        scenario._clients.heat.stacks.list = mock.MagicMock(
                                                return_value=stacks_list)
        with scenario_base.AtomicAction(scenario,
                                        "authenticate.validate_heat"):
            scenario.validate_heat(5)
        scenario._clients.heat().stacks.list.assert_called_with(limit=0)
        self.assertEqual(scenario._clients.heat().stacks.list.call_count, 5)
