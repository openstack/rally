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

import jsonschema

from rally.common import logging
from rally import consts
from rally import exceptions as rally_exceptions
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.cinder import utils as cinder_utils
from rally.plugins.openstack.scenarios.nova import utils
from rally.plugins.openstack.wrappers import network as network_wrapper
from rally.task import types
from rally.task import validation


"""Scenarios for Nova servers."""


LOG = logging.getLogger(__name__)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image")
@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["nova"]},
                    name="NovaServers.boot_and_list_server")
class BootAndListServer(utils.NovaScenario, cinder_utils.CinderScenario):

    def run(self, image, flavor, detailed=True, **kwargs):
        """Boot a server from an image and then list all servers.

        Measure the "nova list" command performance.

        If you have only 1 user in your context, you will
        add 1 server on every iteration. So you will have more
        and more servers and will be able to measure the
        performance of the "nova list" command depending on
        the number of servers owned by users.

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param detailed: True if the server listing should contain
                         detailed information about all of them
        :param kwargs: Optional additional arguments for server creation
        """
        server = self._boot_server(image, flavor, **kwargs)
        msg = ("Servers isn't created")
        self.assertTrue(server, err_msg=msg)

        pool_list = self._list_servers(detailed)
        msg = ("Server not included into list of available servers\n"
               "Booted server: {}\n"
               "Pool of servers: {}").format(server, pool_list)
        self.assertIn(server, pool_list, err_msg=msg)


@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["nova"]},
                    name="NovaServers.list_servers")
class ListServers(utils.NovaScenario, cinder_utils.CinderScenario):

    def run(self, detailed=True):
        """List all servers.

        This simple scenario test the nova list command by listing
        all the servers.

        :param detailed: True if detailed information about servers
                         should be listed
        """
        self._list_servers(detailed)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image")
@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["nova"]},
                    name="NovaServers.boot_and_delete_server")
class BootAndDeleteServer(utils.NovaScenario, cinder_utils.CinderScenario):

    def run(self, image, flavor, min_sleep=0, max_sleep=0,
            force_delete=False, **kwargs):
        """Boot and delete a server.

        Optional 'min_sleep' and 'max_sleep' parameters allow the scenario
        to simulate a pause between volume creation and deletion
        (of random duration from [min_sleep, max_sleep]).

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param min_sleep: Minimum sleep time in seconds (non-negative)
        :param max_sleep: Maximum sleep time in seconds (non-negative)
        :param force_delete: True if force_delete should be used
        :param kwargs: Optional additional arguments for server creation
        """
        server = self._boot_server(image, flavor, **kwargs)
        self.sleep_between(min_sleep, max_sleep)
        self._delete_server(server, force=force_delete)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image")
@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(admin=True, users=True)
@scenario.configure(context={"cleanup": ["nova"]},
                    name="NovaServers.boot_and_delete_multiple_servers")
class BootAndDeleteMultipleServers(utils.NovaScenario,
                                   cinder_utils.CinderScenario):

    def run(self, image, flavor, count=2, min_sleep=0,
            max_sleep=0, force_delete=False, **kwargs):
        """Boot multiple servers in a single request and delete them.

        Deletion is done in parallel with one request per server, not
        with a single request for all servers.

        :param image: The image to boot from
        :param flavor: Flavor used to boot instance
        :param count: Number of instances to boot
        :param min_sleep: Minimum sleep time in seconds (non-negative)
        :param max_sleep: Maximum sleep time in seconds (non-negative)
        :param force_delete: True if force_delete should be used
        :param kwargs: Optional additional arguments for instance creation
        """
        servers = self._boot_servers(image, flavor, 1, instances_amount=count,
                                     **kwargs)
        self.sleep_between(min_sleep, max_sleep)
        self._delete_servers(servers, force=force_delete)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image", validate_disk=False)
@validation.required_services(consts.Service.NOVA, consts.Service.CINDER)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["nova", "cinder"]},
                    name="NovaServers.boot_server_from_volume_and_delete")
