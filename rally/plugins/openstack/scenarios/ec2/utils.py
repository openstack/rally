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

from rally.plugins.openstack import scenario
from rally.task import atomic
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


class EC2Scenario(scenario.OpenStackScenario):
    """Base class for EC2 scenarios with basic atomic actions."""

    @atomic.action_timer("ec2.list_servers")
    def _list_servers(self):
        """Returns user servers list."""
        return self.clients("ec2").get_only_instances()

    @atomic.action_timer("ec2.boot_servers")
    def _boot_servers(self, image_id, flavor_name,
                      instance_num=1, **kwargs):
        """Boot multiple servers.

        Returns when all the servers are actually booted and are in the
        "Running" state.

        :param image_id: ID of the image to be used for server creation
        :param flavor_name: Name of the flavor to be used for server creation
        :param instance_num: Number of instances to boot
        :param kwargs: Other optional parameters to boot servers

        :returns: List of created server objects
        """
        reservation = self.clients("ec2").run_instances(
            image_id=image_id,
            instance_type=flavor_name,
            min_count=instance_num,
            max_count=instance_num,
            **kwargs)
        servers = [instance for instance in reservation.instances]

        time.sleep(CONF.benchmark.ec2_server_boot_prepoll_delay)
        servers = [utils.wait_for(
            server,
            ready_statuses=["RUNNING"],
            update_resource=self._update_resource,
            timeout=CONF.benchmark.ec2_server_boot_timeout,
            check_interval=CONF.benchmark.ec2_server_boot_poll_interval
        ) for server in servers]
        return servers

    def _update_resource(self, resource):
        resource.update()
        return resource
