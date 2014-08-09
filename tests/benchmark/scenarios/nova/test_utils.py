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
from tests.benchmark.scenarios import test_base
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
        self.floating_ip = mock.Mock()
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
        action_duration = test_base.get_atomic_action_timer_value_by_name(
            atomic_actions, name)
        self.assertIsNotNone(action_duration)
        self.assertIsInstance(action_duration, float)

    def test_failed_server_status(self):
        self.get_fm.cleanUp()
        server_manager = fakes.FakeFailedServerManager()
        self.assertRaises(rally_exceptions.GetResourceFailure,
                          butils.get_from_manager(),
                          server_manager.create('fails', '1', '2'))

    def _test_assert_called_once_with(self, mock, resource,
                                      chk_interval, time_out, **kwargs):
        """Method to replace repeatative asserts on resources

        :param mock: The mock to call assert with
        :param resource: The resource used in mock
        :param chk_interval: The interval used for polling the action
        :param time_out: Time out value for action
        :param kwargs: currently used for validating the is_ready attribute,
        can be extended as required
        """

        isready = self.res_is.mock()
        if kwargs:
            if kwargs['is_ready']:
                mock.assert_called_once_with(
                    resource,
                    update_resource=self.gfm(),
                    is_ready=isready,
                    check_interval=chk_interval,
                    timeout=time_out)
            else:
                mock.assert_called_once_with(
                    resource,
                    update_resource=self.gfm(),
                    check_interval=chk_interval,
                    timeout=time_out)

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
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_boot_poll_interval,
            CONF.benchmark.nova_server_boot_timeout)
        self.res_is.mock.assert_has_calls(mock.call('ACTIVE'))
        self.assertEqual(self.wait_for.mock(), return_server)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.boot_server')

    @mock.patch(NOVA_UTILS + '.NovaScenario.clients')
    def test__boot_server_with_network(self, mock_clients):
        mock_clients("nova").servers.create.return_value = self.server
        nova = fakes.FakeNovaClient()
        networks = [
                    nova.networks.create('net-1'),
                    nova.networks.create('net-2')
                   ]
        mock_clients("nova").networks.list.return_value = networks
        nova_scenario = utils.NovaScenario(context={})
        return_server = nova_scenario._boot_server('server_name', 'image_id',
                                                   'flavor_id',
                                                   auto_assign_nic=True)
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_boot_poll_interval,
            CONF.benchmark.nova_server_boot_timeout)
        self.res_is.mock.assert_has_calls(mock.call('ACTIVE'))
        self.assertEqual(self.wait_for.mock(), return_server)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.boot_server')

    @mock.patch(NOVA_UTILS + '.NovaScenario.clients')
    def test__boot_server_with_network_exception(self, mock_clients):
        mock_clients("nova").servers.create.return_value = self.server
        mock_clients("nova").networks.list.return_value = None
        nova_scenario = utils.NovaScenario(context={})
        self.assertRaises(TypeError, nova_scenario._boot_server,
                          'server_name', 'image_id', 'flavor_id',
                          auto_assign_nic=True)

    @mock.patch(NOVA_UTILS + '.NovaScenario.clients')
    def test__boot_server_with_ssh(self, mock_clients):
        mock_clients("nova").servers.create.return_value = self.server
        nova_scenario = utils.NovaScenario(context={"allow_ssh": "test"})
        return_server = nova_scenario._boot_server('server_name', 'image_id',
                                                   'flavor_id')
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_boot_poll_interval,
            CONF.benchmark.nova_server_boot_timeout)
        self.res_is.mock.assert_has_calls(mock.call('ACTIVE'))
        self.assertEqual(self.wait_for.mock(), return_server)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.boot_server')

    @mock.patch(NOVA_UTILS + '.NovaScenario.clients')
    def test__boot_server_with_sec_group(self, mock_clients):
        mock_clients("nova").servers.create.return_value = self.server
        nova_scenario = utils.NovaScenario(context={"allow_ssh": "new"})
        return_server = nova_scenario._boot_server(
            'server_name', 'image_id', 'flavor_id',
            security_groups=['test1'])
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_boot_poll_interval,
            CONF.benchmark.nova_server_boot_timeout)
        self.res_is.mock.assert_has_calls(mock.call('ACTIVE'))
        self.assertEqual(self.wait_for.mock(), return_server)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.boot_server')

    @mock.patch(NOVA_UTILS + '.NovaScenario.clients')
    def test__boot_server_with_similar_sec_group(self, mock_clients):
        mock_clients("nova").servers.create.return_value = self.server
        nova_scenario = utils.NovaScenario(context={"allow_ssh": "test1"})
        return_server = nova_scenario._boot_server(
            'server_name', 'image_id', 'flavor_id',
            security_groups=['test1'])
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_boot_poll_interval,
            CONF.benchmark.nova_server_boot_timeout)
        self.res_is.mock.assert_has_calls(mock.call('ACTIVE'))
        self.assertEqual(self.wait_for.mock(), return_server)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.boot_server')

    def test__suspend_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._suspend_server(self.server)
        self.server.suspend.assert_called_once_with()
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_suspend_poll_interval,
            CONF.benchmark.nova_server_suspend_timeout)
        self.res_is.mock.assert_has_calls(mock.call('SUSPENDED'))
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.suspend_server')

    @mock.patch(NOVA_UTILS + '.NovaScenario.clients')
    def test__create_image(self, mock_clients):
        mock_clients("nova").images.get.return_value = self.image
        nova_scenario = utils.NovaScenario()
        return_image = nova_scenario._create_image(self.server)
        self._test_assert_called_once_with(
            self.wait_for.mock, self.image,
            CONF.benchmark.nova_server_image_create_poll_interval,
            CONF.benchmark.nova_server_image_create_timeout)
        self.res_is.mock.assert_has_calls(mock.call('ACTIVE'))
        self.assertEqual(self.wait_for.mock(), return_image)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.create_image')

    def test__delete_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._delete_server(self.server)
        self.server.delete.assert_called_once_with()
        self._test_assert_called_once_with(
            self.wait_for_delete.mock, self.server,
            CONF.benchmark.nova_server_delete_poll_interval,
            CONF.benchmark.nova_server_delete_timeout,
            is_ready=None)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.delete_server')

    def test__reboot_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._reboot_server(self.server)
        self.server.reboot.assert_called_once_with(reboot_type='HARD')
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_reboot_poll_interval,
            CONF.benchmark.nova_server_reboot_timeout)
        self.res_is.mock.assert_has_calls(mock.call('ACTIVE'))
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.reboot_server')

    def test__soft_reboot_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._soft_reboot_server(self.server)
        self.server.reboot.assert_called_once_with(reboot_type='SOFT')
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_reboot_poll_interval,
            CONF.benchmark.nova_server_reboot_timeout)
        self.res_is.mock.assert_has_calls(mock.call('ACTIVE'))
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.soft_reboot_server')

    def test__start_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._start_server(self.server)
        self.server.start.assert_called_once_with()
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_start_poll_interval,
            CONF.benchmark.nova_server_start_timeout)
        self.res_is.mock.assert_has_calls(mock.call('ACTIVE'))
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.start_server')

    def test__stop_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._stop_server(self.server)
        self.server.stop.assert_called_once_with()
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_stop_poll_interval,
            CONF.benchmark.nova_server_stop_timeout)
        self.res_is.mock.assert_has_calls(mock.call('SHUTOFF'))
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.stop_server')

    def test__rescue_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._rescue_server(self.server)
        self.server.rescue.assert_called_once_with()
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_rescue_poll_interval,
            CONF.benchmark.nova_server_rescue_timeout)
        self.res_is.mock.assert_has_calls(mock.call('RESCUE'))
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.rescue_server')

    def test__unrescue_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._unrescue_server(self.server)
        self.server.unrescue.assert_called_once_with()
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_unrescue_poll_interval,
            CONF.benchmark.nova_server_unrescue_timeout)
        self.res_is.mock.assert_has_calls(mock.call('ACTIVE'))
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.unrescue_server')

    @mock.patch(NOVA_UTILS + '.NovaScenario.clients')
    def test__delete_all_servers(self, mock_clients):
        mock_clients("nova").servers.list.return_value = [self.server,
                                                          self.server1]
        nova_scenario = utils.NovaScenario()
        nova_scenario._delete_all_servers()
        check_interval = CONF.benchmark.nova_server_delete_poll_interval
        expected = [
            mock.call(
                self.server, update_resource=self.gfm(),
                check_interval=check_interval,
                timeout=CONF.benchmark.nova_server_delete_timeout
            ),
            mock.call(
                self.server1, update_resource=self.gfm(),
                check_interval=check_interval,
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
        self._test_assert_called_once_with(
            self.wait_for_delete.mock, self.image,
            CONF.benchmark.nova_server_image_delete_poll_interval,
            CONF.benchmark.nova_server_image_delete_timeout,
            is_ready=None)
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

    @mock.patch(NOVA_UTILS + '.NovaScenario.clients')
    def test__list_floating_ip_pools(self, mock_clients):
        pools_list = []
        mock_clients("nova").floating_ip_pools.list.return_value = pools_list
        nova_scenario = utils.NovaScenario()
        return_pools_list = nova_scenario._list_floating_ip_pools()
        self.assertEqual(pools_list, return_pools_list)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.list_floating_ip_pools')

    @mock.patch(NOVA_UTILS + '.NovaScenario.clients')
    def test__list_floating_ips(self, mock_clients):
        floating_ips_list = []
        mock_clients("nova").floating_ips.list.return_value = floating_ips_list
        nova_scenario = utils.NovaScenario()
        return_floating_ips_list = nova_scenario._list_floating_ips()
        self.assertEqual(floating_ips_list, return_floating_ips_list)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.list_floating_ips')

    @mock.patch(NOVA_UTILS + '.NovaScenario.clients')
    def test__create_floating_ip(self, mock_clients):
        (mock_clients("nova").floating_ips.create.
            return_value) = self.floating_ip
        nova_scenario = utils.NovaScenario()
        return_floating_ip = nova_scenario._create_floating_ip("public")
        self.assertEqual(self.floating_ip, return_floating_ip)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.create_floating_ip')

    @mock.patch(NOVA_UTILS + '.NovaScenario.clients')
    def test__delete_floating_ip(self, mock_clients):
        nova_scenario = utils.NovaScenario()
        nova_scenario._delete_floating_ip(self.floating_ip)
        mock_clients("nova").floating_ips.delete.assert_called_once_with(
            self.floating_ip)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.delete_floating_ip')

    def test__associate_floating_ip(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._associate_floating_ip(self.server, self.floating_ip)
        self.server.add_floating_ip.assert_called_once_with(self.floating_ip,
                                                            fixed_address=None)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.associate_floating_ip')

    def test__dissociate_floating_ip(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._dissociate_floating_ip(self.server, self.floating_ip)
        self.server.remove_floating_ip.assert_called_once_with(
            self.floating_ip)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.dissociate_floating_ip')

    def test__check_ip_address(self):
        nova_scenario = utils.NovaScenario()
        fake_server = fakes.FakeServerManager().create("test_server",
                                                       "image_id_01",
                                                       "flavor_id_01")
        fake_server.addresses = {
            "private": [
                {"version": 4, "addr": "1.2.3.4"},
            ]}
        floating_ip = fakes.FakeFloatingIP()
        floating_ip.ip = "10.20.30.40"

        # Also test function check_ip_address accept a string as attr
        self.assertFalse(
            nova_scenario.check_ip_address(floating_ip.ip)(fake_server))
        self.assertTrue(
            nova_scenario.check_ip_address(floating_ip.ip, must_exist=False)
            (fake_server))

        fake_server.addresses["private"].append(
            {"version": 4, "addr": floating_ip.ip}
        )
        # Also test function check_ip_address accept an object with attr ip
        self.assertTrue(
            nova_scenario.check_ip_address(floating_ip)
            (fake_server))
        self.assertFalse(
            nova_scenario.check_ip_address(floating_ip, must_exist=False)
            (fake_server))

    @mock.patch(NOVA_UTILS + '.NovaScenario.clients')
    def test__list_networks(self, mock_clients):
        network_list = []
        mock_clients("nova").networks.list.return_value = network_list
        nova_scenario = utils.NovaScenario()
        return_network_list = nova_scenario._list_networks()
        self.assertEqual(network_list, return_network_list)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.list_networks')

    def test__resize(self):
        nova_scenario = utils.NovaScenario()
        to_flavor = mock.Mock()
        nova_scenario._resize(self.server, to_flavor)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.resize')

    def test__resize_confirm(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._resize_confirm(self.server)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.resize_confirm')

    def test__resize_revert(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._resize_revert(self.server)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       'nova.resize_revert')