class BootServerFromVolumeAndDelete(utils.NovaScenario,
                                    cinder_utils.CinderScenario):

    def run(self, image, flavor, volume_size, volume_type=None,
            min_sleep=0, max_sleep=0, force_delete=False, **kwargs):
        """Boot a server from volume and then delete it.

        The scenario first creates a volume and then a server.
        Optional 'min_sleep' and 'max_sleep' parameters allow the scenario
        to simulate a pause between volume creation and deletion
        (of random duration from [min_sleep, max_sleep]).

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param volume_size: volume size (in GB)
        :param volume_type: specifies volume type when there are
                            multiple backends
        :param min_sleep: Minimum sleep time in seconds (non-negative)
        :param max_sleep: Maximum sleep time in seconds (non-negative)
        :param force_delete: True if force_delete should be used
        :param kwargs: Optional additional arguments for server creation
        """
        volume = self._create_volume(volume_size, imageRef=image,
                                     volume_type=volume_type)
        block_device_mapping = {"vda": "%s:::1" % volume.id}
        server = self._boot_server(None, flavor,
                                   block_device_mapping=block_device_mapping,
                                   **kwargs)
        self.sleep_between(min_sleep, max_sleep)
        self._delete_server(server, force=force_delete)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image")
@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["nova"]},
                    name="NovaServers.boot_and_bounce_server")
class BootAndBounceServer(utils.NovaScenario, cinder_utils.CinderScenario):

    def run(self, image, flavor, force_delete=False, actions=None, **kwargs):
        """Boot a server and run specified actions against it.

        Actions should be passed into the actions parameter. Available actions
        are 'hard_reboot', 'soft_reboot', 'stop_start', 'rescue_unrescue',
        'pause_unpause', 'suspend_resume', 'lock_unlock' and 'shelve_unshelve'.
        Delete server after all actions were completed.

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param force_delete: True if force_delete should be used
        :param actions: list of action dictionaries, where each action
                        dictionary speicifes an action to be performed
                        in the following format:
                        {"action_name": <no_of_iterations>}
        :param kwargs: Optional additional arguments for server creation
        """
        action_builder = self._bind_actions()
        actions = actions or []
        try:
            action_builder.validate(actions)
        except jsonschema.exceptions.ValidationError as error:
            raise rally_exceptions.InvalidConfigException(
                "Invalid server actions configuration \'%(actions)s\' due to: "
                "%(error)s" % {"actions": str(actions), "error": str(error)})
        server = self._boot_server(image, flavor, **kwargs)
        for action in action_builder.build_actions(actions, server):
            action()
        self._delete_server(server, force=force_delete)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image")
@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["nova"]},
                    name="NovaServers.boot_lock_unlock_and_delete")
class BootLockUnlockAndDelete(utils.NovaScenario, cinder_utils.CinderScenario):

    def run(self, image, flavor, min_sleep=0,
            max_sleep=0, force_delete=False, **kwargs):
        """Boot a server, lock it, then unlock and delete it.

        Optional 'min_sleep' and 'max_sleep' parameters allow the
        scenario to simulate a pause between locking and unlocking the
        server (of random duration from min_sleep to max_sleep).

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param min_sleep: Minimum sleep time between locking and unlocking
                          in seconds
        :param max_sleep: Maximum sleep time between locking and unlocking
                          in seconds
        :param force_delete: True if force_delete should be used
        :param kwargs: Optional additional arguments for server creation
        """
        server = self._boot_server(image, flavor, **kwargs)
        self._lock_server(server)
        self.sleep_between(min_sleep, max_sleep)
        self._unlock_server(server)
        self._delete_server(server, force=force_delete)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image")
@validation.required_services(consts.Service.NOVA, consts.Service.GLANCE)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["nova", "glance"]},
                    name="NovaServers.snapshot_server")
class SnapshotServer(utils.NovaScenario, cinder_utils.CinderScenario):

    def run(self, image, flavor, force_delete=False, **kwargs):
        """Boot a server, make its snapshot and delete both.

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param force_delete: True if force_delete should be used
        :param kwargs: Optional additional arguments for server creation
        """

        server = self._boot_server(image, flavor, **kwargs)
        image = self._create_image(server)
        self._delete_server(server, force=force_delete)

        server = self._boot_server(image.id, flavor, **kwargs)
        self._delete_server(server, force=force_delete)
        self._delete_image(image)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image")
