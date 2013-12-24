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

import json
import jsonschema
import random

from rally.benchmark.scenarios.cinder import utils as cinder_utils
from rally.benchmark.scenarios.nova import utils
from rally.benchmark.scenarios import utils as scenario_utils
from rally.benchmark import utils as benchmark_utils
from rally import exceptions as rally_exceptions
from rally.openstack.common.gettextutils import _  # noqa
from rally.openstack.common import log as logging
from rally import sshutils

LOG = logging.getLogger(__name__)

ACTION_BUILDER = scenario_utils.ActionBuilder(
        ['hard_reboot', 'soft_reboot', 'stop_start', 'rescue_unrescue'])


class NovaServers(utils.NovaScenario,
                  cinder_utils.CinderScenario):

    @classmethod
    def boot_and_delete_server(cls, image_id, flavor_id,
                               min_sleep=0, max_sleep=0, **kwargs):
        """Tests booting and then deleting an image."""
        server_name = cls._generate_random_name(16)

        server = cls._boot_server(server_name, image_id, flavor_id, **kwargs)
        cls.sleep_between(min_sleep, max_sleep)
        cls._delete_server(server)

    @classmethod
    def boot_server_from_volume_and_delete(cls, image_id, flavor_id,
                                           volume_size,
                                           min_sleep=0, max_sleep=0, **kwargs):
        """Tests booting from volume and then deleting an image and volume."""
        server_name = cls._generate_random_name(16)

        volume = cls._create_volume(volume_size, imageRef=image_id)
        block_device_mapping = {'vda': '%s:::1' % volume.id}
        server = cls._boot_server(server_name, image_id, flavor_id,
                                  block_device_mapping=block_device_mapping,
                                  **kwargs)
        cls.sleep_between(min_sleep, max_sleep)
        cls._delete_server(server)

    @classmethod
    def boot_runcommand_delete_server(cls, image_id, flavor_id,
                                      script, interpreter, network='private',
                                      username='ubuntu', ip_version=4,
                                      retries=60, port=22, **kwargs):
        """Boot server, run a script that outputs JSON, delete server.

        Parameters:
        script: script to run on the server, must output JSON mapping metric
                names to values. See sample script below.
        network: Network to choose address to connect to instance from
        username: User to SSH to instance as
        ip_version: Version of ip protocol to use for connection

        returns: Dictionary containing two keys, data and errors. Data is JSON
                 data output by the script. Errors is raw data from the
                 script's standard error stream.


        Example Script in doc/samples/support/instance_dd_test.sh
        """
        server_name = cls._generate_random_name(16)

        server = cls._boot_server(server_name, image_id, flavor_id,
                                  key_name='rally_ssh_key', **kwargs)

        if network not in server.addresses:
            raise ValueError(
                "Can't find cloud network %(network)s, so cannot boot "
                "instance for Rally scenario boot-runcommand-delete. "
                "Available networks: %(networks)s" % (
                    dict(network=network,
                         networks=server.addresses.keys()
                         )
                )
            )
        server_ip = [ip for ip in server.addresses[network] if
                     ip['version'] == ip_version][0]['addr']
        ssh = sshutils.SSH(ip=server_ip, port=port, user=username,
                           key=cls.clients('ssh_key_pair')['private'],
                           key_type='string')

        for retry in range(retries):
            try:
                LOG.debug(_('Execute script on server attempt '
                            '%(retry)i/%(retries)i') % dict(retry=retry,
                                                            retries=retries))
                streams = list(ssh.execute_script(script=script,
                                                  interpreter=interpreter,
                                                  get_stdout=True,
                                                  get_stderr=True))

                #NOTE(hughsaunders): Decode JSON script output
                streams[sshutils.SSH.STDOUT_INDEX]\
                    = json.loads(streams[sshutils.SSH.STDOUT_INDEX])
                break
            except (rally_exceptions.SSHError,
                    rally_exceptions.TimeoutException, IOError) as e:
                LOG.debug(_('Error running script on instance via SSH. '
                            '%(id)s/%(ip)s Attempt:%(retry)i, '
                            'Error: %(error)s') % dict(
                                id=server.id, ip=server_ip, retry=retry,
                                error=benchmark_utils.format_exc(e)))
                cls.sleep_between(5, 5)
            except ValueError:
                LOG.error(_('Script %(script)s did not output valid JSON. ')
                          % dict(script=script))

        cls._delete_server(server)
        LOG.debug(_('Output streams from in-instance script execution: '
                    'stdout: %(stdout)s, stderr: $(stderr)s') % dict(
                        stdout=str(streams[sshutils.SSH.STDOUT_INDEX]),
                        stderr=str(streams[sshutils.SSH.STDERR_INDEX])))
        return dict(data=streams[sshutils.SSH.STDOUT_INDEX],
                    errors=streams[sshutils.SSH.STDERR_INDEX])

    @classmethod
    def boot_and_bounce_server(cls, image_id, flavor_id, **kwargs):
        """Tests booting a server then performing stop/start or hard/soft
        reboot a number of times.
        """
        actions = kwargs.get('actions', [])
        try:
            ACTION_BUILDER.validate(actions)
        except jsonschema.exceptions.ValidationError as error:
            raise rally_exceptions.InvalidConfigException(
                "Invalid server actions configuration \'%(actions)s\' due to: "
                "%(error)s" % {'actions': str(actions), 'error': str(error)})
        server = cls._boot_server(cls._generate_random_name(16),
                                  image_id, flavor_id, **kwargs)
        for action in ACTION_BUILDER.build_actions(actions, server):
            action()
        cls._delete_server(server)

    @classmethod
    def snapshot_server(cls, image_id, flavor_id, **kwargs):
        """Tests Nova instance snapshotting."""
        server_name = cls._generate_random_name(16)

        server = cls._boot_server(server_name, image_id, flavor_id, **kwargs)
        image = cls._create_image(server)
        cls._delete_server(server)

        server = cls._boot_server(server_name, image.id, flavor_id, **kwargs)
        cls._delete_server(server)
        cls._delete_image(image)

    @classmethod
    def boot_server(cls, image_id, flavor_id, **kwargs):
        """Test VM boot - assumed clean-up is done elsewhere."""
        server_name = cls._generate_random_name(16)
        if 'nics' not in kwargs:
            nets = cls.clients("nova").networks.list()
            if nets:
                random_nic = random.choice(nets)
                kwargs['nics'] = [{'net-id': random_nic.id}]
        cls._boot_server(server_name, image_id, flavor_id, **kwargs)

    @classmethod
    def boot_server_from_volume(cls, image_id, flavor_id,
                                volume_size, **kwargs):
        """Test VM boot from volume - assumed clean-up is done elsewhere."""
        server_name = cls._generate_random_name(16)
        if 'nics' not in kwargs:
            nets = cls.clients("nova").networks.list()
            if nets:
                random_nic = random.choice(nets)
                kwargs['nics'] = [{'net-id': random_nic.id}]
        volume = cls._create_volume(volume_size, imageRef=image_id)
        block_device_mapping = {'vda': '%s:::1' % volume.id}
        cls._boot_server(server_name, image_id, flavor_id,
                         block_device_mapping=block_device_mapping,
                         **kwargs)

    @classmethod
    def _stop_and_start_server(cls, server):
        """Stop and then start the given server.

        A stop will be issued on the given server upon which time
        this method will wait for the server to become 'SHUTOFF'.
        Once the server is SHUTOFF a start will be issued and this
        method will wait for the server to become 'ACTIVE' again.

        :param server: The server to stop and then start.

        """
        cls._stop_server(server)
        cls._start_server(server)

    @classmethod
    def _rescue_and_unrescue_server(cls, server):
        """Rescue and then unrescue the given server.
        A rescue will be issued on the given server upon which time
        this method will wait for the server to become 'RESCUE'.
        Once the server is RESCUE a unrescue will be issued and
        this method will wait for the server to become 'ACTIVE'
        again.

        :param server: The server to rescue and then unrescue.

        """
        cls._rescue_server(server)
        cls._unrescue_server(server)


ACTION_BUILDER.bind_action('hard_reboot',
                           utils.NovaScenario._reboot_server, soft=False)
ACTION_BUILDER.bind_action('soft_reboot',
                           utils.NovaScenario._reboot_server, soft=True)
ACTION_BUILDER.bind_action('stop_start',
                           NovaServers._stop_and_start_server)
ACTION_BUILDER.bind_action('rescue_unrescue',
                           NovaServers._rescue_and_unrescue_server)
