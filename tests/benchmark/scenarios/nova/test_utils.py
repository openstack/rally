# Copyright 2013: Mirantis Inc.
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

from rally.benchmark.scenarios.nova import utils
from rally.benchmark import utils as butils
from rally import exceptions as rally_exceptions
from rally.openstack.common.fixture import mockpatch
from tests import fakes
from tests import test

BM_UTILS = 'rally.benchmark.utils'
NOVA_UTILS = "rally.benchmark.scenarios.nova.utils"


class NovaScenarioTestCase(test.TestCase):

    def setUp(self):
        super(NovaScenarioTestCase, self).setUp()
        self.server = mock.Mock()
        self.server1 = mock.Mock()
        self.image = mock.Mock()
        self.res_is = mockpatch.Patch(BM_UTILS + ".resource_is")
        self.get_fm = mockpatch.Patch(BM_UTILS + '.get_from_manager')
        self.wait_for = mockpatch.Patch(NOVA_UTILS + ".utils.wait_for")
        self.useFixture(self.wait_for)
        self.useFixture(self.res_is)
        self.useFixture(self.get_fm)
        self.gfm = self.get_fm.mock
        self.useFixture(mockpatch.Patch('time.sleep'))

    def test_generate_random_name(self):
        for length in [8, 16, 32, 64]:
            name = utils.NovaScenario()._generate_random_name(length)
            self.assertEqual(len(name), length)
            self.assertTrue(name.isalpha())

    def test_failed_server_status(self):
        self.get_fm.cleanUp()
        server_manager = fakes.FakeFailedServerManager()
        self.assertRaises(rally_exceptions.GetResourceFailure,
                          butils.get_from_manager(),
                          server_manager.create('fails', '1', '2'))

    @mock.patch("rally.utils")
    @mock.patch(BM_UTILS + ".osclients")
    def test_server_helper_methods(self, mock_osclients, mock_rally_utils):
        def _is_ready(resource):
            return resource.status == "ACTIVE"

        self.res_is.mock.return_value = _is_ready
        get_from_mgr = butils.get_from_manager()

        fc = fakes.FakeClients()
        mock_osclients.Clients.return_value = fc
        fake_nova = fakes.FakeNovaClient()
        fc.get_nova_client = lambda: fake_nova
        fsm = fakes.FakeServerManager(fake_nova.images)
        fake_server = fsm.create("s1", "i1", 1)
        fsm.create = lambda name, iid, fid, **kwargs: fake_server
        fake_nova.servers = fsm
        fake_image_id = fsm.create_image(fake_server, 'img')
        fake_image = fsm.images.get(fake_image_id)
        fsm.create_image = lambda svr, name: fake_image.id
        temp_keys = ["username", "password", "tenant_name", "auth_url"]
        users_endpoints = [dict(zip(temp_keys, temp_keys))]

        tmp_clients = butils.create_openstack_clients(users_endpoints,
                                                      temp_keys)[0]
        novascenario = utils.NovaScenario(clients=tmp_clients)

        utils.utils = mock_rally_utils
        utils.bench_utils.get_from_manager = lambda: get_from_mgr

        novascenario._boot_server("s1", "i1", 1)
        novascenario._create_image(fake_server)
        novascenario._suspend_server(fake_server)
        novascenario._delete_server(fake_server)

        expected = [
            mock.call.wait_for(fake_server, is_ready=_is_ready,
                               update_resource=butils.get_from_manager(),
                               check_interval=3, timeout=600),
            mock.call.wait_for(fake_image, is_ready=_is_ready,
                               update_resource=butils.get_from_manager(),
                               check_interval=3, timeout=600),
            mock.call.wait_for(fake_server, is_ready=_is_ready,
                               update_resource=butils.get_from_manager(),
                               check_interval=3, timeout=600),
            mock.call.wait_for(fake_server, is_ready=butils.is_none,
                               update_resource=butils.get_from_manager(),
                               check_interval=3, timeout=600)
        ]

        self.assertEqual(expected, mock_rally_utils.mock_calls)

    def test_server_reboot(self):
        utils.NovaScenario()._reboot_server(self.server)
        self.server.reboot.assert_called_once_with(reboot_type='SOFT')
        self.wait_for.mock.assert_called_once_with(self.server,
                                                   update_resource=self.gfm(),
                                                   is_ready=self.res_is.mock(),
                                                   check_interval=3,
                                                   timeout=600)
        self.res_is.mock.assert_has_calls(mock.call('ACTIVE'))

    def test_server_start(self):
        utils.NovaScenario()._start_server(self.server)
        self.server.start.assert_called_once_with()
        self.wait_for.mock.assert_called_once_with(self.server,
                                                   update_resource=self.gfm(),
                                                   is_ready=self.res_is.mock(),
                                                   check_interval=2,
                                                   timeout=600)
        self.res_is.mock.assert_has_calls(mock.call('ACTIVE'))

    def test_server_stop(self):
        utils.NovaScenario()._stop_server(self.server)
        self.server.stop.assert_called_once_with()
        self.wait_for.mock.assert_called_once_with(self.server,
                                                   update_resource=self.gfm(),
                                                   is_ready=self.res_is.mock(),
                                                   check_interval=2,
                                                   timeout=600)
        self.res_is.mock.assert_has_calls(mock.call('SHUTOFF'))

    def test_server_rescue(self):
        utils.NovaScenario()._rescue_server(self.server)
        self.server.rescue.assert_called_once_with()
        self.wait_for.mock.assert_called_once_with(self.server,
                                                   update_resource=self.gfm(),
                                                   is_ready=self.res_is.mock(),
                                                   check_interval=3,
                                                   timeout=600)
        self.res_is.mock.assert_has_calls(mock.call('RESCUE'))

    def test_server_unrescue(self):
        utils.NovaScenario()._unrescue_server(self.server)
        self.server.unrescue.assert_called_once_with()
        self.wait_for.mock.assert_called_once_with(self.server,
                                                   update_resource=self.gfm(),
                                                   is_ready=self.res_is.mock(),
                                                   check_interval=3,
                                                   timeout=600)
        self.res_is.mock.assert_has_calls(mock.call('ACTIVE'))

    @mock.patch(BM_UTILS + ".is_none")
    @mock.patch(NOVA_UTILS + '.NovaScenario.clients')
    def test_delete_all_servers(self, mock_clients, mock_isnone):
        mock_clients("nova").servers.list.return_value = [self.server,
                                                          self.server1]
        utils.NovaScenario()._delete_all_servers()
        expected = [
            mock.call(self.server, is_ready=mock_isnone,
                      update_resource=self.gfm(),
                      check_interval=3, timeout=600),
            mock.call(self.server1, is_ready=mock_isnone,
                      update_resource=self.gfm(),
                      check_interval=3, timeout=600)
        ]
        self.assertEqual(expected, self.wait_for.mock.mock_calls)

    def test_delete_image(self):
        utils.NovaScenario()._delete_image(self.image)
        self.image.delete.assert_called_once_with()
        self.wait_for.mock.assert_called_once_with(self.image,
                                                   update_resource=self.gfm(),
                                                   is_ready=self.res_is.mock(),
                                                   check_interval=3,
                                                   timeout=600)
        self.res_is.mock.assert_has_calls(mock.call('DELETED'))

    @mock.patch(NOVA_UTILS + '.NovaScenario.clients')
    def test_boot_servers(self, mock_clients):
        mock_clients("nova").servers.list.return_value = [self.server,
                                                          self.server1]
        utils.NovaScenario()._boot_servers('prefix', 'image', 'flavor', 2)
        expected = [
            mock.call(self.server, is_ready=self.res_is.mock(),
                      update_resource=self.gfm(),
                      check_interval=3, timeout=600),
            mock.call(self.server1, is_ready=self.res_is.mock(),
                      update_resource=self.gfm(),
                      check_interval=3, timeout=600)
        ]
        self.assertEqual(expected, self.wait_for.mock.mock_calls)
        self.res_is.mock.assert_has_calls(mock.call('ACTIVE'))