@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["nova"]},
                    name="NovaServers.boot_server")
class BootServer(utils.NovaScenario, cinder_utils.CinderScenario):

    def run(self, image, flavor, auto_assign_nic=False, **kwargs):
        """Boot a server.

        Assumes that cleanup is done elsewhere.

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param auto_assign_nic: True if NICs should be assigned
        :param kwargs: Optional additional arguments for server creation
        """
        self._boot_server(image, flavor,
                          auto_assign_nic=auto_assign_nic, **kwargs)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image", validate_disk=False)
@validation.required_services(consts.Service.NOVA, consts.Service.CINDER)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["nova", "cinder"]},
                    name="NovaServers.boot_server_from_volume")
class BootServerFromVolume(utils.NovaScenario, cinder_utils.CinderScenario):

    def run(self, image, flavor, volume_size,
            volume_type=None, auto_assign_nic=False, **kwargs):
        """Boot a server from volume.

        The scenario first creates a volume and then a server.
        Assumes that cleanup is done elsewhere.

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param volume_size: volume size (in GB)
        :param volume_type: specifies volume type when there are
                            multiple backends
        :param auto_assign_nic: True if NICs should be assigned
        :param kwargs: Optional additional arguments for server creation
        """
        volume = self._create_volume(volume_size, imageRef=image,
                                     volume_type=volume_type)
        block_device_mapping = {"vda": "%s:::1" % volume.id}
        self._boot_server(None, flavor, auto_assign_nic=auto_assign_nic,
                          block_device_mapping=block_device_mapping,
                          **kwargs)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"},
               to_flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image")
@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["nova"]},
                    name="NovaServers.resize_server")
class ResizeServer(utils.NovaScenario, cinder_utils.CinderScenario):

    def run(self, image, flavor, to_flavor, force_delete=False, **kwargs):
        """Boot a server, then resize and delete it.

        This test will confirm the resize by default,
        or revert the resize if confirm is set to false.

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param to_flavor: flavor to be used to resize the booted instance
        :param force_delete: True if force_delete should be used
        :param kwargs: Optional additional arguments for server creation
        """
        server = self._boot_server(image, flavor, **kwargs)
        self._resize(server, to_flavor)
        # by default we confirm
        confirm = kwargs.get("confirm", True)
        if confirm:
            self._resize_confirm(server)
        else:
            self._resize_revert(server)
        self._delete_server(server, force=force_delete)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"},
               to_flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image")
@validation.required_services(consts.Service.NOVA, consts.Service.CINDER)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["cinder", "nova"]},
                    name=("NovaServers.boot_server"
                          "_attach_created_volume_and_resize"))
class BootServerAttachCreatedVolumeAndResize(utils.NovaScenario,
                                             cinder_utils.CinderScenario):

    def run(self, image, flavor, to_flavor, volume_size, min_sleep=0,
            max_sleep=0, force_delete=False, confirm=True, do_delete=True,
            boot_server_kwargs=None, create_volume_kwargs=None):
        """Create a VM from image, attach a volume to it and resize.

        Simple test to create a VM and attach a volume, then resize the VM,
        detach the volume then delete volume and VM.
        Optional 'min_sleep' and 'max_sleep' parameters allow the scenario
        to simulate a pause between attaching a volume and running resize
        (of random duration from range [min_sleep, max_sleep]).
        :param image: Glance image name to use for the VM
        :param flavor: VM flavor name
        :param to_flavor: flavor to be used to resize the booted instance
        :param volume_size: volume size (in GB)
        :param min_sleep: Minimum sleep time in seconds (non-negative)
        :param max_sleep: Maximum sleep time in seconds (non-negative)
        :param force_delete: True if force_delete should be used
        :param confirm: True if need to confirm resize else revert resize
        :param do_delete: True if resources needs to be deleted explicitly
                        else use rally cleanup to remove resources
        :param boot_server_kwargs: optional arguments for VM creation
        :param create_volume_kwargs: optional arguments for volume creation
        """
        boot_server_kwargs = boot_server_kwargs or {}
        create_volume_kwargs = create_volume_kwargs or {}

        server = self._boot_server(image, flavor, **boot_server_kwargs)
        volume = self._create_volume(volume_size, **create_volume_kwargs)

        attachment = self._attach_volume(server, volume)
        self.sleep_between(min_sleep, max_sleep)
        self._resize(server, to_flavor)

        if confirm:
            self._resize_confirm(server)
        else:
            self._resize_revert(server)

        if do_delete:
            self._detach_volume(server, volume, attachment)
            self._delete_volume(volume)
            self._delete_server(server, force=force_delete)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"},
               to_flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image", validate_disk=False)
