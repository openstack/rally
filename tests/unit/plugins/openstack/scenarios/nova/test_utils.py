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

import ddt
import mock
from oslo_config import cfg

from rally import exceptions as rally_exceptions
from rally.plugins.openstack.scenarios.nova import utils
from tests.unit import fakes
from tests.unit import test

BM_UTILS = "rally.task.utils"
NOVA_UTILS = "rally.plugins.openstack.scenarios.nova.utils"
CONF = cfg.CONF


@ddt.ddt
class NovaScenarioTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(NovaScenarioTestCase, self).setUp()
        self.server = mock.Mock()
        self.server1 = mock.Mock()
        self.volume = mock.Mock()
        self.floating_ip = mock.Mock()
        self.image = mock.Mock()
        self.context["iteration"] = 3
        self.context["config"] = {"users": {"tenants": 2}}

    def _context_with_networks(self, networks):
        retval = {"tenant": {"networks": networks}}
        retval.update(self.context)
        return retval

    def _context_with_secgroup(self, secgroup):
        retval = {"user": {"secgroup": secgroup,
                           "credential": mock.MagicMock()}}
        retval.update(self.context)
        return retval

    def test__list_servers(self):
        servers_list = []
        self.clients("nova").servers.list.return_value = servers_list
        nova_scenario = utils.NovaScenario(self.context)
        return_servers_list = nova_scenario._list_servers(True)
        self.assertEqual(servers_list, return_servers_list)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.list_servers")

    def test__pick_random_nic(self):
        context = {"tenant": {"networks": [{"id": "net_id_1"},
                                           {"id": "net_id_2"}]},
                   "iteration": 0}
        nova_scenario = utils.NovaScenario(context=context)
        nic1 = nova_scenario._pick_random_nic()
        self.assertEqual(nic1, [{"net-id": "net_id_1"}])

        context["iteration"] = 1
        nova_scenario = utils.NovaScenario(context=context)
        nic2 = nova_scenario._pick_random_nic()
        # balance to net 2
        self.assertEqual(nic2, [{"net-id": "net_id_2"}])

        context["iteration"] = 2
        nova_scenario = utils.NovaScenario(context=context)
        nic3 = nova_scenario._pick_random_nic()
        # balance again, get net 1
        self.assertEqual(nic3, [{"net-id": "net_id_1"}])

    @ddt.data(
        {},
        {"kwargs": {"auto_assign_nic": True}},
        {"kwargs": {"auto_assign_nic": True, "nics": [{"net-id": "baz_id"}]}},
        {"context": {"user": {"secgroup": {"name": "test"}}}},
        {"context": {"user": {"secgroup": {"name": "new8"}}},
         "kwargs": {"security_groups": ["test8"]}},
        {"context": {"user": {"secgroup": {"name": "test1"}}},
         "kwargs": {"security_groups": ["test1"]}},
    )
    @ddt.unpack
    def test__boot_server(self, context=None, kwargs=None):
        self.clients("nova").servers.create.return_value = self.server

        if context is None:
            context = self.context
        context.setdefault("user", {}).setdefault("credential",
                                                  mock.MagicMock())
        context.setdefault("config", {})

        nova_scenario = utils.NovaScenario(context=context)
        nova_scenario.generate_random_name = mock.Mock()
        nova_scenario._pick_random_nic = mock.Mock()
        if kwargs is None:
            kwargs = {}
        kwargs["fakearg"] = "fakearg"
        return_server = nova_scenario._boot_server("image_id", "flavor_id",
                                                   **kwargs)
        self.mock_wait_for_status.mock.assert_called_once_with(
            self.server,
            ready_statuses=["ACTIVE"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.nova_server_boot_poll_interval,
            timeout=CONF.benchmark.nova_server_boot_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self.assertEqual(self.mock_wait_for_status.mock.return_value,
                         return_server)

        expected_kwargs = {"fakearg": "fakearg"}
        if "nics" in kwargs:
            expected_kwargs["nics"] = kwargs["nics"]
        elif "auto_assign_nic" in kwargs:
            expected_kwargs["nics"] = (nova_scenario._pick_random_nic.
                                       return_value)

        expected_secgroups = set()
        if "security_groups" in kwargs:
            expected_secgroups.update(kwargs["security_groups"])
        if "secgroup" in context["user"]:
            expected_secgroups.add(context["user"]["secgroup"]["name"])
        if expected_secgroups:
            expected_kwargs["security_groups"] = list(expected_secgroups)

        self.clients("nova").servers.create.assert_called_once_with(
            nova_scenario.generate_random_name.return_value,
            "image_id", "flavor_id", **expected_kwargs)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.boot_server")

    def test__boot_server_with_network_exception(self):
        self.clients("nova").servers.create.return_value = self.server
        nova_scenario = utils.NovaScenario(
            context=self._context_with_networks(None))
        self.assertRaises(TypeError, nova_scenario._boot_server,
                          "image_id", "flavor_id",
                          auto_assign_nic=True)

    def test__suspend_server(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._suspend_server(self.server)
        self.server.suspend.assert_called_once_with()
        self.mock_wait_for_status.mock.assert_called_once_with(
            self.server,
            ready_statuses=["SUSPENDED"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.nova_server_suspend_poll_interval,
            timeout=CONF.benchmark.nova_server_suspend_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.suspend_server")

    def test__resume_server(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._resume_server(self.server)
        self.server.resume.assert_called_once_with()
        self.mock_wait_for_status.mock.assert_called_once_with(
            self.server,
            ready_statuses=["ACTIVE"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.nova_server_resume_poll_interval,
            timeout=CONF.benchmark.nova_server_resume_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.resume_server")

    def test__pause_server(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._pause_server(self.server)
        self.server.pause.assert_called_once_with()
        self.mock_wait_for_status.mock.assert_called_once_with(
            self.server,
            ready_statuses=["PAUSED"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.nova_server_pause_poll_interval,
            timeout=CONF.benchmark.nova_server_pause_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.pause_server")

    def test__unpause_server(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._unpause_server(self.server)
        self.server.unpause.assert_called_once_with()
        self.mock_wait_for_status.mock.assert_called_once_with(
            self.server,
            ready_statuses=["ACTIVE"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.nova_server_unpause_poll_interval,
            timeout=CONF.benchmark.nova_server_unpause_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.unpause_server")

    def test__shelve_server(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._shelve_server(self.server)
        self.server.shelve.assert_called_once_with()
        self.mock_wait_for_status.mock.assert_called_once_with(
            self.server,
            ready_statuses=["SHELVED_OFFLOADED"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.nova_server_shelve_poll_interval,
            timeout=CONF.benchmark.nova_server_shelve_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.shelve_server")

    def test__unshelve_server(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._unshelve_server(self.server)
        self.server.unshelve.assert_called_once_with()
        self.mock_wait_for_status.mock.assert_called_once_with(
            self.server,
            ready_statuses=["ACTIVE"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.nova_server_unshelve_poll_interval,
            timeout=CONF.benchmark.nova_server_unshelve_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.unshelve_server")

    def test__create_image(self):
        self.clients("nova").images.get.return_value = self.image
        nova_scenario = utils.NovaScenario(context=self.context)
        return_image = nova_scenario._create_image(self.server)
        self.mock_wait_for_status.mock.assert_called_once_with(
            self.image,
            ready_statuses=["ACTIVE"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.
            nova_server_image_create_poll_interval,
            timeout=CONF.benchmark.nova_server_image_create_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self.assertEqual(self.mock_wait_for_status.mock.return_value,
                         return_image)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.create_image")

    def test__default_delete_server(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._delete_server(self.server)
        self.server.delete.assert_called_once_with()
        self.mock_wait_for_status.mock.assert_called_once_with(
            self.server,
            ready_statuses=["deleted"],
            check_deletion=True,
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.nova_server_delete_poll_interval,
            timeout=CONF.benchmark.nova_server_delete_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.delete_server")

    def test__force_delete_server(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._delete_server(self.server, force=True)
        self.server.force_delete.assert_called_once_with()
        self.mock_wait_for_status.mock.assert_called_once_with(
            self.server,
            ready_statuses=["deleted"],
            check_deletion=True,
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.nova_server_delete_poll_interval,
            timeout=CONF.benchmark.nova_server_delete_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.force_delete_server")

    def test__reboot_server(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._reboot_server(self.server)
        self.server.reboot.assert_called_once_with(reboot_type="HARD")
        self.mock_wait_for_status.mock.assert_called_once_with(
            self.server,
            ready_statuses=["ACTIVE"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.nova_server_reboot_poll_interval,
            timeout=CONF.benchmark.nova_server_reboot_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.reboot_server")

    def test__soft_reboot_server(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._soft_reboot_server(self.server)
        self.server.reboot.assert_called_once_with(reboot_type="SOFT")
        self.mock_wait_for_status.mock.assert_called_once_with(
            self.server,
            ready_statuses=["ACTIVE"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.nova_server_reboot_poll_interval,
            timeout=CONF.benchmark.nova_server_reboot_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.soft_reboot_server")

    def test__rebuild_server(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._rebuild_server(self.server, "img", fakearg="fakearg")
        self.server.rebuild.assert_called_once_with("img", fakearg="fakearg")
        self.mock_wait_for_status.mock.assert_called_once_with(
            self.server,
            ready_statuses=["ACTIVE"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.nova_server_rebuild_poll_interval,
            timeout=CONF.benchmark.nova_server_rebuild_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.rebuild_server")

    def test__start_server(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._start_server(self.server)
        self.server.start.assert_called_once_with()
        self.mock_wait_for_status.mock.assert_called_once_with(
            self.server,
            ready_statuses=["ACTIVE"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.nova_server_start_poll_interval,
            timeout=CONF.benchmark.nova_server_start_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.start_server")

    def test__stop_server(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._stop_server(self.server)
        self.server.stop.assert_called_once_with()
        self.mock_wait_for_status.mock.assert_called_once_with(
            self.server,
            ready_statuses=["SHUTOFF"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.nova_server_stop_poll_interval,
            timeout=CONF.benchmark.nova_server_stop_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.stop_server")

    def test__rescue_server(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._rescue_server(self.server)
        self.server.rescue.assert_called_once_with()
        self.mock_wait_for_status.mock.assert_called_once_with(
            self.server,
            ready_statuses=["RESCUE"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.nova_server_rescue_poll_interval,
            timeout=CONF.benchmark.nova_server_rescue_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.rescue_server")

    def test__unrescue_server(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._unrescue_server(self.server)
        self.server.unrescue.assert_called_once_with()
        self.mock_wait_for_status.mock.assert_called_once_with(
            self.server,
            ready_statuses=["ACTIVE"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.nova_server_unrescue_poll_interval,
            timeout=CONF.benchmark.nova_server_unrescue_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.unrescue_server")

    def _test_delete_servers(self, force=False):
        servers = [self.server, self.server1]
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._delete_servers(servers, force=force)
        check_interval = CONF.benchmark.nova_server_delete_poll_interval
        expected = []
        for server in servers:
            expected.append(mock.call(
                server,
                ready_statuses=["deleted"],
                check_deletion=True,
                update_resource=self.mock_get_from_manager.mock.return_value,
                check_interval=check_interval,
                timeout=CONF.benchmark.nova_server_delete_timeout))
            if force:
                server.force_delete.assert_called_once_with()
                self.assertFalse(server.delete.called)
            else:
                server.delete.assert_called_once_with()
                self.assertFalse(server.force_delete.called)

        self.mock_wait_for_status.mock.assert_has_calls(expected)
        timer_name = "nova.%sdelete_servers" % ("force_" if force else "")
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       timer_name)

    def test__default_delete_servers(self):
        self._test_delete_servers()

    def test__force_delete_servers(self):
        self._test_delete_servers(force=True)

    @mock.patch("rally.plugins.openstack.wrappers.glance.wrap")
    def test__delete_image(self, mock_wrap):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._clients = mock.Mock()
        nova_scenario._delete_image(self.image)
        self.clients("glance").images.delete.assert_called_once_with(
            self.image.id)
        self.mock_wait_for_status.mock.assert_called_once_with(
            self.image,
            ready_statuses=["deleted", "pending_delete"],
            check_deletion=True,
            update_resource=mock_wrap.return_value.get_image,
            check_interval=CONF.benchmark.
            nova_server_image_delete_poll_interval,
            timeout=CONF.benchmark.nova_server_image_delete_timeout)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.delete_image")

    @ddt.data(
        {"requests": 1},
        {"requests": 25},
        {"requests": 2, "instances_amount": 100, "auto_assign_nic": True,
         "fakearg": "fake"},
        {"auto_assign_nic": True, "nics": [{"net-id": "foo"}]},
        {"auto_assign_nic": False, "nics": [{"net-id": "foo"}]})
    @ddt.unpack
    def test__boot_servers(self, image_id="image", flavor_id="flavor",
                           requests=1, instances_amount=1,
                           auto_assign_nic=False, **kwargs):
        servers = [mock.Mock() for i in range(instances_amount)]
        self.clients("nova").servers.list.return_value = servers
        scenario = utils.NovaScenario(context=self.context)
        scenario.generate_random_name = mock.Mock()
        scenario._pick_random_nic = mock.Mock()

        scenario._boot_servers(image_id, flavor_id, requests,
                               instances_amount=instances_amount,
                               auto_assign_nic=auto_assign_nic,
                               **kwargs)

        expected_kwargs = dict(kwargs)
        if auto_assign_nic and "nics" not in kwargs:
            expected_kwargs["nics"] = scenario._pick_random_nic.return_value

        create_calls = [
            mock.call(
                "%s_%d" % (scenario.generate_random_name.return_value, i),
                image_id, flavor_id,
                min_count=instances_amount, max_count=instances_amount,
                **expected_kwargs)
            for i in range(requests)]
        self.clients("nova").servers.create.assert_has_calls(create_calls)

        wait_for_status_calls = [
            mock.call(
                servers[i],
                ready_statuses=["ACTIVE"],
                update_resource=self.mock_get_from_manager.mock.return_value,
                check_interval=CONF.benchmark.nova_server_boot_poll_interval,
                timeout=CONF.benchmark.nova_server_boot_timeout)
            for i in range(instances_amount)]
        self.mock_wait_for_status.mock.assert_has_calls(wait_for_status_calls)

        self.mock_get_from_manager.mock.assert_has_calls(
            [mock.call() for i in range(instances_amount)])
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "nova.boot_servers")

    def test__show_server(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._show_server(self.server)
        self.clients("nova").servers.get.assert_called_once_with(
            self.server
        )
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.show_server")

    def test__get_console_server(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._get_server_console_output(self.server)
        self.clients(
            "nova").servers.get_console_output.assert_called_once_with(
            self.server, length=None)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.get_console_output_server")

    def test__associate_floating_ip(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._associate_floating_ip(self.server, self.floating_ip)
        self.server.add_floating_ip.assert_called_once_with(self.floating_ip,
                                                            fixed_address=None)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.associate_floating_ip")

    def test__associate_floating_ip_with_no_atomic_action(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._associate_floating_ip(self.server, self.floating_ip,
                                             atomic_action=False)
        self.server.add_floating_ip.assert_called_once_with(self.floating_ip,
                                                            fixed_address=None)

    def test__dissociate_floating_ip(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._dissociate_floating_ip(self.server, self.floating_ip)
        self.server.remove_floating_ip.assert_called_once_with(
            self.floating_ip)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.dissociate_floating_ip")

    def test__dissociate_floating_ip_with_no_atomic_action(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._dissociate_floating_ip(self.server, self.floating_ip,
                                              atomic_action=False)
        self.server.remove_floating_ip.assert_called_once_with(
            self.floating_ip)

    def test__check_ip_address(self):
        nova_scenario = utils.NovaScenario(context=self.context)
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

    def test__list_networks(self):
        network_list = []
        self.clients("nova").networks.list.return_value = network_list
        nova_scenario = utils.NovaScenario(context=self.context)
        return_network_list = nova_scenario._list_networks()
        self.assertEqual(network_list, return_network_list)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.list_networks")

    def test__resize(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        to_flavor = mock.Mock()
        nova_scenario._resize(self.server, to_flavor)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.resize")

    def test__resize_confirm(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._resize_confirm(self.server)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.resize_confirm")

    @ddt.data({},
              {"status": "SHUTOFF"})
    @ddt.unpack
    def test__resize_revert(self, status=None):
        nova_scenario = utils.NovaScenario(context=self.context)
        if status is None:
            nova_scenario._resize_revert(self.server)
            status = "ACTIVE"
        else:
            nova_scenario._resize_revert(self.server, status=status)
        self.mock_wait_for_status.mock.assert_called_once_with(
            self.server,
            ready_statuses=[status],
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.
            nova_server_resize_revert_poll_interval,
            timeout=CONF.benchmark.nova_server_resize_revert_timeout)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.resize_revert")

    def test__attach_volume(self):
        expect_attach = mock.MagicMock()
        device = None
        (self.clients("nova").volumes.create_server_volume
         .return_value) = expect_attach
        nova_scenario = utils.NovaScenario(context=self.context)
        attach = nova_scenario._attach_volume(self.server, self.volume, device)
        (self.clients("nova").volumes.create_server_volume
         .assert_called_once_with(self.server.id, self.volume.id, device))
        self.assertEqual(expect_attach, attach)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.attach_volume")

    def test__detach_volume(self):
        attach = mock.MagicMock(id="attach_id")
        self.clients("nova").volumes.delete_server_volume.return_value = None
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._detach_volume(self.server, self.volume, attach)
        (self.clients("nova").volumes.delete_server_volume
         .assert_called_once_with(self.server.id, attach.id))
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.detach_volume")

    def test__detach_volume_no_attach(self):
        self.clients("nova").volumes.delete_server_volume.return_value = None
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._detach_volume(self.server, self.volume, None)
        (self.clients("nova").volumes.delete_server_volume
         .assert_called_once_with(self.server.id, self.volume.id))
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.detach_volume")

    def test__live_migrate_server(self):
        fake_host = mock.MagicMock()
        self.admin_clients("nova").servers.get(return_value=self.server)
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._live_migrate(self.server,
                                    fake_host,
                                    block_migration=False,
                                    disk_over_commit=False,
                                    skip_host_check=True)

        self.mock_wait_for_status.mock.assert_called_once_with(
            self.server,
            ready_statuses=["ACTIVE"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.
            nova_server_live_migrate_poll_interval,
            timeout=CONF.benchmark.nova_server_live_migrate_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.live_migrate")

    def test__find_host_to_migrate(self):
        fake_server = self.server
        fake_host = {"nova-compute": {"available": True}}
        fake_host_compute_off = {"nova-compute": {"available": False}}
        fake_host_no_compute = {"nova-conductor": {"available": True}}
        self.admin_clients("nova").servers.get.return_value = fake_server
        self.admin_clients("nova").availability_zones.list.return_value = [
            mock.MagicMock(zoneName="a",
                           hosts={"a1": fake_host, "a2": fake_host,
                                  "a3": fake_host}),
            mock.MagicMock(zoneName="b",
                           hosts={"b1": fake_host, "b2": fake_host,
                                  "b3": fake_host, "b4": fake_host_compute_off,
                                  "b5": fake_host_no_compute}),
            mock.MagicMock(zoneName="c",
                           hosts={"c1": fake_host,
                                  "c2": fake_host, "c3": fake_host})
        ]
        setattr(fake_server, "OS-EXT-SRV-ATTR:host", "b2")
        setattr(fake_server, "OS-EXT-AZ:availability_zone", "b")
        nova_scenario = utils.NovaScenario(context=self.context)

        self.assertIn(
            nova_scenario._find_host_to_migrate(fake_server), ["b1", "b3"])

    def test__migrate_server(self):
        fake_server = self.server
        setattr(fake_server, "OS-EXT-SRV-ATTR:host", "a1")
        self.clients("nova").servers.get(return_value=fake_server)
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._migrate(fake_server, skip_host_check=True)

        self.mock_wait_for_status.mock.assert_called_once_with(
            fake_server,
            ready_statuses=["VERIFY_RESIZE"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.nova_server_migrate_poll_interval,
            timeout=CONF.benchmark.nova_server_migrate_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.migrate")

        self.assertRaises(rally_exceptions.MigrateException,
                          nova_scenario._migrate,
                          fake_server, skip_host_check=False)

    def test__create_security_groups(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario.generate_random_name = mock.MagicMock()

        security_group_count = 5

        sec_groups = nova_scenario._create_security_groups(
            security_group_count)

        self.assertEqual(security_group_count, len(sec_groups))
        self.assertEqual(security_group_count,
                         nova_scenario.generate_random_name.call_count)
        self.assertEqual(
            security_group_count,
            self.clients("nova").security_groups.create.call_count)
        self._test_atomic_action_timer(
            nova_scenario.atomic_actions(),
            "nova.create_%s_security_groups" % security_group_count)

    def test__create_rules_for_security_group(self):
        nova_scenario = utils.NovaScenario(context=self.context)

        fake_secgroups = [fakes.FakeSecurityGroup(None, None, 1, "uuid1"),
                          fakes.FakeSecurityGroup(None, None, 2, "uuid2")]
        rules_per_security_group = 10

        nova_scenario._create_rules_for_security_group(
            fake_secgroups, rules_per_security_group)

        self.assertEqual(
            len(fake_secgroups) * rules_per_security_group,
            self.clients("nova").security_group_rules.create.call_count)
        self._test_atomic_action_timer(
            nova_scenario.atomic_actions(),
            "nova.create_%s_rules" %
            (rules_per_security_group * len(fake_secgroups)))

    def test__update_security_groups(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        fake_secgroups = [fakes.FakeSecurityGroup(None, None, 1, "uuid1"),
                          fakes.FakeSecurityGroup(None, None, 2, "uuid2")]
        nova_scenario._update_security_groups(fake_secgroups)
        self.assertEqual(
            len(fake_secgroups),
            self.clients("nova").security_groups.update.call_count)
        self._test_atomic_action_timer(
            nova_scenario.atomic_actions(),
            "nova.update_%s_security_groups" % len(fake_secgroups))

    def test__delete_security_groups(self):
        nova_scenario = utils.NovaScenario(context=self.context)

        fake_secgroups = [fakes.FakeSecurityGroup(None, None, 1, "uuid1"),
                          fakes.FakeSecurityGroup(None, None, 2, "uuid2")]

        nova_scenario._delete_security_groups(fake_secgroups)

        self.assertSequenceEqual(
            map(lambda x: mock.call(x.id), fake_secgroups),
            self.clients("nova").security_groups.delete.call_args_list)
        self._test_atomic_action_timer(
            nova_scenario.atomic_actions(),
            "nova.delete_%s_security_groups" % len(fake_secgroups))

    def test__list_security_groups(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._list_security_groups()

        self.clients("nova").security_groups.list.assert_called_once_with()

        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.list_security_groups")

    def test__add_server_secgroups(self):
        server = mock.Mock()
        fake_secgroups = [fakes.FakeSecurityGroup(None, None, 1, "uuid1")]

        nova_scenario = utils.NovaScenario()
        security_group = fake_secgroups[0]
        result = nova_scenario._add_server_secgroups(server,
                                                     security_group.name)
        self.assertEqual(
            self.clients("nova").servers.add_security_group.return_value,
            result)
        (self.clients("nova").servers.add_security_group.
            assert_called_once_with(server, security_group.name))
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.add_server_secgroups")

    def test__list_keypairs(self):
        nova_scenario = utils.NovaScenario()
        result = nova_scenario._list_keypairs()
        self.assertEqual(self.clients("nova").keypairs.list.return_value,
                         result)
        self.clients("nova").keypairs.list.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.list_keypairs")

    def test__create_keypair(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario.generate_random_name = mock.Mock(
            return_value="rally_nova_keypair_fake")
        result = nova_scenario._create_keypair(fakeargs="fakeargs")
        self.assertEqual(
            self.clients("nova").keypairs.create.return_value.name,
            result)
        self.clients("nova").keypairs.create.assert_called_once_with(
            "rally_nova_keypair_fake", fakeargs="fakeargs")
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.create_keypair")

    def test__delete_keypair(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._delete_keypair("fake_keypair")
        self.clients("nova").keypairs.delete.assert_called_once_with(
            "fake_keypair")
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.delete_keypair")

    def test__list_floating_ips_bulk(self):
        floating_ips_bulk_list = ["foo_floating_ips_bulk"]
        self.admin_clients("nova").floating_ips_bulk.list.return_value = (
            floating_ips_bulk_list)
        nova_scenario = utils.NovaScenario(context=self.context)
        return_floating_ips_bulk_list = nova_scenario._list_floating_ips_bulk()
        self.assertEqual(floating_ips_bulk_list, return_floating_ips_bulk_list)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.list_floating_ips_bulk")

    @mock.patch(NOVA_UTILS + ".network_wrapper.generate_cidr")
    def test__create_floating_ips_bulk(self, mock_generate_cidr):
        fake_cidr = "10.2.0.0/24"
        fake_pool = "test1"
        fake_floating_ips_bulk = mock.MagicMock()
        fake_floating_ips_bulk.ip_range = fake_cidr
        fake_floating_ips_bulk.pool = fake_pool
        self.admin_clients("nova").floating_ips_bulk.create.return_value = (
            fake_floating_ips_bulk)
        nova_scenario = utils.NovaScenario(context=self.context)
        return_iprange = nova_scenario._create_floating_ips_bulk(fake_cidr)
        mock_generate_cidr.assert_called_once_with(start_cidr=fake_cidr)
        self.assertEqual(return_iprange, fake_floating_ips_bulk)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.create_floating_ips_bulk")

    def test__delete_floating_ips_bulk(self):
        fake_cidr = "10.2.0.0/24"
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._delete_floating_ips_bulk(fake_cidr)
        self.admin_clients(
            "nova").floating_ips_bulk.delete.assert_called_once_with(fake_cidr)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.delete_floating_ips_bulk")

    def test__list_hypervisors(self):
        nova_scenario = utils.NovaScenario()
        result = nova_scenario._list_hypervisors(detailed=False)
        self.assertEqual(
            self.admin_clients("nova").hypervisors.list.return_value, result)
        self.admin_clients("nova").hypervisors.list.assert_called_once_with(
            False)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.list_hypervisors")

    def test__statistics_hypervisors(self):
        nova_scenario = utils.NovaScenario()
        result = nova_scenario._statistics_hypervisors()
        self.assertEqual(
            self.admin_clients("nova").hypervisors.statistics.return_value,
            result)
        (self.admin_clients("nova").hypervisors.statistics.
            assert_called_once_with())
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.statistics_hypervisors")

    def test__get_hypervisor(self):
        hypervisor = mock.Mock()
        nova_scenario = utils.NovaScenario()
        result = nova_scenario._get_hypervisor(hypervisor)
        self.assertEqual(
            self.admin_clients("nova").hypervisors.get.return_value,
            result)
        self.admin_clients("nova").hypervisors.get.assert_called_once_with(
            hypervisor)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.get_hypervisor")

    def test__search_hypervisors(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._search_hypervisors("fake_hostname", servers=False)

        self.admin_clients("nova").hypervisors.search.assert_called_once_with(
            "fake_hostname", servers=False)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.search_hypervisors")

    def test__get_host(self):
        nova_scenario = utils.NovaScenario()
        result = nova_scenario._get_host("host_name")
        self.assertEqual(
            self.admin_clients("nova").hosts.get.return_value,
            result)
        self.admin_clients("nova").hosts.get.assert_called_once_with(
            "host_name")
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.get_host")

    def test__list_images(self):
        nova_scenario = utils.NovaScenario()
        result = nova_scenario._list_images(detailed=False, fakearg="fakearg")
        self.assertEqual(self.clients("nova").images.list.return_value,
                         result)
        self.clients("nova").images.list.assert_called_once_with(
            False, fakearg="fakearg")
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.list_images")

    def test__lock_server(self):
        server = mock.Mock()
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._lock_server(server)
        server.lock.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.lock_server")

    def test__unlock_server(self):
        server = mock.Mock()
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario._unlock_server(server)
        server.unlock.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.unlock_server")

    def test__delete_network(self):
        nova_scenario = utils.NovaScenario()
        result = nova_scenario._delete_network("fake_net_id")
        self.assertEqual(
            self.admin_clients("nova").networks.delete.return_value,
            result)
        self.admin_clients("nova").networks.delete.assert_called_once_with(
            "fake_net_id")
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.delete_network")

    @mock.patch(NOVA_UTILS + ".network_wrapper.generate_cidr")
    def test__create_network(self, mock_generate_cidr):
        nova_scenario = utils.NovaScenario()
        nova_scenario.generate_random_name = mock.Mock(
            return_value="rally_novanet_fake")

        result = nova_scenario._create_network("fake_start_cidr",
                                               fakearg="fakearg")

        mock_generate_cidr.assert_called_once_with(
            start_cidr="fake_start_cidr")

        self.assertEqual(
            self.admin_clients("nova").networks.create.return_value,
            result)
        self.admin_clients("nova").networks.create.assert_called_once_with(
            label="rally_novanet_fake", cidr=mock_generate_cidr.return_value,
            fakearg="fakearg")
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.create_network")

    def test__list_flavors(self):
        nova_scenario = utils.NovaScenario()
        result = nova_scenario._list_flavors(detailed=True, fakearg="fakearg")
        self.assertEqual(self.clients("nova").flavors.list.return_value,
                         result)
        self.clients("nova").flavors.list.assert_called_once_with(
            True, fakearg="fakearg")
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.list_flavors")

    def test__set_flavor_keys(self):
        flavor = mock.MagicMock()
        nova_scenario = utils.NovaScenario()
        extra_specs = {"fakeargs": "foo"}
        flavor.set_keys = mock.MagicMock()

        result = nova_scenario._set_flavor_keys(flavor, extra_specs)
        self.assertEqual(flavor.set_keys.return_value, result)
        flavor.set_keys.assert_called_once_with(extra_specs)

        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.set_flavor_keys")

    @ddt.data({},
              {"hypervisor": "foo_hypervisor"})
    @ddt.unpack
    def test__list_agents(self, hypervisor=None):
        nova_scenario = utils.NovaScenario()
        result = nova_scenario._list_agents(hypervisor)
        self.assertEqual(
            self.admin_clients("nova").agents.list.return_value, result)
        self.admin_clients("nova").agents.list.assert_called_once_with(
            hypervisor)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.list_agents")

    def test__list_aggregates(self):
        nova_scenario = utils.NovaScenario()
        result = nova_scenario._list_aggregates()
        self.assertEqual(
            self.admin_clients("nova").aggregates.list.return_value, result)
        self.admin_clients("nova").aggregates.list.assert_called_once_with()
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.list_aggregates")

    def test__list_availability_zones(self):
        nova_scenario = utils.NovaScenario()
        result = nova_scenario._list_availability_zones(detailed=True)
        self.assertEqual(
            self.admin_clients("nova").availability_zones.list.return_value,
            result)
        avail_zones_client = self.admin_clients("nova").availability_zones
        avail_zones_client.list.assert_called_once_with(True)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.list_availbility_zones")

    @ddt.data({},
              {"zone": "foo_zone"})
    @ddt.unpack
    def test__list_hosts(self, zone=None):
        nova_scenario = utils.NovaScenario()
        result = nova_scenario._list_hosts(zone)
        self.assertEqual(self.admin_clients("nova").hosts.list.return_value,
                         result)
        self.admin_clients("nova").hosts.list.assert_called_once_with(zone)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.list_hosts")

    @ddt.data({},
              {"host": "foo_host"},
              {"binary": "foo_binary"},
              {"host": "foo_host", "binary": "foo_binary"})
    @ddt.unpack
    def test__list_services(self, host=None, binary=None):
        nova_scenario = utils.NovaScenario()
        result = nova_scenario._list_services(host=host, binary=binary)
        self.assertEqual(self.admin_clients("nova").services.list.return_value,
                         result)
        self.admin_clients("nova").services.list.assert_called_once_with(
            host, binary)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.list_services")

    def test__list_flavor_access(self):
        nova_scenario = utils.NovaScenario()
        result = nova_scenario._list_flavor_access("foo_id")
        self.assertEqual(
            self.admin_clients("nova").flavor_access.list.return_value,
            result)
        self.admin_clients("nova").flavor_access.list.assert_called_once_with(
            flavor="foo_id")
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.list_flavor_access")

    def test__add_tenant_access(self):
        tenant = mock.Mock()
        flavor = mock.Mock()
        nova_scenario = utils.NovaScenario()
        admin_clients = self.admin_clients("nova")
        result = nova_scenario._add_tenant_access(flavor.id, tenant.id)
        self.assertEqual(
            admin_clients.flavor_access.add_tenant_access.return_value,
            result)
        admin_clients.flavor_access.add_tenant_access.assert_called_once_with(
            flavor.id, tenant.id)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.add_tenant_access")

    def test__create_flavor(self):
        nova_scenario = utils.NovaScenario()
        random_name = "random_name"
        nova_scenario.generate_random_name = mock.Mock(
            return_value=random_name)
        result = nova_scenario._create_flavor(500, 1, 1,
                                              fakearg="fakearg")
        self.assertEqual(
            self.admin_clients("nova").flavors.create.return_value,
            result)
        self.admin_clients("nova").flavors.create.assert_called_once_with(
            random_name, 500, 1, 1, fakearg="fakearg")
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.create_flavor")

    def test__get_flavor(self):
        nova_scenario = utils.NovaScenario()
        result = nova_scenario._get_flavor("foo_flavor_id")
        self.assertEqual(
            self.admin_clients("nova").flavors.get.return_value,
            result)
        self.admin_clients("nova").flavors.get.assert_called_once_with(
            "foo_flavor_id")
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.get_flavor")

    def test__delete_flavor(self):
        nova_scenario = utils.NovaScenario()
        result = nova_scenario._delete_flavor("foo_flavor_id")
        self.assertEqual(
            self.admin_clients("nova").flavors.delete.return_value,
            result)
        self.admin_clients("nova").flavors.delete.assert_called_once_with(
            "foo_flavor_id")
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.delete_flavor")

    def test__update_server(self):
        server = mock.Mock()
        nova_scenario = utils.NovaScenario()
        nova_scenario.generate_random_name = mock.Mock(
            return_value="new_name")
        server.update = mock.Mock()

        result = nova_scenario._update_server(server)
        self.assertEqual(result, server.update.return_value)
        nova_scenario.generate_random_name.assert_called_once_with()
        server.update.assert_called_once_with(name="new_name")

        nova_scenario.generate_random_name.reset_mock()
        server.update.reset_mock()

        result = nova_scenario._update_server(server,
                                              description="desp")
        self.assertEqual(result, server.update.return_value)
        nova_scenario.generate_random_name.assert_called_once_with()
        server.update.assert_called_once_with(name="new_name",
                                              description="desp")

        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.update_server")

    def test_create_aggregate(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        random_name = "random_name"
        nova_scenario.generate_random_name = mock.Mock(
            return_value=random_name)
        result = nova_scenario._create_aggregate("nova")
        self.assertEqual(
            self.admin_clients("nova").aggregates.create.return_value,
            result)
        self.admin_clients("nova").aggregates.create.assert_called_once_with(
            random_name, "nova")
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.create_aggregate")

    def test_delete_aggregate(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        result = nova_scenario._delete_aggregate("fake_aggregate")
        self.assertEqual(
            self.admin_clients("nova").aggregates.delete.return_value,
            result)
        self.admin_clients("nova").aggregates.delete.assert_called_once_with(
            "fake_aggregate")
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.delete_aggregate")

    def test_get_aggregate_details(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        result = nova_scenario._get_aggregate_details("fake_aggregate")
        self.assertEqual(
            self.admin_clients("nova").aggregates.get_details.return_value,
            result)
        self.admin_clients(
            "nova").aggregates.get_details.assert_called_once_with(
            "fake_aggregate")
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.get_aggregate_details")

    def test_update_aggregate(self):
        aggregate = mock.Mock()
        nova_scenario = utils.NovaScenario(context=self.context)
        nova_scenario.generate_random_name = mock.Mock(
            return_value="random_name")
        values = {"name": "random_name",
                  "availability_zone": "random_name"}
        result = nova_scenario._update_aggregate(aggregate=aggregate)
        self.assertEqual(
            self.admin_clients("nova").aggregates.update.return_value,
            result)
        self.admin_clients("nova").aggregates.update.assert_called_once_with(
            aggregate, values)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.update_aggregate")

    def test_aggregate_add_host(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        result = nova_scenario._aggregate_add_host("fake_agg", "fake_host")
        self.assertEqual(
            self.admin_clients("nova").aggregates.add_host.return_value,
            result)
        self.admin_clients("nova").aggregates.add_host.assert_called_once_with(
            "fake_agg", "fake_host")
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.aggregate_add_host")

    def test_aggregate_remove_host(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        result = nova_scenario._aggregate_remove_host("fake_agg", "fake_host")
        self.assertEqual(
            self.admin_clients("nova").aggregates.remove_host.return_value,
            result)
        self.admin_clients(
            "nova").aggregates.remove_host.assert_called_once_with(
            "fake_agg", "fake_host")
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.aggregate_remove_host")

    def test__uptime_hypervisor(self):
        nova_scenario = utils.NovaScenario()
        nova_scenario._uptime_hypervisor("fake_hostname")

        self.admin_clients("nova").hypervisors.uptime.assert_called_once_with(
            "fake_hostname")
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.uptime_hypervisor")

    def test_aggregate_set_metadata(self):
        nova_scenario = utils.NovaScenario(context=self.context)
        fake_metadata = {"test_metadata": "true"}
        result = nova_scenario._aggregate_set_metadata("fake_aggregate",
                                                       fake_metadata)
        self.assertEqual(
            self.admin_clients("nova").aggregates.set_metadata.return_value,
            result)
        self.admin_clients(
            "nova").aggregates.set_metadata.assert_called_once_with(
            "fake_aggregate", fake_metadata)
        self._test_atomic_action_timer(nova_scenario.atomic_actions(),
                                       "nova.aggregate_set_metadata")
