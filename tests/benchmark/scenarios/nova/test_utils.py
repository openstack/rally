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
from rally import test
from tests import fakes


class NovaScenarioTestCase(test.TestCase):

    def setUp(self):
        super(NovaScenarioTestCase, self).setUp()

    def test_generate_random_name(self):
        for length in [8, 16, 32, 64]:
            name = utils.NovaScenario._generate_random_name(length)
            self.assertEqual(len(name), length)
            self.assertTrue(name.isalpha())

    def test_failed_server_status(self):
        server_manager = fakes.FakeFailedServerManager()
        self.assertRaises(rally_exceptions.GetResourceFailure,
                          butils.get_from_manager(),
                          server_manager.create('fails', '1', '2'))

    @mock.patch("rally.benchmark.scenarios.nova.utils.time.sleep")
    @mock.patch("rally.utils")
    @mock.patch("rally.benchmark.utils.osclients")
    @mock.patch("rally.benchmark.utils.resource_is")
    def test_server_helper_methods(self, mock_ris, mock_osclients,
                                   mock_rally_utils, mock_sleep):

        def _is_ready(resource):
            return resource.status == "ACTIVE"

        mock_ris.return_value = _is_ready
        get_from_mgr = butils.get_from_manager()

        fc = fakes.FakeClients()
        mock_osclients.Clients.return_value = fc
        fake_nova = fakes.FakeNovaClient()
        fc.get_nova_client = lambda: fake_nova
        fsm = fakes.FakeServerManager(fake_nova.images)
        fake_server = fsm.create("s1", "i1", 1)
        fsm.create = lambda name, iid, fid: fake_server
        fake_nova.servers = fsm
        fake_image_id = fsm.create_image(fake_server, 'img')
        fake_image = fsm.images.get(fake_image_id)
        fsm.create_image = lambda svr, name: fake_image.id
        temp_keys = ["username", "password", "tenant_name", "uri"]
        users_endpoints = [dict(zip(temp_keys, temp_keys))]
        utils.NovaScenario._clients = butils.\
            create_openstack_clients(users_endpoints, temp_keys)[0]
        utils.utils = mock_rally_utils
        utils.bench_utils.get_from_manager = lambda: get_from_mgr

        utils.NovaScenario._boot_server("s1", "i1", 1)
        utils.NovaScenario._create_image(fake_server)
        utils.NovaScenario._suspend_server(fake_server)
        utils.NovaScenario._delete_server(fake_server)

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