@validation.required_services(consts.Service.NOVA, consts.Service.CINDER)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["nova", "cinder"]},
                    name="NovaServers.boot_server_from_volume_and_resize")
class BootServerFromVolumeAndResize(utils.NovaScenario,
                                    cinder_utils.CinderScenario):

    def run(self, image, flavor, to_flavor, volume_size, min_sleep=0,
            max_sleep=0, force_delete=False, confirm=True, do_delete=True,
            boot_server_kwargs=None, create_volume_kwargs=None):
        """Boot a server from volume, then resize and delete it.

        The scenario first creates a volume and then a server.
        Optional 'min_sleep' and 'max_sleep' parameters allow the scenario
        to simulate a pause between volume creation and deletion
        (of random duration from [min_sleep, max_sleep]).

        This test will confirm the resize by default,
        or revert the resize if confirm is set to false.

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param to_flavor: flavor to be used to resize the booted instance
        :param volume_size: volume size (in GB)
        :param min_sleep: Minimum sleep time in seconds (non-negative)
        :param max_sleep: Maximum sleep time in seconds (non-negative)
        :param force_delete: True if force_delete should be used
        :param confirm: True if need to confirm resize else revert resize
        :param do_delete: True if resources needs to be deleted explicitly
                        else use rally cleanup to remove resources
        :param boot_server_kwargs: optional arguments for VM creation
        :param create_volume_kwargs: optional arguments for volume creation
        """
        boot_server_kwargs = boot_server_kwargs or {}
        create_volume_kwargs = create_volume_kwargs or {}

        if boot_server_kwargs.get("block_device_mapping"):
            LOG.warning("Using already existing volume is not permitted.")

        volume = self._create_volume(volume_size, imageRef=image,
                                     **create_volume_kwargs)
        boot_server_kwargs["block_device_mapping"] = {
            "vda": "%s:::1" % volume.id}

        server = self._boot_server(None, flavor, **boot_server_kwargs)
        self.sleep_between(min_sleep, max_sleep)
        self._resize(server, to_flavor)

        if confirm:
            self._resize_confirm(server)
        else:
            self._resize_revert(server)

        if do_delete:
            self._delete_server(server, force=force_delete)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image")
@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["nova"]},
                    name="NovaServers.suspend_and_resume_server")
class SuspendAndResumeServer(utils.NovaScenario, cinder_utils.CinderScenario):

    def run(self, image, flavor, force_delete=False, **kwargs):
        """Create a server, suspend, resume and then delete it

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param force_delete: True if force_delete should be used
        :param kwargs: Optional additional arguments for server creation
        """
        server = self._boot_server(image, flavor, **kwargs)
        self._suspend_server(server)
        self._resume_server(server)
        self._delete_server(server, force=force_delete)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image")
@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["nova"]},
                    name="NovaServers.pause_and_unpause_server")
class PauseAndUnpauseServer(utils.NovaScenario,
                            cinder_utils.CinderScenario):

    def run(self, image, flavor, force_delete=False, **kwargs):
        """Create a server, pause, unpause and then delete it

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param force_delete: True if force_delete should be used
        :param kwargs: Optional additional arguments for server creation
        """
        server = self._boot_server(image, flavor, **kwargs)
        self._pause_server(server)
        self._unpause_server(server)
        self._delete_server(server, force=force_delete)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image")
@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["nova"]},
                    name="NovaServers.shelve_and_unshelve_server")
