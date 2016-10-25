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

import random

from oslo_config import cfg

from rally import exceptions
from rally.plugins.openstack import scenario
from rally.plugins.openstack.wrappers import glance as glance_wrapper
from rally.plugins.openstack.wrappers import network as network_wrapper
from rally.task import atomic
from rally.task import utils

NOVA_BENCHMARK_OPTS = []
option_names_and_defaults = [
    # action, prepoll delay, timeout, poll interval
    ("start", 0, 300, 1),
    ("stop", 0, 300, 2),
    ("boot", 1, 300, 1),
    ("delete", 2, 300, 2),
    ("reboot", 2, 300, 2),
    ("rebuild", 1, 300, 1),
    ("rescue", 2, 300, 2),
    ("unrescue", 2, 300, 2),
    ("suspend", 2, 300, 2),
    ("resume", 2, 300, 2),
    ("pause", 2, 300, 2),
    ("unpause", 2, 300, 2),
    ("shelve", 2, 300, 2),
    ("unshelve", 2, 300, 2),
    ("image_create", 0, 300, 2),
    ("image_delete", 0, 300, 2),
    ("resize", 2, 400, 5),
    ("resize_confirm", 0, 200, 2),
    ("resize_revert", 0, 200, 2),
    ("live_migrate", 1, 400, 2),
    ("migrate", 1, 400, 2),
]

for action, prepoll, timeout, poll in option_names_and_defaults:
    NOVA_BENCHMARK_OPTS.extend([
        cfg.FloatOpt(
            "nova_server_%s_prepoll_delay" % action,
            default=float(prepoll),
            help="Time to sleep after %s before polling for status" % action
        ),
        cfg.FloatOpt(
            "nova_server_%s_timeout" % action,
            default=float(timeout),
            help="Server %s timeout" % action
        ),
        cfg.FloatOpt(
            "nova_server_%s_poll_interval" % action,
            default=float(poll),
            help="Server %s poll interval" % action
        )
    ])

NOVA_BENCHMARK_OPTS.extend([
    cfg.FloatOpt(
        "nova_detach_volume_timeout",
        default=float(200),
        help="Nova volume detach timeout"),
    cfg.FloatOpt(
        "nova_detach_volume_poll_interval",
        default=float(2),
        help="Nova volume detach poll interval")
])

CONF = cfg.CONF
benchmark_group = cfg.OptGroup(name="benchmark",
                               title="benchmark options")
CONF.register_group(benchmark_group)
CONF.register_opts(NOVA_BENCHMARK_OPTS, group=benchmark_group)


