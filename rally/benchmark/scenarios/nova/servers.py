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


class NovaServers(utils.NovaScenario,
                  cinder_utils.CinderScenario):

    def __init__(self, *args, **kwargs):
        super(NovaServers, self).__init__(*args, **kwargs)

    def boot_and_delete_server(self, image_id, flavor_id,
                               min_sleep=0, max_sleep=0, **kwargs):
        """Tests booting and then deleting an image."""
        server_name = self._generate_random_name(16)

        server = self._boot_server(server_name, image_id, flavor_id, **kwargs)
        self.sleep_between(min_sleep, max_sleep)
        self._delete_server(server)

    def boot_server_from_volume_and_delete(self, image_id, flavor_id,
                                           volume_size,
                                           min_sleep=0, max_sleep=0, **kwargs):
        """Tests booting from volume and then deleting an image and volume."""
        server_name = self._generate_random_name(16)

        volume = self._create_volume(volume_size, imageRef=image_id)
        block_device_mapping = {'vda': '%s:::1' % volume.id}
        server = self._boot_server(server_name, image_id, flavor_id,
                                   block_device_mapping=block_device_mapping,
                                   **kwargs)
        self.sleep_between(min_sleep, max_sleep)
        self._delete_server(server)

    def boot_runcommand_delete_server(self, image_id, flavor_id,
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
        server_name = self._generate_random_name(16)

        server = self._boot_server(server_name, image_id, flavor_id,
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
                           key=self.clients('ssh_key_pair')['private'],
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
                self.sleep_between(5, 5)
            except ValueError:
                LOG.error(_('Script %(script)s did not output valid JSON. ')
                          % dict(script=script))

        self._delete_server(server)
        LOG.debug(_('Output streams from in-instance script execution: '
                    'stdout: %(stdout)s, stderr: $(stderr)s') % dict(
                        stdout=str(streams[sshutils.SSH.STDOUT_INDEX]),
                        stderr=str(streams[sshutils.SSH.STDERR_INDEX])))
        return dict(data=streams[sshutils.SSH.STDOUT_INDEX],
                    errors=streams[sshutils.SSH.STDERR_INDEX])

    def boot_and_bounce_server(self, image_id, flavor_id, **kwargs):
        """Tests booting a server then performing stop/start or hard/soft
        reboot a number of times.
        """
        action_builder = self._bind_actions()
        actions = kwargs.get('actions', [])
        try:
            action_builder.validate(actions)
        except jsonschema.exceptions.ValidationError as error:
            raise rally_exceptions.InvalidConfigException(
                "Invalid server actions configuration \'%(actions)s\' due to: "
                "%(error)s" % {'actions': str(actions), 'error': str(error)})
        server = self._boot_server(self._generate_random_name(16),
                                   image_id, flavor_id, **kwargs)
        for action in action_builder.build_actions(actions, server):
            action()
        self._delete_server(server)

    def snapshot_server(self, image_id, flavor_id, **kwargs):
        """Tests Nova instance snapshotting."""
        server_name = self._generate_random_name(16)

        server = self._boot_server(server_name, image_id, flavor_id, **kwargs)
        image = self._create_image(server)
        self._delete_server(server)

        server = self._boot_server(server_name, image.id, flavor_id, **kwargs)
        self._delete_server(server)
        self._delete_image(image)

    def boot_server(self, image_id, flavor_id, **kwargs):
        """Test VM boot - assumed clean-up is done elsewhere."""
        server_name = self._generate_random_name(16)
        if 'nics' not in kwargs:
            nets = self.clients("nova").networks.list()
            if nets:
                random_nic = random.choice(nets)
                kwargs['nics'] = [{'net-id': random_nic.id}]
        self._boot_server(server_name, image_id, flavor_id, **kwargs)

    def boot_server_from_volume(self, image_id, flavor_id,
                                volume_size, **kwargs):
        """Test VM boot from volume - assumed clean-up is done elsewhere."""
        server_name = self._generate_random_name(16)
        if 'nics' not in kwargs:
            nets = self.clients("nova").networks.list()
            if nets:
                random_nic = random.choice(nets)
                kwargs['nics'] = [{'net-id': random_nic.id}]
        volume = self._create_volume(volume_size, imageRef=image_id)
        block_device_mapping = {'vda': '%s:::1' % volume.id}
        self._boot_server(server_name, image_id, flavor_id,
                          block_device_mapping=block_device_mapping,
                          **kwargs)

    def _bind_actions(self):
        actions = ['hard_reboot', 'soft_reboot', 'stop_start',
                   'rescue_unrescue']
        action_builder = scenario_utils.ActionBuilder(actions)
        action_builder.bind_action('hard_reboot', self._reboot_server,
                                   soft=False)
        action_builder.bind_action('soft_reboot', self._reboot_server,
                                   soft=True)
        action_builder.bind_action('stop_start',
                                   self._stop_and_start_server)
        action_builder.bind_action('rescue_unrescue',
                                   self._rescue_and_unrescue_server)
        return action_builder

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

    def _rescue_and_unrescue_server(self, server):
        """Rescue and then unrescue the given server.
        A rescue will be issued on the given server upon which time
        this method will wait for the server to become 'RESCUE'.
        Once the server is RESCUE a unrescue will be issued and
        this method will wait for the server to become 'ACTIVE'
        again.

        :param server: The server to rescue and then unrescue.

        """
        self._rescue_server(server)
        self._unrescue_server(server)