class ShelveAndUnshelveServer(utils.NovaScenario,
                              cinder_utils.CinderScenario):

    def run(self, image, flavor, force_delete=False, **kwargs):
        """Create a server, shelve, unshelve and then delete it

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param force_delete: True if force_delete should be used
        :param kwargs: Optional additional arguments for server creation
        """
        server = self._boot_server(image, flavor, **kwargs)
        self._shelve_server(server)
        self._unshelve_server(server)
        self._delete_server(server, force=force_delete)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image")
@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(admin=True, users=True)
@scenario.configure(context={"cleanup": ["nova"]},
                    name="NovaServers.boot_and_live_migrate_server")
class BootAndLiveMigrateServer(utils.NovaScenario,
                               cinder_utils.CinderScenario):

    def run(self, image, flavor, block_migration=False, disk_over_commit=False,
            min_sleep=0, max_sleep=0, **kwargs):
        """Live Migrate a server.

        This scenario launches a VM on a compute node available in
        the availability zone and then migrates the VM to another
        compute node on the same availability zone.

        Optional 'min_sleep' and 'max_sleep' parameters allow the scenario
        to simulate a pause between VM booting and running live migration
        (of random duration from range [min_sleep, max_sleep]).

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param block_migration: Specifies the migration type
        :param disk_over_commit: Specifies whether to allow overcommit
                                 on migrated instance or not
        :param min_sleep: Minimum sleep time in seconds (non-negative)
        :param max_sleep: Maximum sleep time in seconds (non-negative)
        :param kwargs: Optional additional arguments for server creation
        """
        server = self._boot_server(image, flavor, **kwargs)
        self.sleep_between(min_sleep, max_sleep)

        new_host = self._find_host_to_migrate(server)
        self._live_migrate(server, new_host,
                           block_migration, disk_over_commit)

        self._delete_server(server)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image", validate_disk=False)
@validation.required_services(consts.Service.NOVA, consts.Service.CINDER)
@validation.required_openstack(admin=True, users=True)
@scenario.configure(context={"cleanup": ["nova", "cinder"]},
                    name=("NovaServers.boot_server_from_volume"
                          "_and_live_migrate"))
class BootServerFromVolumeAndLiveMigrate(utils.NovaScenario,
                                         cinder_utils.CinderScenario):

    def run(self, image, flavor, volume_size, volume_type=None,
            block_migration=False, disk_over_commit=False, force_delete=False,
            min_sleep=0, max_sleep=0, **kwargs):
        """Boot a server from volume and then migrate it.

        The scenario first creates a volume and a server booted from
        the volume on a compute node available in the availability zone and
        then migrates the VM to another compute node on the same availability
        zone.

        Optional 'min_sleep' and 'max_sleep' parameters allow the scenario
        to simulate a pause between VM booting and running live migration
        (of random duration from range [min_sleep, max_sleep]).

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param volume_size: volume size (in GB)
        :param volume_type: specifies volume type when there are
                            multiple backends
        :param block_migration: Specifies the migration type
        :param disk_over_commit: Specifies whether to allow overcommit
                                 on migrated instance or not
        :param force_delete: True if force_delete should be used
        :param min_sleep: Minimum sleep time in seconds (non-negative)
        :param max_sleep: Maximum sleep time in seconds (non-negative)
        :param kwargs: Optional additional arguments for server creation
        """
        volume = self._create_volume(volume_size, imageRef=image,
                                     volume_type=volume_type)
        block_device_mapping = {"vda": "%s:::1" % volume.id}
        server = self._boot_server(None, flavor,
                                   block_device_mapping=block_device_mapping,
                                   **kwargs)
        self.sleep_between(min_sleep, max_sleep)

        new_host = self._find_host_to_migrate(server)
        self._live_migrate(server, new_host,
                           block_migration, disk_over_commit)

        self._delete_server(server, force=force_delete)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image")
@validation.required_services(consts.Service.NOVA, consts.Service.CINDER)
@validation.required_openstack(admin=True, users=True)
@scenario.configure(context={"cleanup": ["cinder", "nova"]},
                    name=("NovaServers.boot_server_attach_created_volume"
                          "_and_live_migrate"))
