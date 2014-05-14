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
from oslo.config import cfg
from oslotest import mockpatch

from rally.benchmark.scenarios.nova import utils
from rally.benchmark import utils as butils
from rally import exceptions as rally_exceptions
from tests.benchmark.scenarios import test_utils
from tests import fakes
from tests import test

BM_UTILS = 'rally.benchmark.utils'
NOVA_UTILS = "rally.benchmark.scenarios.nova.utils"
CONF = cfg.CONF


class NovaScenarioTestCase(test.TestCase):

    def setUp(self):
        super(NovaScenarioTestCase, self).setUp()
        self.server = mock.Mock()
        self.server1 = mock.Mock()
        self.image = mock.Mock()
        self.res_is = mockpatch.Patch(BM_UTILS + ".resource_is")
        self.get_fm = mockpatch.Patch(BM_UTILS + '.get_from_manager')
        self.wait_for = mockpatch.Patch(NOVA_UTILS + ".bench_utils.wait_for")
        self.wait_for_delete = mockpatch.Patch(NOVA_UTILS +
                                               ".bench_utils.wait_for_delete")
        self.useFixture(self.wait_for_delete)
        self.useFixture(self.wait_for)
        self.useFixture(self.res_is)
        self.useFixture(self.get_fm)
        self.gfm = self.get_fm.mock
        self.useFixture(mockpatch.Patch('time.sleep'))

    def _test_atomic_action_timer(self, atomic_actions, name):
        action_duration = test_utils.get_atomic_action_timer_value_by_name(
            atomic_actions, name)
        self.assertIsNotNone(action_duration)
        self.assertIsInstance(action_duration, float)

    def test_failed_server_status(self):
        self.get_fm.cleanUp()
        server_manager = fakes.FakeFailedServerManager()
        self.assertRaises(rally_exceptions.GetResourceFailure,
                          butils.get_from_manager(),
                          server_manager.create('fails', '1', '2'))

    @mock.patch(NOVA_UTILS + '.NovaScenario.clients')
    def test__list_servers(self, mock_clients):
        servers_list = []
        mock_clients("nova").servers.list.return_value = servers_list
        nova_scenario = utils.NovaScenario()
        return_servers_list = nova_scenario._list_servers(True)
        self.assertEqual(servers_list, return_servers_list)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.list_servers')

    @mock.patch(NOVA_UTILS + '.NovaScenario.clients')
    def test__boot_server(self, mock_clients):
        mock_clients("nova").servers.create.return_value = self.server
        nova_scenario = utils.NovaScenario(context={})
        return_server = nova_scenario._boot_server('server_name', 'image_id',
                                                   'flavor_id')
        self.wait_for.mock.assert_called_once_with(
            self.server,
            update_resource=self.gfm(),
            is_ready=self.res_is.mock(),
            check_interval=CONF.benchmark.nova_server_boot_poll_interval,
            timeout=CONF.benchmark.nova_server_boot_timeout
        )
        self.res_is.mock.assert_has_calls(mock.call('ACTIVE'))
        self.assertEqual(self.wait_for.mock(), return_server)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.boot_server')

    def test__suspend_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._suspend_server(self.server)
        self.server.suspend.assert_called_once_with()
        self.wait_for.mock.assert_called_once_with(
            self.server,
            update_resource=self.gfm(),
            is_ready=self.res_is.mock(),
            check_interval=CONF.benchmark.nova_server_suspend_poll_interval,
            timeout=CONF.benchmark.nova_server_suspend_timeout
        )
        self.res_is.mock.assert_has_calls(mock.call('SUSPENDED'))
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.suspend_server')

    @mock.patch(NOVA_UTILS + '.NovaScenario.clients')
    def test__create_image(self, mock_clients):
        mock_clients("nova").images.get.return_value = self.image
        nova_scenario = utils.NovaScenario()
        return_image = nova_scenario._create_image(self.server)
        self.wait_for.mock.assert_called_once_with(
            self.image,
            update_resource=self.gfm(),
            is_ready=self.res_is.mock(),
            check_interval=
                CONF.benchmark.nova_server_image_create_poll_interval,
            timeout=CONF.benchmark.nova_server_image_create_timeout
        )
        self.res_is.mock.assert_has_calls(mock.call('ACTIVE'))
        self.assertEqual(self.wait_for.mock(), return_image)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.create_image')

    def test__delete_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._delete_server(self.server)
        self.server.delete.assert_called_once_with()
        self.wait_for_delete.mock.assert_called_once_with(
            self.server,
            update_resource=self.gfm(),
            check_interval=CONF.benchmark.nova_server_delete_poll_interval,
            timeout=CONF.benchmark.nova_server_delete_timeout
        )
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.delete_server')

    def test__reboot_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._reboot_server(self.server)
        self.server.reboot.assert_called_once_with(reboot_type='SOFT')
        self.wait_for.mock.assert_called_once_with(
            self.server,
            update_resource=self.gfm(),
            is_ready=self.res_is.mock(),
            check_interval=CONF.benchmark.nova_server_reboot_poll_interval,
            timeout=CONF.benchmark.nova_server_reboot_timeout
        )
        self.res_is.mock.assert_has_calls(mock.call('ACTIVE'))
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.reboot_server')

    def test__start_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._start_server(self.server)
        self.server.start.assert_called_once_with()
        self.wait_for.mock.assert_called_once_with(
            self.server,
            update_resource=self.gfm(),
            is_ready=self.res_is.mock(),
            check_interval=CONF.benchmark.nova_server_start_poll_interval,
            timeout=CONF.benchmark.nova_server_start_timeout
        )
        self.res_is.mock.assert_has_calls(mock.call('ACTIVE'))
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.start_server')

    def test__stop_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._stop_server(self.server)
        self.server.stop.assert_called_once_with()
        self.wait_for.mock.assert_called_once_with(
            self.server,
            update_resource=self.gfm(),
            is_ready=self.res_is.mock(),
            check_interval=CONF.benchmark.nova_server_stop_poll_interval,
            timeout=CONF.benchmark.nova_server_stop_timeout
        )
        self.res_is.mock.assert_has_calls(mock.call('SHUTOFF'))
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.stop_server')

    def test__rescue_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._rescue_server(self.server)
        self.server.rescue.assert_called_once_with()
        self.wait_for.mock.assert_called_once_with(
            self.server,
            update_resource=self.gfm(),
            is_ready=self.res_is.mock(),
            check_interval=CONF.benchmark.nova_server_rescue_poll_interval,
            timeout=CONF.benchmark.nova_server_rescue_timeout
        )
        self.res_is.mock.assert_has_calls(mock.call('RESCUE'))
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.rescue_server')

    def test__unrescue_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._unrescue_server(self.server)
        self.server.unrescue.assert_called_once_with()
        self.wait_for.mock.assert_called_once_with(
            self.server,
            update_resource=self.gfm(),
            is_ready=self.res_is.mock(),
            check_interval=CONF.benchmark.nova_server_unrescue_poll_interval,
            timeout=CONF.benchmark.nova_server_unrescue_timeout
        )
        self.res_is.mock.assert_has_calls(mock.call('ACTIVE'))
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.unrescue_server')

    @mock.patch(NOVA_UTILS + '.NovaScenario.clients')
    def test__delete_all_servers(self, mock_clients):
        mock_clients("nova").servers.list.return_value = [self.server,
                                                          self.server1]
        nova_scenario = utils.NovaScenario()
        nova_scenario._delete_all_servers()
        expected = [
            mock.call(
                self.server, update_resource=self.gfm(),
                check_interval=
                    CONF.benchmark.nova_server_delete_poll_interval,
                timeout=CONF.benchmark.nova_server_delete_timeout
            ),
            mock.call(
                self.server1, update_resource=self.gfm(),
                check_interval=
                    CONF.benchmark.nova_server_delete_poll_interval,
                timeout=CONF.benchmark.nova_server_delete_timeout
            )
        ]
        self.assertEqual(expected, self.wait_for_delete.mock.mock_calls)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.delete_all_servers')

    def test__delete_image(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._delete_image(self.image)
        self.image.delete.assert_called_once_with()
        self.wait_for_delete.mock.assert_called_once_with(
            self.image, update_resource=self.gfm(),
            check_interval=
                CONF.benchmark.nova_server_image_delete_poll_interval,
            timeout=CONF.benchmark.nova_server_image_delete_timeout
        )
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.delete_image')

    @mock.patch(NOVA_UTILS + '.NovaScenario.clients')
    def test__boot_servers(self, mock_clients):
        mock_clients("nova").servers.list.return_value = [self.server,
                                                          self.server1]
        nova_scenario = utils.NovaScenario()
        nova_scenario._boot_servers('prefix', 'image', 'flavor', 2)
        expected = [
            mock.call(
                self.server, is_ready=self.res_is.mock(),
                update_resource=self.gfm(),
                check_interval=CONF.benchmark.nova_server_boot_poll_interval,
                timeout=CONF.benchmark.nova_server_boot_timeout
            ),
            mock.call(
                self.server1, is_ready=self.res_is.mock(),
                update_resource=self.gfm(),
                check_interval=CONF.benchmark.nova_server_boot_poll_interval,
                timeout=CONF.benchmark.nova_server_boot_timeout
            )
        ]
        self.assertEqual(expected, self.wait_for.mock.mock_calls)
        self.res_is.mock.assert_has_calls(mock.call('ACTIVE'))
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.boot_servers')
