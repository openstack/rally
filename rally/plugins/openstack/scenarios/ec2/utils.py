# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import time

from oslo_config import cfg

from rally.task.scenarios import base
from rally.task import utils


EC2_BENCHMARK_OPTS = [
    cfg.FloatOpt(
        "ec2_server_boot_prepoll_delay",
        default=1.0,
        help="Time to sleep after boot before polling for status"
    ),
    cfg.FloatOpt(
        "ec2_server_boot_timeout",
        default=300.0,
        help="Server boot timeout"
    ),
    cfg.FloatOpt(
        "ec2_server_boot_poll_interval",
        default=1.0,
        help="Server boot poll interval"
    )
]

CONF = cfg.CONF
benchmark_group = cfg.OptGroup(name="benchmark",
                               title="benchmark options")
CONF.register_opts(EC2_BENCHMARK_OPTS, group=benchmark_group)


class EC2Scenario(base.Scenario):
    """Base class for EC2 scenarios with basic atomic actions."""

    RESOURCE_NAME_PREFIX = "rally_ec2server_"
    RESOURCE_NAME_LENGTH = 16

    @base.atomic_action_timer("ec2.boot_server")
    def _boot_server(self, image_id, flavor_name, **kwargs):
        """Boot a server.

        Returns when the server is actually booted and in "Running" state.

        :param image_id: ID of the image to be used for server creation
        :param flavor_name: Name of the flavor to be used for server creation
        :param kwargs: other optional parameters to initialize the server
        :returns: EC2 Server instance
        """
        reservation = self.clients("ec2").run_instances(
            image_id=image_id, instance_type=flavor_name, **kwargs)
        server = reservation.instances[0]

        time.sleep(CONF.benchmark.ec2_server_boot_prepoll_delay)
        server = utils.wait_for(
            server,
            is_ready=utils.resource_is("RUNNING"),
            update_resource=self._update_resource,
            timeout=CONF.benchmark.ec2_server_boot_timeout,
            check_interval=CONF.benchmark.ec2_server_boot_poll_interval
        )
        return server

    def _update_resource(self, resource):
        resource.update()
        return resource