class BootServerAttachCreatedVolumeAndLiveMigrate(utils.NovaScenario,
                                                  cinder_utils.CinderScenario):

    def run(self, image, flavor, size, block_migration=False,
            disk_over_commit=False, boot_server_kwargs=None,
            create_volume_kwargs=None, min_sleep=0, max_sleep=0):
        """Create a VM, attach a volume to it and live migrate.

        Simple test to create a VM and attach a volume, then migrate the VM,
        detach the volume and delete volume/VM.

        Optional 'min_sleep' and 'max_sleep' parameters allow the scenario
        to simulate a pause between attaching a volume and running live
        migration (of random duration from range [min_sleep, max_sleep]).

        :param image: Glance image name to use for the VM
        :param flavor: VM flavor name
        :param size: volume size (in GB)
        :param block_migration: Specifies the migration type
        :param disk_over_commit: Specifies whether to allow overcommit
                                 on migrated instance or not
        :param boot_server_kwargs: optional arguments for VM creation
        :param create_volume_kwargs: optional arguments for volume creation
        :param min_sleep: Minimum sleep time in seconds (non-negative)
        :param max_sleep: Maximum sleep time in seconds (non-negative)
        """

        if boot_server_kwargs is None:
            boot_server_kwargs = {}
        if create_volume_kwargs is None:
            create_volume_kwargs = {}

        server = self._boot_server(image, flavor, **boot_server_kwargs)
        volume = self._create_volume(size, **create_volume_kwargs)

        attachment = self._attach_volume(server, volume)

        self.sleep_between(min_sleep, max_sleep)

        new_host = self._find_host_to_migrate(server)
        self._live_migrate(server, new_host,
                           block_migration, disk_over_commit)

        self._detach_volume(server, volume, attachment)

        self._delete_volume(volume)
        self._delete_server(server)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image")
@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(admin=True, users=True)
@scenario.configure(context={"cleanup": ["nova"]},
                    name="NovaServers.boot_and_migrate_server")
class BootAndMigrateServer(utils.NovaScenario, cinder_utils.CinderScenario):

    def run(self, image, flavor, **kwargs):
        """Migrate a server.

        This scenario launches a VM on a compute node available in
        the availability zone, and then migrates the VM
        to another compute node on the same availability zone.

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param kwargs: Optional additional arguments for server creation
        """
        server = self._boot_server(image, flavor, **kwargs)
        self._migrate(server)
        # NOTE(wtakase): This is required because cold migration and resize
        #                share same code path.
        confirm = kwargs.get("confirm", True)
        if confirm:
            self._resize_confirm(server, status="ACTIVE")
        else:
            self._resize_revert(server, status="ACTIVE")
        self._delete_server(server)


@types.convert(from_image={"type": "glance_image"},
               to_image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "from_image")
@validation.image_valid_on_flavor("flavor", "to_image")
@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(admin=True, users=True)
@scenario.configure(context={"cleanup": ["nova"]},
                    name="NovaServers.boot_and_rebuild_server")
class BootAndRebuildServer(utils.NovaScenario, cinder_utils.CinderScenario):

    def run(self, from_image, to_image, flavor, **kwargs):
        """Rebuild a server.

        This scenario launches a VM, then rebuilds that VM with a
        different image.

        :param from_image: image to be used to boot an instance
        :param to_image: image to be used to rebuild the instance
        :param flavor: flavor to be used to boot an instance
        :param kwargs: Optional additional arguments for server creation
        """
        server = self._boot_server(from_image, flavor, **kwargs)
        self._rebuild_server(server, to_image)
        self._delete_server(server)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image")
@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(users=True)
@validation.required_contexts("network")
@scenario.configure(context={"cleanup": ["nova"]},
                    name="NovaServers.boot_and_associate_floating_ip")
