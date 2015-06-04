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
from oslo_config import cfg
from oslotest import mockpatch

from rally.benchmark import utils as butils
from rally import exceptions as rally_exceptions
from rally.plugins.openstack.scenarios.nova import utils
from tests.unit import fakes
from tests.unit import test

BM_UTILS = "rally.benchmark.utils"
NOVA_UTILS = "rally.plugins.openstack.scenarios.nova.utils"
SCN = "rally.benchmark.scenarios.base"
CONF = cfg.CONF


class NovaScenarioTestCase(test.TestCase):

    def setUp(self):
        super(NovaScenarioTestCase, self).setUp()
        self.server = mock.Mock()
        self.server1 = mock.Mock()
        self.volume = mock.Mock()
        self.floating_ip = mock.Mock()
        self.image = mock.Mock()
        self.keypair = mock.Mock()
        self.res_is = mockpatch.Patch(BM_UTILS + ".resource_is")
        self.get_fm = mockpatch.Patch(BM_UTILS + ".get_from_manager")
        self.wait_for = mockpatch.Patch(NOVA_UTILS + ".bench_utils.wait_for")
        self.wait_for_delete = mockpatch.Patch(NOVA_UTILS +
                                               ".bench_utils.wait_for_delete")
        self.useFixture(self.wait_for_delete)
        self.useFixture(self.wait_for)
        self.useFixture(self.res_is)
        self.useFixture(self.get_fm)
        self.gfm = self.get_fm.mock
        self.useFixture(mockpatch.Patch("time.sleep"))

    def test_failed_server_status(self):
        self.get_fm.cleanUp()
        server_manager = fakes.FakeFailedServerManager()
        self.assertRaises(rally_exceptions.GetResourceFailure,
                          butils.get_from_manager(),
                          server_manager.create("fails", "1", "2"))

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
            if kwargs["is_ready"]:
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

    @mock.patch(NOVA_UTILS + ".NovaScenario.clients")
    def test__list_servers(self, mock_clients):
        servers_list = []
        mock_clients("nova").servers.list.return_value = servers_list
        nova_scenario = utils.NovaScenario()
        return_servers_list = nova_scenario._list_servers(True)
        self.assertEqual(servers_list, return_servers_list)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.list_servers")

    @mock.patch(SCN + ".Scenario._generate_random_name",
                return_value="foo_server_name")
    @mock.patch(NOVA_UTILS + ".NovaScenario.clients")
    def test__boot_server(self, mock_clients, mock_generate_random_name):
        mock_clients("nova").servers.create.return_value = self.server
        nova_scenario = utils.NovaScenario(context={})
        return_server = nova_scenario._boot_server("image_id",
                                                   "flavor_id")
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_boot_poll_interval,
            CONF.benchmark.nova_server_boot_timeout)
        self.res_is.mock.assert_has_calls([mock.call("ACTIVE")])
        self.assertEqual(self.wait_for.mock(), return_server)
        mock_clients("nova").servers.create.assert_called_once_with(
            "foo_server_name", "image_id", "flavor_id")
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.boot_server")

    @mock.patch(SCN + ".Scenario._generate_random_name",
                return_value="foo_server_name")
    @mock.patch(NOVA_UTILS + ".NovaScenario.clients")
    def test__boot_server_with_network(self, mock_clients,
                                       mock_generate_random_name):
        mock_clients("nova").servers.create.return_value = self.server
        networks = [{"id": "foo_id", "external": False},
                    {"id": "bar_id", "external": False}]
        mock_clients("nova").networks.list.return_value = networks
        nova_scenario = utils.NovaScenario(context={
            "iteration": 3,
            "config": {"users": {"tenants": 2}},
            "tenant": {"networks": networks}})
        return_server = nova_scenario._boot_server("image_id",
                                                   "flavor_id",
                                                   auto_assign_nic=True)
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_boot_poll_interval,
            CONF.benchmark.nova_server_boot_timeout)
        self.res_is.mock.assert_has_calls([mock.call("ACTIVE")])
        mock_clients("nova").servers.create.assert_called_once_with(
            "foo_server_name", "image_id", "flavor_id",
            nics=[{"net-id": "bar_id"}])
        self.assertEqual(self.wait_for.mock(), return_server)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.boot_server")

    @mock.patch(NOVA_UTILS + ".NovaScenario.clients")
    def test__boot_server_with_network_exception(self, mock_clients):
        mock_clients("nova").servers.create.return_value = self.server
        nova_scenario = utils.NovaScenario(
            context={"tenant": {"networks": None}})
        self.assertRaises(TypeError, nova_scenario._boot_server,
                          "image_id", "flavor_id",
                          auto_assign_nic=True)

    @mock.patch(SCN + ".Scenario._generate_random_name",
                return_value="foo_server_name")
    @mock.patch(NOVA_UTILS + ".NovaScenario.clients")
    def test__boot_server_with_ssh(self, mock_clients,
                                   mock_generate_random_name):
        mock_clients("nova").servers.create.return_value = self.server
        nova_scenario = utils.NovaScenario(context={
            "user": {"secgroup": {"name": "test"}}}
        )
        return_server = nova_scenario._boot_server("image_id", "flavor_id")
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_boot_poll_interval,
            CONF.benchmark.nova_server_boot_timeout)
        self.res_is.mock.assert_has_calls([mock.call("ACTIVE")])
        self.assertEqual(self.wait_for.mock(), return_server)
        mock_clients("nova").servers.create.assert_called_once_with(
            "foo_server_name", "image_id", "flavor_id",
            security_groups=["test"])
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.boot_server")

    @mock.patch(SCN + ".Scenario._generate_random_name",
                return_value="foo_server_name")
    @mock.patch(NOVA_UTILS + ".NovaScenario.clients")
    def test__boot_server_with_sec_group(self, mock_clients,
                                         mock_generate_random_name):
        mock_clients("nova").servers.create.return_value = self.server
        nova_scenario = utils.NovaScenario(context={
            "user": {"secgroup": {"name": "new"}}}
        )
        return_server = nova_scenario._boot_server(
            "image_id", "flavor_id",
            security_groups=["test"])
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_boot_poll_interval,
            CONF.benchmark.nova_server_boot_timeout)
        self.res_is.mock.assert_has_calls([mock.call("ACTIVE")])
        self.assertEqual(self.wait_for.mock(), return_server)
        mock_clients("nova").servers.create.assert_called_once_with(
            "foo_server_name", "image_id", "flavor_id",
            security_groups=["test", "new"])
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.boot_server")

    @mock.patch(SCN + ".Scenario._generate_random_name",
                return_value="foo_server_name")
    @mock.patch(NOVA_UTILS + ".NovaScenario.clients")
    def test__boot_server_with_similar_sec_group(self, mock_clients,
                                                 mock_generate_random_name):
        mock_clients("nova").servers.create.return_value = self.server
        nova_scenario = utils.NovaScenario(context={
            "user": {"secgroup": {"name": "test1"}}}
        )
        return_server = nova_scenario._boot_server(
            "image_id", "flavor_id",
            security_groups=["test1"])
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_boot_poll_interval,
            CONF.benchmark.nova_server_boot_timeout)
        self.res_is.mock.assert_has_calls([mock.call("ACTIVE")])
        self.assertEqual(self.wait_for.mock(), return_server)
        mock_clients("nova").servers.create.assert_called_once_with(
            "foo_server_name", "image_id", "flavor_id",
            security_groups=["test1"])
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.boot_server")

    def test__suspend_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._suspend_server(self.server)
        self.server.suspend.assert_called_once_with()
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_suspend_poll_interval,
            CONF.benchmark.nova_server_suspend_timeout)
        self.res_is.mock.assert_has_calls([mock.call("SUSPENDED")])
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.suspend_server")

    def test__resume_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._resume_server(self.server)
        self.server.resume.assert_called_once_with()
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_resume_poll_interval,
            CONF.benchmark.nova_server_resume_timeout)
        self.res_is.mock.assert_has_calls([mock.call("ACTIVE")])
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.resume_server")

    def test__pause_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._pause_server(self.server)
        self.server.pause.assert_called_once_with()
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_pause_poll_interval,
            CONF.benchmark.nova_server_pause_timeout)
        self.res_is.mock.assert_has_calls([mock.call("PAUSED")])
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.pause_server")

    def test__unpause_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._unpause_server(self.server)
        self.server.unpause.assert_called_once_with()
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_unpause_poll_interval,
            CONF.benchmark.nova_server_unpause_timeout)
        self.res_is.mock.assert_has_calls([mock.call("ACTIVE")])
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.unpause_server")

    def test__shelve_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._shelve_server(self.server)
        self.server.shelve.assert_called_once_with()
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_shelve_poll_interval,
            CONF.benchmark.nova_server_shelve_timeout)
        self.res_is.mock.assert_has_calls([mock.call("SHELVED_OFFLOADED")])
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.shelve_server")

    def test__unshelve_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._unshelve_server(self.server)
        self.server.unshelve.assert_called_once_with()
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_unshelve_poll_interval,
            CONF.benchmark.nova_server_unshelve_timeout)
        self.res_is.mock.assert_has_calls([mock.call("ACTIVE")])
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.unshelve_server")

    @mock.patch(NOVA_UTILS + ".NovaScenario.clients")
    def test__create_image(self, mock_clients):
        mock_clients("nova").images.get.return_value = self.image
        nova_scenario = utils.NovaScenario()
        return_image = nova_scenario._create_image(self.server)
        self._test_assert_called_once_with(
            self.wait_for.mock, self.image,
            CONF.benchmark.nova_server_image_create_poll_interval,
            CONF.benchmark.nova_server_image_create_timeout)
        self.res_is.mock.assert_has_calls([mock.call("ACTIVE")])
        self.assertEqual(self.wait_for.mock(), return_image)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.create_image")

    def test__default_delete_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._delete_server(self.server)
        self.server.delete.assert_called_once_with()
        self._test_assert_called_once_with(
            self.wait_for_delete.mock, self.server,
            CONF.benchmark.nova_server_delete_poll_interval,
            CONF.benchmark.nova_server_delete_timeout,
            is_ready=None)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.delete_server")

    def test__force_delete_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._delete_server(self.server, force=True)
        self.server.force_delete.assert_called_once_with()
        self._test_assert_called_once_with(
            self.wait_for_delete.mock, self.server,
            CONF.benchmark.nova_server_delete_poll_interval,
            CONF.benchmark.nova_server_delete_timeout,
            is_ready=None)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.force_delete_server")

    def test__reboot_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._reboot_server(self.server)
        self.server.reboot.assert_called_once_with(reboot_type="HARD")
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_reboot_poll_interval,
            CONF.benchmark.nova_server_reboot_timeout)
        self.res_is.mock.assert_has_calls([mock.call("ACTIVE")])
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.reboot_server")

    def test__soft_reboot_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._soft_reboot_server(self.server)
        self.server.reboot.assert_called_once_with(reboot_type="SOFT")
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_reboot_poll_interval,
            CONF.benchmark.nova_server_reboot_timeout)
        self.res_is.mock.assert_has_calls([mock.call("ACTIVE")])
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.soft_reboot_server")

    def test__rebuild_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._rebuild_server(self.server, "img", fakearg="fakearg")
        self.server.rebuild.assert_called_once_with("img", fakearg="fakearg")
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_rebuild_poll_interval,
            CONF.benchmark.nova_server_rebuild_timeout)
        self.res_is.mock.assert_has_calls([mock.call("ACTIVE")])
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.rebuild_server")

    def test__start_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._start_server(self.server)
        self.server.start.assert_called_once_with()
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_start_poll_interval,
            CONF.benchmark.nova_server_start_timeout)
        self.res_is.mock.assert_has_calls([mock.call("ACTIVE")])
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.start_server")

    def test__stop_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._stop_server(self.server)
        self.server.stop.assert_called_once_with()
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_stop_poll_interval,
            CONF.benchmark.nova_server_stop_timeout)
        self.res_is.mock.assert_has_calls([mock.call("SHUTOFF")])
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.stop_server")

    def test__rescue_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._rescue_server(self.server)
        self.server.rescue.assert_called_once_with()
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_rescue_poll_interval,
            CONF.benchmark.nova_server_rescue_timeout)
        self.res_is.mock.assert_has_calls([mock.call("RESCUE")])
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.rescue_server")

    def test__unrescue_server(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._unrescue_server(self.server)
        self.server.unrescue.assert_called_once_with()
        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_unrescue_poll_interval,
            CONF.benchmark.nova_server_unrescue_timeout)
        self.res_is.mock.assert_has_calls([mock.call("ACTIVE")])
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.unrescue_server")

    @mock.patch(NOVA_UTILS + ".NovaScenario.clients")
    def _test_delete_servers(self, mock_clients, force=False):
        servers = [self.server, self.server1]
        nova_scenario = utils.NovaScenario()
        nova_scenario._delete_servers(servers, force=force)
        check_interval = CONF.benchmark.nova_server_delete_poll_interval
        expected = []
        for server in servers:
            expected.append(mock.call(
                server, update_resource=self.gfm(),
                check_interval=check_interval,
                timeout=CONF.benchmark.nova_server_delete_timeout))
            if force:
                server.force_delete.assert_called_once_with()
                self.assertFalse(server.delete.called)
            else:
                server.delete.assert_called_once_with()
                self.assertFalse(server.force_delete.called)

        self.assertEqual(expected, self.wait_for_delete.mock.mock_calls)
        timer_name = "nova.%sdelete_servers" % ("force_" if force else "")
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       timer_name)

    def test__default_delete_servers(self):
        self._test_delete_servers()

    def test__force_delete_servers(self):
        self._test_delete_servers(force=True)

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
                                       "nova.delete_image")

    @mock.patch(NOVA_UTILS + ".NovaScenario.clients")
    def test__boot_servers(self, mock_clients):
        mock_clients("nova").servers.list.return_value = [self.server,
                                                          self.server1]
        nova_scenario = utils.NovaScenario()
        nova_scenario._boot_servers("image", "flavor", 2)
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
        self.res_is.mock.assert_has_calls([mock.call("ACTIVE")])
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.boot_servers")

    def test__associate_floating_ip(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._associate_floating_ip(self.server, self.floating_ip)
        self.server.add_floating_ip.assert_called_once_with(self.floating_ip,
                                                            fixed_address=None)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.associate_floating_ip")

    def test__dissociate_floating_ip(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._dissociate_floating_ip(self.server, self.floating_ip)
        self.server.remove_floating_ip.assert_called_once_with(
            self.floating_ip)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.dissociate_floating_ip")

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

    @mock.patch(NOVA_UTILS + ".NovaScenario.clients")
    def test__list_networks(self, mock_clients):
        network_list = []
        mock_clients("nova").networks.list.return_value = network_list
        nova_scenario = utils.NovaScenario()
        return_network_list = nova_scenario._list_networks()
        self.assertEqual(network_list, return_network_list)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.list_networks")

    def test__resize(self):
        nova_scenario = utils.NovaScenario()
        to_flavor = mock.Mock()
        nova_scenario._resize(self.server, to_flavor)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.resize")

    def test__resize_confirm(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._resize_confirm(self.server)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.resize_confirm")

    def test__resize_revert(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._resize_revert(self.server)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.resize_revert")

    @mock.patch(NOVA_UTILS + ".NovaScenario.clients")
    def test__attach_volume(self, mock_clients):
        mock_clients("nova").volumes.create_server_volume.return_value = None
        nova_scenario = utils.NovaScenario()
        nova_scenario._attach_volume(self.server, self.volume)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.attach_volume")

    @mock.patch(NOVA_UTILS + ".NovaScenario.clients")
    def test__detach_volume(self, mock_clients):
        mock_clients("nova").volumes.delete_server_volume.return_value = None
        nova_scenario = utils.NovaScenario()
        nova_scenario._detach_volume(self.server, self.volume)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.detach_volume")

    @mock.patch(NOVA_UTILS + ".NovaScenario.clients")
    def test__live_migrate_server(self, mock_clients):
        fake_host = mock.MagicMock()
        mock_clients("nova").servers.get(return_value=self.server)
        nova_scenario = utils.NovaScenario(admin_clients=mock_clients)
        nova_scenario._live_migrate(self.server,
                                    fake_host,
                                    block_migration=False,
                                    disk_over_commit=False,
                                    skip_host_check=True)

        self._test_assert_called_once_with(
            self.wait_for.mock, self.server,
            CONF.benchmark.nova_server_live_migrate_poll_interval,
            CONF.benchmark.nova_server_live_migrate_timeout)
        self.res_is.mock.assert_has_calls([mock.call("ACTIVE")])
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.live_migrate")

    @mock.patch(NOVA_UTILS + ".NovaScenario.admin_clients")
    def test__find_host_to_migrate(self, mock_clients):
        fake_server = self.server
        fake_host = {"nova-compute": {"available": True}}
        nova_client = mock.MagicMock()
        mock_clients.return_value = nova_client
        nova_client.servers.get.return_value = fake_server
        nova_client.availability_zones.list.return_value = [
            mock.MagicMock(zoneName="a",
                           hosts={"a1": fake_host, "a2": fake_host,
                                  "a3": fake_host}),
            mock.MagicMock(zoneName="b",
                           hosts={"b1": fake_host, "b2": fake_host,
                                  "b3": fake_host}),
            mock.MagicMock(zoneName="c",
                           hosts={"c1": fake_host,
                                  "c2": fake_host, "c3": fake_host})
        ]
        setattr(fake_server, "OS-EXT-SRV-ATTR:host", "b2")
        setattr(fake_server, "OS-EXT-AZ:availability_zone", "b")
        nova_scenario = utils.NovaScenario(admin_clients=fakes.FakeClients())

        self.assertIn(
            nova_scenario._find_host_to_migrate(fake_server), ["b1", "b3"])

    @mock.patch(NOVA_UTILS + ".NovaScenario.clients")
    def test__migrate_server(self, mock_clients):
        fake_server = self.server
        setattr(fake_server, "OS-EXT-SRV-ATTR:host", "a1")
        mock_clients("nova").servers.get(return_value=fake_server)
        nova_scenario = utils.NovaScenario(admin_clients=mock_clients)
        nova_scenario._migrate(fake_server, skip_host_check=True)

        self._test_assert_called_once_with(
            self.wait_for.mock, fake_server,
            CONF.benchmark.nova_server_migrate_poll_interval,
            CONF.benchmark.nova_server_migrate_timeout)
        self.res_is.mock.assert_has_calls([mock.call("VERIFY_RESIZE")])
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.migrate")

        self.assertRaises(rally_exceptions.MigrateException,
                          nova_scenario._migrate,
                          fake_server, skip_host_check=False)

    def test__create_security_groups(self):
        clients = mock.MagicMock()
        nova_scenario = utils.NovaScenario()
        nova_scenario.clients = clients
        nova_scenario._generate_random_name = mock.MagicMock()

        security_group_count = 5

        sec_groups = nova_scenario._create_security_groups(
            security_group_count)

        self.assertEqual(security_group_count, clients.call_count)
        self.assertEqual(security_group_count, len(sec_groups))
        self.assertEqual(security_group_count,
                         nova_scenario._generate_random_name.call_count)
        self.assertEqual(security_group_count,
                         clients().security_groups.create.call_count)
        self._test_atomic_action_timer(
            nova_scenario.atomic_actions(),
            "nova.create_%s_security_groups" % security_group_count)

    def test__create_rules_for_security_group(self):
        clients = mock.MagicMock()
        nova_scenario = utils.NovaScenario()
        nova_scenario.clients = clients

        fake_secgroups = [fakes.FakeSecurityGroup(None, None, 1, "uuid1"),
                          fakes.FakeSecurityGroup(None, None, 2, "uuid2")]
        rules_per_security_group = 10

        nova_scenario._create_rules_for_security_group(
            fake_secgroups, rules_per_security_group)

        self.assertEqual(len(fake_secgroups) * rules_per_security_group,
                         clients.call_count)
        self.assertEqual(len(fake_secgroups) * rules_per_security_group,
                         clients().security_group_rules.create.call_count)
        self._test_atomic_action_timer(
            nova_scenario.atomic_actions(),
            "nova.create_%s_rules" %
            (rules_per_security_group * len(fake_secgroups)))

    def test__delete_security_groups(self):
        clients = mock.MagicMock()
        nova_scenario = utils.NovaScenario()
        nova_scenario.clients = clients

        fake_secgroups = [fakes.FakeSecurityGroup(None, None, 1, "uuid1"),
                          fakes.FakeSecurityGroup(None, None, 2, "uuid2")]

        nova_scenario._delete_security_groups(fake_secgroups)

        self.assertEqual(len(fake_secgroups), clients.call_count)

        self.assertSequenceEqual(
            map(lambda x: mock.call(x.id), fake_secgroups),
            clients().security_groups.delete.call_args_list)
        self._test_atomic_action_timer(
            nova_scenario.atomic_actions(),
            "nova.delete_%s_security_groups" % len(fake_secgroups))

    def test__list_security_groups(self):
        clients = mock.MagicMock()
        nova_scenario = utils.NovaScenario()
        nova_scenario.clients = clients

        nova_scenario._list_security_groups()

        clients.assert_called_once_with("nova")
        clients().security_groups.list.assert_called_once_with()

        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.list_security_groups")

    @mock.patch(NOVA_UTILS + ".NovaScenario.clients")
    def test__list_keypairs(self, mock_clients):
        keypairs_list = ["foo_keypair"]
        mock_clients("nova").keypairs.list.return_value = keypairs_list
        nova_scenario = utils.NovaScenario()
        return_keypairs_list = nova_scenario._list_keypairs()
        self.assertEqual(keypairs_list, return_keypairs_list)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.list_keypairs")

    @mock.patch(NOVA_UTILS + ".NovaScenario.clients")
    def test__create_keypair(self, mock_clients):
        (mock_clients("nova").keypairs.create.
            return_value.name) = self.keypair
        nova_scenario = utils.NovaScenario()
        return_keypair = nova_scenario._create_keypair()
        self.assertEqual(self.keypair, return_keypair)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.create_keypair")

    @mock.patch(NOVA_UTILS + ".NovaScenario.clients")
    def test__delete_keypair(self, mock_clients):
        nova_scenario = utils.NovaScenario()
        nova_scenario._delete_keypair(self.keypair)
        mock_clients("nova").keypairs.delete.assert_called_once_with(
            self.keypair)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.delete_keypair")

    @mock.patch(NOVA_UTILS + ".NovaScenario.admin_clients")
    def test__list_floating_ips_bulk(self, mock_clients):
        floating_ips_bulk_list = ["foo_floating_ips_bulk"]
        mock_clients("nova").floating_ips_bulk.list.return_value = (
            floating_ips_bulk_list)
        nova_scenario = utils.NovaScenario()
        return_floating_ips_bulk_list = nova_scenario._list_floating_ips_bulk()
        self.assertEqual(floating_ips_bulk_list, return_floating_ips_bulk_list)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.list_floating_ips_bulk")

    @mock.patch(NOVA_UTILS + ".network_wrapper.generate_cidr")
    @mock.patch(NOVA_UTILS + ".NovaScenario.admin_clients")
    def test__create_floating_ips_bulk(self, mock_clients, mock_gencidr):
        fake_cidr = "10.2.0.0/24"
        fake_pool = "test1"
        fake_floating_ips_bulk = mock.MagicMock()
        fake_floating_ips_bulk.ip_range = fake_cidr
        fake_floating_ips_bulk.pool = fake_pool
        mock_clients("nova").floating_ips_bulk.create.return_value = (
            fake_floating_ips_bulk)
        nova_scenario = utils.NovaScenario()
        return_iprange = nova_scenario._create_floating_ips_bulk(fake_cidr)
        mock_gencidr.assert_called_once_with(start_cidr=fake_cidr)
        self.assertEqual(return_iprange, fake_floating_ips_bulk)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.create_floating_ips_bulk")

    @mock.patch(NOVA_UTILS + ".NovaScenario.admin_clients")
    def test__delete_floating_ips_bulk(self, mock_clients):
        fake_cidr = "10.2.0.0/24"
        nova_scenario = utils.NovaScenario()
        nova_scenario._delete_floating_ips_bulk(fake_cidr)
        mock_clients("nova").floating_ips_bulk.delete.assert_called_once_with(
            fake_cidr)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.delete_floating_ips_bulk")

    @mock.patch(NOVA_UTILS + ".NovaScenario.admin_clients")
    def test__list_hypervisors(self, mock_clients):
        nova_scenario = utils.NovaScenario()
        nova_scenario._list_hypervisors(detailed=False)
        mock_clients("nova").hypervisors.list.assert_called_once_with(False)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.list_hypervisors")

    def test__lock_server(self):
        server = mock.Mock()
        nova_scenario = utils.NovaScenario()
        nova_scenario._lock_server(server)
        server.lock.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.lock_server")

    def test__unlock_server(self):
        server = mock.Mock()
        nova_scenario = utils.NovaScenario()
        nova_scenario._unlock_server(server)
        server.unlock.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.unlock_server")