class NovaScenario(scenario.OpenStackScenario):
    """Base class for Nova scenarios with basic atomic actions."""

    @atomic.action_timer("nova.list_servers")
    def _list_servers(self, detailed=True):
        """Returns user servers list."""
        return self.clients("nova").servers.list(detailed)

    def _pick_random_nic(self):
        """Choose one network from existing ones."""
        ctxt = self.context
        nets = [net["id"]
                for net in ctxt.get("tenant", {}).get("networks", [])]
        if nets:
            # NOTE(amaretskiy): Balance servers among networks.
            net_idx = self.context["iteration"] % len(nets)
            return [{"net-id": nets[net_idx]}]

    @atomic.action_timer("nova.boot_server")
    def _boot_server(self, image_id, flavor_id,
                     auto_assign_nic=False, **kwargs):
        """Boot a server.

        Returns when the server is actually booted and in "ACTIVE" state.

        If multiple networks created by Network context are present, the first
        network found that isn't associated with a floating IP pool is used.

        :param image_id: int, image ID for server creation
        :param flavor_id: int, flavor ID for server creation
        :param auto_assign_nic: bool, whether or not to auto assign NICs
        :param kwargs: other optional parameters to initialize the server
        :returns: nova Server instance
        """
        server_name = self.generate_random_name()
        secgroup = self.context.get("user", {}).get("secgroup")
        if secgroup:
            if "security_groups" not in kwargs:
                kwargs["security_groups"] = [secgroup["name"]]
            elif secgroup["name"] not in kwargs["security_groups"]:
                kwargs["security_groups"].append(secgroup["name"])

        if auto_assign_nic and not kwargs.get("nics", False):
            nic = self._pick_random_nic()
            if nic:
                kwargs["nics"] = nic

        server = self.clients("nova").servers.create(
            server_name, image_id, flavor_id, **kwargs)

        self.sleep_between(CONF.benchmark.nova_server_boot_prepoll_delay)
        server = utils.wait_for_status(
            server,
            ready_statuses=["ACTIVE"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_boot_timeout,
            check_interval=CONF.benchmark.nova_server_boot_poll_interval
        )
        return server

    def _do_server_reboot(self, server, reboottype):
        server.reboot(reboot_type=reboottype)
        self.sleep_between(CONF.benchmark.nova_server_pause_prepoll_delay)
        utils.wait_for_status(
            server,
            ready_statuses=["ACTIVE"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_reboot_timeout,
            check_interval=CONF.benchmark.nova_server_reboot_poll_interval
        )

    @atomic.action_timer("nova.soft_reboot_server")
    def _soft_reboot_server(self, server):
        """Reboot a server with soft reboot.

        A soft reboot will be issued on the given server upon which time
        this method will wait for the server to become active.

        :param server: The server to reboot.
        """
        self._do_server_reboot(server, "SOFT")

    @atomic.action_timer("nova.show_server")
    def _show_server(self, server):
        """Show server details.

        :param server: The server to get details for.

        :returns: Server details
        """
        return self.clients("nova").servers.get(server)

    @atomic.action_timer("nova.get_console_output_server")
    def _get_server_console_output(self, server, length=None):
        """Get text of a console log output from a server.

        :param server: The server whose console output to retrieve
        :param length: The number of tail log lines you would like to retrieve.

        :returns: Text console output from server
        """
        return self.clients("nova").servers.get_console_output(server,
                                                               length=length)

    @atomic.action_timer("nova.reboot_server")
    def _reboot_server(self, server):
        """Reboot a server with hard reboot.

        A reboot will be issued on the given server upon which time
        this method will wait for the server to become active.

        :param server: The server to reboot.
        """
        self._do_server_reboot(server, "HARD")

    @atomic.action_timer("nova.rebuild_server")
    def _rebuild_server(self, server, image, **kwargs):
        """Rebuild a server with a new image.

        :param server: The server to rebuild.
        :param image: The new image to rebuild the server with.
        :param kwargs: Optional additional arguments to pass to the rebuild
        """
        server.rebuild(image, **kwargs)
        self.sleep_between(CONF.benchmark.nova_server_rebuild_prepoll_delay)
        utils.wait_for_status(
            server,
            ready_statuses=["ACTIVE"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_rebuild_timeout,
            check_interval=CONF.benchmark.nova_server_rebuild_poll_interval
        )

    @atomic.action_timer("nova.start_server")
    def _start_server(self, server):
        """Start the given server.

        A start will be issued for the given server upon which time
        this method will wait for it to become ACTIVE.

        :param server: The server to start and wait to become ACTIVE.
        """
        server.start()
        utils.wait_for_status(
            server,
            ready_statuses=["ACTIVE"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_start_timeout,
            check_interval=CONF.benchmark.nova_server_start_poll_interval
        )

    @atomic.action_timer("nova.stop_server")
    def _stop_server(self, server):
        """Stop the given server.

        Issues a stop on the given server and waits for the server
        to become SHUTOFF.

        :param server: The server to stop.
        """
        server.stop()
        utils.wait_for_status(
            server,
            ready_statuses=["SHUTOFF"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_stop_timeout,
            check_interval=CONF.benchmark.nova_server_stop_poll_interval
        )

    @atomic.action_timer("nova.rescue_server")
    def _rescue_server(self, server):
        """Rescue the given server.

        Returns when the server is actually rescue and is in the "Rescue"
        state.

        :param server: Server object
        """
        server.rescue()
        self.sleep_between(CONF.benchmark.nova_server_rescue_prepoll_delay)
        utils.wait_for_status(
            server,
            ready_statuses=["RESCUE"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_rescue_timeout,
            check_interval=CONF.benchmark.nova_server_rescue_poll_interval
        )

    @atomic.action_timer("nova.unrescue_server")
    def _unrescue_server(self, server):
        """Unrescue the given server.

        Returns when the server is unrescue and waits to become ACTIVE

        :param server: Server object
        """
        server.unrescue()
        self.sleep_between(CONF.benchmark.nova_server_unrescue_prepoll_delay)
        utils.wait_for_status(
            server,
            ready_statuses=["ACTIVE"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_unrescue_timeout,
            check_interval=CONF.benchmark.nova_server_unrescue_poll_interval
        )

    @atomic.action_timer("nova.suspend_server")
    def _suspend_server(self, server):
        """Suspends the given server.

        Returns when the server is actually suspended and is in the "Suspended"
        state.

        :param server: Server object
        """
        server.suspend()
        self.sleep_between(CONF.benchmark.nova_server_suspend_prepoll_delay)
        utils.wait_for_status(
            server,
            ready_statuses=["SUSPENDED"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_suspend_timeout,
            check_interval=CONF.benchmark.nova_server_suspend_poll_interval
        )

    @atomic.action_timer("nova.resume_server")
    def _resume_server(self, server):
        """Resumes the suspended server.

        Returns when the server is actually resumed and is in the "ACTIVE"
        state.

        :param server: Server object
        """
        server.resume()
        self.sleep_between(CONF.benchmark.nova_server_resume_prepoll_delay)
        utils.wait_for_status(
            server,
            ready_statuses=["ACTIVE"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_resume_timeout,
            check_interval=CONF.benchmark.nova_server_resume_poll_interval
        )

    @atomic.action_timer("nova.pause_server")
    def _pause_server(self, server):
        """Pause the live server.

        Returns when the server is actually paused and is in the "PAUSED"
        state.

        :param server: Server object
        """
        server.pause()
        self.sleep_between(CONF.benchmark.nova_server_pause_prepoll_delay)
        utils.wait_for_status(
            server,
            ready_statuses=["PAUSED"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_pause_timeout,
            check_interval=CONF.benchmark.nova_server_pause_poll_interval
        )

    @atomic.action_timer("nova.unpause_server")
    def _unpause_server(self, server):
        """Unpause the paused server.

        Returns when the server is actually unpaused and is in the "ACTIVE"
        state.

        :param server: Server object
        """
        server.unpause()
        self.sleep_between(CONF.benchmark.nova_server_pause_prepoll_delay)
        utils.wait_for_status(
            server,
            ready_statuses=["ACTIVE"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_unpause_timeout,
            check_interval=CONF.benchmark.nova_server_unpause_poll_interval
        )

    @atomic.action_timer("nova.shelve_server")
    def _shelve_server(self, server):
        """Shelve the given server.

        Returns when the server is actually shelved and is in the
        "SHELVED_OFFLOADED" state.

        :param server: Server object
        """
        server.shelve()
        self.sleep_between(CONF.benchmark.nova_server_pause_prepoll_delay)
        utils.wait_for_status(
            server,
            ready_statuses=["SHELVED_OFFLOADED"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_shelve_timeout,
            check_interval=CONF.benchmark.nova_server_shelve_poll_interval
        )

    @atomic.action_timer("nova.unshelve_server")
    def _unshelve_server(self, server):
        """Unshelve the given server.

        Returns when the server is unshelved and is in the "ACTIVE" state.

        :param server: Server object
        """
        server.unshelve()

        self.sleep_between(CONF.benchmark. nova_server_unshelve_prepoll_delay)
        utils.wait_for_status(
            server,
            ready_statuses=["ACTIVE"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_unshelve_timeout,
            check_interval=CONF.benchmark.nova_server_unshelve_poll_interval
        )

    def _delete_server(self, server, force=False):
        """Delete the given server.

        Returns when the server is actually deleted.

        :param server: Server object
        :param force: If True, force_delete will be used instead of delete.
        """
        atomic_name = ("nova.%sdelete_server") % (force and "force_" or "")
        with atomic.ActionTimer(self, atomic_name):
            if force:
                server.force_delete()
            else:
                server.delete()

            utils.wait_for_status(
                server,
                ready_statuses=["deleted"],
                check_deletion=True,
                update_resource=utils.get_from_manager(),
                timeout=CONF.benchmark.nova_server_delete_timeout,
                check_interval=CONF.benchmark.nova_server_delete_poll_interval
            )

    def _delete_servers(self, servers, force=False):
        """Delete multiple servers.

        :param servers: A list of servers to delete
        :param force: If True, force_delete will be used instead of delete.
        """
        atomic_name = ("nova.%sdelete_servers") % (force and "force_" or "")
        with atomic.ActionTimer(self, atomic_name):
            for server in servers:
                if force:
                    server.force_delete()
                else:
                    server.delete()

            for server in servers:
                utils.wait_for_status(
                    server,
                    ready_statuses=["deleted"],
                    check_deletion=True,
                    update_resource=utils.get_from_manager(),
                    timeout=CONF.benchmark.nova_server_delete_timeout,
                    check_interval=CONF.
                    benchmark.nova_server_delete_poll_interval
                )

    @atomic.action_timer("nova.delete_image")
    def _delete_image(self, image):
        """Delete the given image.

        Returns when the image is actually deleted.

        :param image: Image object
        """
        self.clients("glance").images.delete(image.id)
        wrapper = glance_wrapper.wrap(self._clients.glance, self)
        check_interval = CONF.benchmark.nova_server_image_delete_poll_interval
        utils.wait_for_status(
            image,
            ready_statuses=["deleted", "pending_delete"],
            check_deletion=True,
            update_resource=wrapper.get_image,
            timeout=CONF.benchmark.nova_server_image_delete_timeout,
            check_interval=check_interval
        )

    @atomic.action_timer("nova.create_image")
    def _create_image(self, server):
        """Create an image from the given server

        Uses the server name to name the created image. Returns when the image
        is actually created and is in the "Active" state.

        :param server: Server object for which the image will be created

        :returns: Created image object
        """
        image_uuid = self.clients("nova").servers.create_image(server,
                                                               server.name)
        image = self.clients("nova").images.get(image_uuid)
        check_interval = CONF.benchmark.nova_server_image_create_poll_interval
        image = utils.wait_for_status(
            image,
            ready_statuses=["ACTIVE"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_image_create_timeout,
            check_interval=check_interval
        )
        return image

    @atomic.action_timer("nova.list_images")
    def _list_images(self, detailed=False, **kwargs):
        """List all images.

        :param detailed: True if the image listing
                         should contain detailed information
        :param kwargs: Optional additional arguments for image listing

        :returns: Image list
        """
        return self.clients("nova").images.list(detailed, **kwargs)

    @atomic.action_timer("nova.create_keypair")
    def _create_keypair(self, **kwargs):
        """Create a keypair

        :returns: Created keypair name
        """
        keypair_name = self.generate_random_name()
        keypair = self.clients("nova").keypairs.create(keypair_name, **kwargs)
        return keypair.name

    @atomic.action_timer("nova.list_keypairs")
    def _list_keypairs(self):
        """Return user keypairs list."""
        return self.clients("nova").keypairs.list()

    @atomic.action_timer("nova.delete_keypair")
    def _delete_keypair(self, keypair_name):
        """Delete keypair

        :param keypair_name: The keypair name to delete.
        """
        self.clients("nova").keypairs.delete(keypair_name)

    @atomic.action_timer("nova.boot_servers")
    def _boot_servers(self, image_id, flavor_id, requests, instances_amount=1,
                      auto_assign_nic=False, **kwargs):
        """Boot multiple servers.

        Returns when all the servers are actually booted and are in the
        "Active" state.

        :param image_id: ID of the image to be used for server creation
        :param flavor_id: ID of the flavor to be used for server creation
        :param requests: Number of booting requests to perform
        :param instances_amount: Number of instances to boot per each request
        :param auto_assign_nic: bool, whether or not to auto assign NICs
        :param kwargs: other optional parameters to initialize the servers

        :returns: List of created server objects
        """
        if auto_assign_nic and not kwargs.get("nics", False):
            nic = self._pick_random_nic()
            if nic:
                kwargs["nics"] = nic

        name_prefix = self.generate_random_name()
        for i in range(requests):
            self.clients("nova").servers.create("%s_%d" % (name_prefix, i),
                                                image_id, flavor_id,
                                                min_count=instances_amount,
                                                max_count=instances_amount,
                                                **kwargs)
        # NOTE(msdubov): Nova python client returns only one server even when
        #                min_count > 1, so we have to rediscover all the
        #                created servers manually.
        servers = [s for s in self.clients("nova").servers.list()
                   if s.name.startswith(name_prefix)]
        self.sleep_between(CONF.benchmark.nova_server_boot_prepoll_delay)
        servers = [utils.wait_for_status(
            server,
            ready_statuses=["ACTIVE"],
            update_resource=utils.
            get_from_manager(),
            timeout=CONF.benchmark.nova_server_boot_timeout,
            check_interval=CONF.benchmark.nova_server_boot_poll_interval
        ) for server in servers]
        return servers

    @atomic.optional_action_timer("nova.associate_floating_ip")
    def _associate_floating_ip(self, server, address, fixed_address=None):
        """Add floating IP to an instance

        :param server: The :class:`Server` to add an IP to.
        :param address: The ip address or FloatingIP to add to the instance
        :param fixed_address: The fixedIP address the FloatingIP is to be
               associated with (optional)
        :param atomic_action: True if this is an atomic action. added
                              and handled by the
                              optional_action_timer() decorator
        """
        server.add_floating_ip(address, fixed_address=fixed_address)
        utils.wait_for(server,
                       is_ready=self.check_ip_address(address),
                       update_resource=utils.get_from_manager())
        # Update server data
        server.addresses = server.manager.get(server.id).addresses

    @atomic.optional_action_timer("nova.dissociate_floating_ip")
    def _dissociate_floating_ip(self, server, address):
        """Remove floating IP from an instance

        :param server: The :class:`Server` to add an IP to.
        :param address: The ip address or FloatingIP to remove
        :param atomic_action: True if this is an atomic action. added
                              and handled by the
                              optional_action_timer() decorator
        """
        server.remove_floating_ip(address)
        utils.wait_for(
            server,
            is_ready=self.check_ip_address(address, must_exist=False),
            update_resource=utils.get_from_manager()
        )
        # Update server data
        server.addresses = server.manager.get(server.id).addresses

    @staticmethod
    def check_ip_address(address, must_exist=True):
        ip_to_check = getattr(address, "ip", address)

        def _check_addr(resource):
            for network, addr_list in resource.addresses.items():
                for addr in addr_list:
                        if ip_to_check == addr["addr"]:
                            return must_exist
            return not must_exist
        return _check_addr

    @atomic.action_timer("nova.list_networks")
    def _list_networks(self):
        """Return user networks list."""
        return self.clients("nova").networks.list()

    @atomic.action_timer("nova.resize")
    def _resize(self, server, flavor):
        server.resize(flavor)
        utils.wait_for_status(
            server,
            ready_statuses=["VERIFY_RESIZE"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_resize_timeout,
            check_interval=CONF.benchmark.nova_server_resize_poll_interval
        )

    @atomic.action_timer("nova.resize_confirm")
    def _resize_confirm(self, server, status="ACTIVE"):
        server.confirm_resize()
        utils.wait_for_status(
            server,
            ready_statuses=[status],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_resize_confirm_timeout,
            check_interval=(
                CONF.benchmark.nova_server_resize_confirm_poll_interval)
        )

    @atomic.action_timer("nova.resize_revert")
    def _resize_revert(self, server, status="ACTIVE"):
        server.revert_resize()
        utils.wait_for_status(
            server,
            ready_statuses=[status],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_resize_revert_timeout,
            check_interval=(
                CONF.benchmark.nova_server_resize_revert_poll_interval)
        )

    @atomic.action_timer("nova.attach_volume")
    def _attach_volume(self, server, volume, device=None):
        server_id = server.id
        volume_id = volume.id
        attachment = self.clients("nova").volumes.create_server_volume(
            server_id, volume_id, device)
        utils.wait_for_status(
            volume,
            ready_statuses=["in-use"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_resize_revert_timeout,
            check_interval=(
                CONF.benchmark.nova_server_resize_revert_poll_interval)
        )
        return attachment

    @atomic.action_timer("nova.detach_volume")
    def _detach_volume(self, server, volume, attachment=None):
        server_id = server.id
        # NOTE(chenhb): Recommend the use of attachment.The use of
        # volume.id is retained mainly for backwoard compatible.
        attachment_id = attachment.id if attachment else volume.id

        self.clients("nova").volumes.delete_server_volume(server_id,
                                                          attachment_id)
        utils.wait_for_status(
            volume,
            ready_statuses=["available"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.nova_detach_volume_timeout,
            check_interval=CONF.benchmark.nova_detach_volume_poll_interval
        )

    @atomic.action_timer("nova.live_migrate")
    def _live_migrate(self, server, target_host, block_migration=False,
                      disk_over_commit=False, skip_host_check=False):
        """Run live migration of the given server.

        :param server: Server object
        :param target_host: Specifies the target compute node to migrate
        :param block_migration: Specifies the migration type
        :param disk_over_commit: Specifies whether to overcommit migrated
                                 instance or not
        :param skip_host_check: Specifies whether to verify the targeted host
                                availability
        """
        server_admin = self.admin_clients("nova").servers.get(server.id)
        host_pre_migrate = getattr(server_admin, "OS-EXT-SRV-ATTR:host")
        server_admin.live_migrate(target_host,
                                  block_migration=block_migration,
                                  disk_over_commit=disk_over_commit)
        utils.wait_for_status(
            server,
            ready_statuses=["ACTIVE"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_live_migrate_timeout,
            check_interval=(
                CONF.benchmark.nova_server_live_migrate_poll_interval)
        )
        server_admin = self.admin_clients("nova").servers.get(server.id)
        if (host_pre_migrate == getattr(server_admin, "OS-EXT-SRV-ATTR:host")
                and not skip_host_check):
            raise exceptions.LiveMigrateException(
                "Migration complete but instance did not change host: %s" %
                host_pre_migrate)

    @atomic.action_timer("nova.find_host_to_migrate")
    def _find_host_to_migrate(self, server):
        """Find a compute node for live migration.

        :param server: Server object
        """
        server_admin = self.admin_clients("nova").servers.get(server.id)
        host = getattr(server_admin, "OS-EXT-SRV-ATTR:host")
        az_name = getattr(server_admin, "OS-EXT-AZ:availability_zone")
        az = None
        for a in self.admin_clients("nova").availability_zones.list():
            if az_name == a.zoneName:
                az = a
                break
        try:
            new_host = random.choice(
                [key for key, value in az.hosts.items()
                    if key != host and
                    value.get("nova-compute", {}).get("available", False)])
            return new_host
        except IndexError:
            raise exceptions.InvalidHostException(
                "No valid host found to migrate")

    @atomic.action_timer("nova.migrate")
    def _migrate(self, server, skip_host_check=False):
        """Run migration of the given server.

        :param server: Server object
        :param skip_host_check: Specifies whether to verify the targeted host
                                availability
        """
        server_admin = self.admin_clients("nova").servers.get(server.id)
        host_pre_migrate = getattr(server_admin, "OS-EXT-SRV-ATTR:host")
        server_admin.migrate()
        utils.wait_for_status(
            server,
            ready_statuses=["VERIFY_RESIZE"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.nova_server_migrate_timeout,
            check_interval=(
                CONF.benchmark.nova_server_migrate_poll_interval)
        )
        if not skip_host_check:
            server_admin = self.admin_clients("nova").servers.get(server.id)
            host_after_migrate = getattr(server_admin, "OS-EXT-SRV-ATTR:host")
            if host_pre_migrate == host_after_migrate:
                raise exceptions.MigrateException(
                    "Migration complete but instance did not change host: %s" %
                    host_pre_migrate)

    def _create_security_groups(self, security_group_count):
        security_groups = []
        with atomic.ActionTimer(self, "nova.create_%s_security_groups" %
                                security_group_count):
            for i in range(security_group_count):
                sg_name = self.generate_random_name()
                sg = self.clients("nova").security_groups.create(sg_name,
                                                                 sg_name)
                security_groups.append(sg)

        return security_groups

    def _create_rules_for_security_group(self, security_groups,
                                         rules_per_security_group,
                                         ip_protocol="tcp", cidr="0.0.0.0/0"):
        action_name = ("nova.create_%s_rules" % (rules_per_security_group *
                                                 len(security_groups)))
        creation_status = True
        with atomic.ActionTimer(self, action_name):
            for i, security_group in enumerate(security_groups):
                result = True
                for j in range(rules_per_security_group):
                    result = self.clients("nova").security_group_rules.create(
                        security_group.id,
                        from_port=(i * rules_per_security_group + j + 1),
                        to_port=(i * rules_per_security_group + j + 1),
                        ip_protocol=ip_protocol,
                        cidr=cidr)
                if not result:
                    creation_status = False
        return creation_status

    def _update_security_groups(self, security_groups):
        """Update a list of security groups

        :param security_groups: list, security_groups that are to be updated
        """
        with atomic.ActionTimer(self, "nova.update_%s_security_groups" %
                                len(security_groups)):
            for sec_group in security_groups:
                sg_new_name = self.generate_random_name()
                sg_new_desc = self.generate_random_name()
                self.clients("nova").security_groups.update(sec_group.id,
                                                            sg_new_name,
                                                            sg_new_desc)

    def _delete_security_groups(self, security_group):
        with atomic.ActionTimer(self, "nova.delete_%s_security_groups" %
                                len(security_group)):
            for sg in security_group:
                self.clients("nova").security_groups.delete(sg.id)

    def _list_security_groups(self):
        """Return security groups list."""
        with atomic.ActionTimer(self, "nova.list_security_groups"):
            return self.clients("nova").security_groups.list()

    @atomic.optional_action_timer("nova.add_server_secgroups")
    def _add_server_secgroups(self, server, security_group,
                              atomic_action=False):
        """add security group to a server.

        :param server: Server object
        :param security_groups: The name of security group to add.
        :param atomic_action: True if this is atomic action. added and
                              handled by the optional_action_timer()
                              decorator.
        :returns: An instance of novaclient.base.DictWithMeta
        """
        return self.clients("nova").servers.add_security_group(server,
                                                               security_group)

    @atomic.action_timer("nova.list_floating_ips_bulk")
    def _list_floating_ips_bulk(self):
        """List all floating IPs."""
        return self.admin_clients("nova").floating_ips_bulk.list()

    @atomic.action_timer("nova.create_floating_ips_bulk")
    def _create_floating_ips_bulk(self, ip_range, **kwargs):
        """Create floating IPs by range."""
        ip_range = network_wrapper.generate_cidr(start_cidr=ip_range)
        pool_name = self.generate_random_name()
        return self.admin_clients("nova").floating_ips_bulk.create(
            ip_range=ip_range, pool=pool_name, **kwargs)

    @atomic.action_timer("nova.delete_floating_ips_bulk")
    def _delete_floating_ips_bulk(self, ip_range):
        """Delete floating IPs by range."""
        return self.admin_clients("nova").floating_ips_bulk.delete(ip_range)

    @atomic.action_timer("nova.list_hypervisors")
    def _list_hypervisors(self, detailed=True):
        """List hypervisors."""
        return self.admin_clients("nova").hypervisors.list(detailed)

    @atomic.action_timer("nova.statistics_hypervisors")
    def _statistics_hypervisors(self):
        """Get hypervisor statistics over all compute nodes.

        :returns: Hypervisor statistics
        """
        return self.admin_clients("nova").hypervisors.statistics()

    @atomic.optional_action_timer("nova.get_hypervisor")
    def _get_hypervisor(self, hypervisor):
        """Get a specific hypervisor.

        :param hypervisor: Hypervisor to get.
        :param atomic_action: True if this is atomic action. added and
                              handled by the optional_action_timer()
                              decorator.
        :returns: Hypervisor object
        """
        return self.admin_clients("nova").hypervisors.get(hypervisor)

    @atomic.optional_action_timer("nova.search_hypervisors")
    def _search_hypervisors(self, hypervisor_match, servers=False):
        """List all servers belonging to specific hypervisor.

        :param hypervisor_match: Hypervisor's host name.
        :param servers: If True, server information is also retrieved.
        :param atomic_action: True if this is atomic action. added and
                              handled by the optional_action_timer()
                              decorator.
        :returns: Hypervisor object
        """
        return self.admin_clients("nova").hypervisors.search(hypervisor_match,
                                                             servers=servers)

    @atomic.action_timer("nova.lock_server")
    def _lock_server(self, server):
        """Lock the given server.

        :param server: Server to lock
        """
        server.lock()

    @atomic.optional_action_timer("nova.uptime_hypervisor")
    def _uptime_hypervisor(self, hypervisor, atomic_action=False):
        """Display the uptime of the specified hypervisor.

        :param hypervisor: Hypervisor to get.
        :param atomic_action: True if this is atomic action. added and
                              handled by the optional_action_timer()
                              decorator.
        :returns: Hypervisor object
        """
        return self.admin_clients("nova").hypervisors.uptime(hypervisor)

    @atomic.action_timer("nova.unlock_server")
    def _unlock_server(self, server):
        """Unlock the given server.

        :param server: Server to unlock
        """
        server.unlock()

    @atomic.action_timer("nova.create_network")
    def _create_network(self, ip_range, **kwargs):
        """Create nova network.

        :param ip_range: IP range in CIDR notation to create
        """
        net_label = self.generate_random_name()
        ip_range = network_wrapper.generate_cidr(start_cidr=ip_range)
        return self.admin_clients("nova").networks.create(
            label=net_label, cidr=ip_range, **kwargs)

    @atomic.action_timer("nova.delete_network")
    def _delete_network(self, net_id):
        """Delete nova network.

        :param net_id: The nova-network ID to delete
        """
        return self.admin_clients("nova").networks.delete(net_id)

    @atomic.action_timer("nova.list_flavors")
    def _list_flavors(self, detailed=True, **kwargs):
        """List all flavors.

        :param kwargs: Optional additional arguments for flavor listing
        :param detailed: True if the image listing
                         should contain detailed information
        :returns: flavors list
        """
        return self.clients("nova").flavors.list(detailed, **kwargs)

    @atomic.action_timer("nova.set_flavor_keys")
    def _set_flavor_keys(self, flavor, extra_specs):
        """set flavor keys

        :param flavor: flavor to set keys
        :param extra_specs: additional arguments for flavor set keys
        """
        return flavor.set_keys(extra_specs)

    @atomic.action_timer("nova.list_agents")
    def _list_agents(self, hypervisor=None):
        """List all nova-agent builds.

        :param hypervisor: The nova-hypervisor ID on which we need to list all
                           the builds
        :returns: Nova-agent build list
        """
        return self.admin_clients("nova").agents.list(hypervisor)

    @atomic.action_timer("nova.list_aggregates")
    def _list_aggregates(self):
        """Returns list of all os-aggregates."""
        return self.admin_clients("nova").aggregates.list()

    @atomic.action_timer("nova.list_availbility_zones")
    def _list_availability_zones(self, detailed=True):
        """List availability-zones.

        :param detailed: True if the availability-zone listing should contain
                         detailed information
        :returns: Availability-zone list
        """
        return self.admin_clients("nova").availability_zones.list(detailed)

    @atomic.action_timer("nova.list_hosts")
    def _list_hosts(self, zone=None):
        """List nova hosts.

        :param zone: List all hosts in the given nova availability-zone ID
        :returns: Nova host list
        """
        return self.admin_clients("nova").hosts.list(zone)

    @atomic.optional_action_timer("nova.get_host")
    def _get_host(self, host_name):
        """Describe a specific host.

        :param host_name: host name to get.
        :param atomic_action: True if this is atomic action. added and
                              handled by the optional_action_timer()
                              decorator.
        :returns: host object
        """
        return self.admin_clients("nova").hosts.get(host_name)

    @atomic.action_timer("nova.list_services")
    def _list_services(self, host=None, binary=None):
        """return all nova service details

        :param host: List all nova services on host
        :param binary: List all nova services matching  given binary
        """
        return self.admin_clients("nova").services.list(host, binary)

    @atomic.action_timer("nova.create_flavor")
    def _create_flavor(self, ram, vcpus, disk, **kwargs):
        """Create a flavor

        :param ram: Memory in MB for the flavor
        :param vcpus: Number of VCPUs for the flavor
        :param disk: Size of local disk in GB
        :param kwargs: Optional additional arguments for flavor creation
        """
        name = self.generate_random_name()
        return self.admin_clients("nova").flavors.create(name, ram, vcpus,
                                                         disk, **kwargs)

    @atomic.action_timer("nova.delete_flavor")
    def _delete_flavor(self, flavor):
        """Delete a flavor

        :param flavor: The ID of the :class:`Flavor`
        :returns: An instance of novaclient.base.TupleWithMeta
        """
        return self.admin_clients("nova").flavors.delete(flavor)

    @atomic.action_timer("nova.list_flavor_access")
    def _list_flavor_access(self, flavor):
        """List access-rules for non-public flavor.

        :param flavor: List access rules for flavor instance or flavor ID
        """
        return self.admin_clients("nova").flavor_access.list(flavor=flavor)

    @atomic.action_timer("nova.add_tenant_access")
    def _add_tenant_access(self, flavor, tenant):
        """Add a tenant to the given flavor access list.

        :param flavor: name or id of the object flavor
        :param tenant: id of the object tenant
        :returns: access rules for flavor instance or flavor ID
        """
        return self.admin_clients("nova").flavor_access.add_tenant_access(
            flavor, tenant)

    @atomic.action_timer("nova.update_server")
    def _update_server(self, server, description=None):
        """update the server's name and description.

        :param server: Server object
        :param description: update the server description
        :returns: The updated server
        """
        new_name = self.generate_random_name()
        if description:
            return server.update(name=new_name,
                                 description=description)
        else:
            return server.update(name=new_name)

    @atomic.action_timer("nova.get_flavor")
    def _get_flavor(self, flavor_id):
        """Show a flavor

        :param flavor_id: The flavor ID to get
        """
        return self.admin_clients("nova").flavors.get(flavor_id)

    @atomic.action_timer("nova.create_aggregate")
    def _create_aggregate(self, availability_zone):
        """Create a new aggregate.

        :param availability_zone: The availability zone of the aggregate
        :returns: The created aggregate
        """
        aggregate_name = self.generate_random_name()
        return self.admin_clients("nova").aggregates.create(aggregate_name,
                                                            availability_zone)

    @atomic.action_timer("nova.get_aggregate_details")
    def _get_aggregate_details(self, aggregate):
        """Get details of the specified aggregate.

        :param aggregate: The aggregate to get details
        :returns: Detailed information of aggregate
        """
        return self.admin_clients("nova").aggregates.get_details(aggregate)

    @atomic.action_timer("nova.delete_aggregate")
    def _delete_aggregate(self, aggregate):
        """Delete the specified aggregate.

        :param aggregate: The aggregate to delete
        :returns: An instance of novaclient.base.TupleWithMeta
        """
        return self.admin_clients("nova").aggregates.delete(aggregate)

    @atomic.action_timer("nova.bind_actions")
    def _bind_actions(self):
        actions = ["hard_reboot", "soft_reboot", "stop_start",
                   "rescue_unrescue", "pause_unpause", "suspend_resume",
                   "lock_unlock", "shelve_unshelve"]
        action_builder = utils.ActionBuilder(actions)
        action_builder.bind_action("hard_reboot", self._reboot_server)
        action_builder.bind_action("soft_reboot", self._soft_reboot_server)
        action_builder.bind_action("stop_start",
                                   self._stop_and_start_server)
        action_builder.bind_action("rescue_unrescue",
                                   self._rescue_and_unrescue_server)
        action_builder.bind_action("pause_unpause",
                                   self._pause_and_unpause_server)
        action_builder.bind_action("suspend_resume",
                                   self._suspend_and_resume_server)
        action_builder.bind_action("lock_unlock",
                                   self._lock_and_unlock_server)
        action_builder.bind_action("shelve_unshelve",
                                   self._shelve_and_unshelve_server)

        return action_builder

    @atomic.action_timer("nova.stop_and_start_server")
    def _stop_and_start_server(self, server):
        """Stop and then start the given server.

        A stop will be issued on the given server upon which time
        this method will wait for the server to become 'SHUTOFF'.
        Once the server is SHUTOFF a start will be issued and this
        method will wait for the server to become 'ACTIVE' again.

        :param server: The server to stop and then start.

        """
        self._stop_server(server)
        self._start_server(server)

    @atomic.action_timer("nova.rescue_and_unrescue_server")
    def _rescue_and_unrescue_server(self, server):
        """Rescue and then unrescue the given server.

        A rescue will be issued on the given server upon which time
        this method will wait for the server to become 'RESCUE'.
        Once the server is RESCUE an unrescue will be issued and
        this method will wait for the server to become 'ACTIVE'
        again.

        :param server: The server to rescue and then unrescue.

        """
        self._rescue_server(server)
        self._unrescue_server(server)

    @atomic.action_timer("nova.pause_and_unpause_server")
    def _pause_and_unpause_server(self, server):
        """Pause and then unpause the given server.

        A pause will be issued on the given server upon which time
        this method will wait for the server to become 'PAUSED'.
        Once the server is PAUSED an unpause will be issued and
        this method will wait for the server to become 'ACTIVE'
        again.

        :param server: The server to pause and then unpause.

        """
        self._pause_server(server)
        self._unpause_server(server)

    @atomic.action_timer("nova.suspend_and_resume_server")
    def _suspend_and_resume_server(self, server):
        """Suspend and then resume the given server.

        A suspend will be issued on the given server upon which time
        this method will wait for the server to become 'SUSPENDED'.
        Once the server is SUSPENDED an resume will be issued and
        this method will wait for the server to become 'ACTIVE'
        again.

        :param server: The server to suspend and then resume.

        """
        self._suspend_server(server)
        self._resume_server(server)

    @atomic.action_timer("nova.lock_and_unlock_server")
    def _lock_and_unlock_server(self, server):
        """Lock and then unlock the given server.

        A lock will be issued on the given server upon which time
        this method will wait for the server to become locked'.
        Once the server is locked an unlock will be issued.

        :param server: The server to lock and then unlock.

        """
        self._lock_server(server)
        self._unlock_server(server)

    @atomic.action_timer("nova.shelve_and_unshelve_server")
    def _shelve_and_unshelve_server(self, server):
        """Shelve and then unshelve the given server.

        A shelve will be issued on the given server upon which time
        this method will wait for the server to become 'SHELVED'.
        Once the server is SHELVED an unshelve will be issued and
        this method will wait for the server to become 'ACTIVE'
        again.

        :param server: The server to shelve and then unshelve.

        """
        self._shelve_server(server)
        self._unshelve_server(server)

    @atomic.action_timer("nova.update_aggregate")
    def _update_aggregate(self, aggregate):
        """Update the aggregate's name and availability_zone.

        :param aggregate: The aggregate to update
        :return: The updated aggregate
        """
        aggregate_name = self.generate_random_name()
        availability_zone = self.generate_random_name()
        values = {"name": aggregate_name,
                  "availability_zone": availability_zone}
        return self.admin_clients("nova").aggregates.update(aggregate,
                                                            values)

    @atomic.action_timer("nova.aggregate_add_host")
    def _aggregate_add_host(self, aggregate, host):
        """Add a host into the Host Aggregate.

        :param aggregate: The aggregate add host to
        :param host: The host add to aggregate
        :returns: The aggregate that has been added host to
        """
        return self.admin_clients("nova").aggregates.add_host(aggregate,
                                                              host)

    @atomic.action_timer("nova.aggregate_remove_host")
    def _aggregate_remove_host(self, aggregate, host):
        """Remove a host from an aggregate.

        :param aggregate: The aggregate remove host from
        :param host: The host to remove
        :returns: The aggregate that has been removed host from
        """
        return self.admin_clients("nova").aggregates.remove_host(aggregate,
                                                                 host)

    @atomic.action_timer("nova.aggregate_set_metadata")
    def _aggregate_set_metadata(self, aggregate, metadata):
        """Set metadata to an aggregate

        :param aggregate: The aggregate to set metadata to
        :param metadata: The metadata to be set
        :return: The aggregate that has the set metadata
        """
        return self.admin_clients("nova").aggregates.set_metadata(aggregate,
                                                                  metadata)