class BootAndAssociateFloatingIp(utils.NovaScenario,
                                 cinder_utils.CinderScenario):

    def run(self, image, flavor, **kwargs):
        """Boot a server and associate a floating IP to it.

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param kwargs: Optional additional arguments for server creation
        """
        server = self._boot_server(image, flavor, **kwargs)
        address = network_wrapper.wrap(self.clients, self).create_floating_ip(
            tenant_id=server.tenant_id)
        self._associate_floating_ip(server, address["ip"])


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image")
@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["nova"]},
                    name="NovaServers.boot_and_show_server")
class BootAndShowServer(utils.NovaScenario, cinder_utils.CinderScenario):

    def run(self, image, flavor, **kwargs):
        """Show server details.

        This simple scenario tests the nova show command by retrieving
        the server details.
        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param kwargs: Optional additional arguments for server creation

        :returns: Server details
        """
        server = self._boot_server(image, flavor, **kwargs)
        self._show_server(server)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image")
@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["nova"]},
                    name="NovaServers.boot_and_get_console_output")
class BootAndGetConsoleOutput(utils.NovaScenario, cinder_utils.CinderScenario):

    def run(self, image, flavor, length=None, **kwargs):
        """Get text console output from server.

        This simple scenario tests the nova console-log command by retrieving
        the text console log output.
        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param length: The number of tail log lines you would like to retrieve.
                       None (default value) or -1 means unlimited length.
        :param kwargs: Optional additional arguments for server creation

        :returns: Text console log output for server
        """
        server = self._boot_server(image, flavor, **kwargs)
        self._get_server_console_output(server, length)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image")
@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["nova"]},
                    name="NovaServers.boot_and_update_server")
class BootAndUpdateServer(utils.NovaScenario, cinder_utils.CinderScenario):

    def run(self, image, flavor, description=None, **kwargs):
        """Boot a server, then update its name and description.

        The scenario first creates a server, then update it.
        Assumes that cleanup is done elsewhere.

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param description: update the server description
        :param kwargs: Optional additional arguments for server creation
        """
        server = self._boot_server(image, flavor, **kwargs)
        self._update_server(server, description)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image")
@validation.required_services(consts.Service.NOVA, consts.Service.CINDER)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["nova", "cinder"]},
                    name="NovaServers.boot_server_from_volume_snapshot")
class BootServerFromVolumeSnapshot(utils.NovaScenario,
                                   cinder_utils.CinderScenario):

    def run(self, image, flavor, volume_size, volume_type=None,
            auto_assign_nic=False, **kwargs):
        """Boot a server from a snapshot.

        The scenario first creates a volume and creates a
        snapshot from this volume, then boots a server from
        the created snapshot.
        Assumes that cleanup is done elsewhere.

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param volume_size: volume size (in GB)
        :param volume_type: specifies volume type when there are
                            multiple backends
        :param auto_assign_nic: True if NICs should be assigned
        :param kwargs: Optional additional arguments for server creation
        """
        volume = self._create_volume(volume_size, imageRef=image,
                                     volume_type=volume_type)
        snapshot = self._create_snapshot(volume.id, False)
        block_device_mapping = {"vda": "%s:snap::1" % snapshot.id}
        self._boot_server(None, flavor, auto_assign_nic=auto_assign_nic,
                          block_device_mapping=block_device_mapping,
                          **kwargs)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image")
@validation.required_services(consts.Service.NOVA)
@validation.required_openstack(users=True)
@validation.required_contexts("network")
@scenario.configure(context={"cleanup": ["nova"]},
                    name="NovaServers.boot_server_associate_and"
                         "_dissociate_floating_ip")
class BootServerAssociateAndDissociateFloatingIP(utils.NovaScenario):
    """"Benchmark scenarios for Nova FloatingIp API."""
    def run(self, image, flavor, **kwargs):
        """Boot a server associate and dissociate a floating IP from it.

        The scenario first boot a server and create a floating IP. then
        associate the floating IP to the server.Finally dissociate the floating
        IP.

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param kwargs: Optional additional arguments for server creation
        """
        server = self._boot_server(image, flavor, **kwargs)
        address = network_wrapper.wrap(self.clients, self).create_floating_ip(
            tenant_id=server.tenant_id)
        self._associate_floating_ip(server, address["ip"])
        self._dissociate_floating_ip(server, address["ip"])
