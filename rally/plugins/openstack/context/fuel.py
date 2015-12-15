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

import collections

from rally.common import broker
from rally.common.i18n import _
from rally.common import logging
from rally import consts
from rally import exceptions
from rally.plugins.openstack.scenarios.fuel import utils as fuel_utils
from rally.task import context as base

LOG = logging.getLogger(__name__)


@base.configure(name="fuel_environments", order=110)
class FuelEnvGenerator(base.Context):
    """Context for generating Fuel environments."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "environments": {
                "type": "integer",
                "minimum": 1
            },
            "release_id": {
                "type": "integer"
            },
            "network_provider": {
                "type": "string"
            },
            "net_segment_type": {
                "type": "string"
            },
            "deployment_mode": {
                "type": "string"
            },
            "resource_management_workers": {
                "type": "integer",
                "minimum": 1
            },
        },
        "additionalProperties": False
    }

    DEFAULT_CONFIG = {
        "environments": 5,
        "release_id": 1,
        "network_provider": "neutron",
        "deployment_mode": "ha_compact",
        "net_segment_type": "vlan",
        "resource_management_workers": 2
    }

    def _create_envs(self):
        threads = self.config["resource_management_workers"]

        envs = collections.deque()

        def publish(queue):
            kwargs = {"release_id": self.config["release_id"],
                      "network_provider": self.config["network_provider"],
                      "deployment_mode": self.config["deployment_mode"],
                      "net_segment_type": self.config["net_segment_type"]}

            for i in range(self.config["environments"]):
                queue.append(kwargs)

        def consume(cache, kwargs):
            env_id = self.fscenario._create_environment(**kwargs)
            envs.append(env_id)

        broker.run(publish, consume, threads)

        return list(envs)

    def _delete_envs(self):
        threads = self.config["resource_management_workers"]

        def publish(queue):
            queue.extend(self.context["fuel"]["environments"])

        def consume(cache, env_id):
            self.fscenario._delete_environment(env_id)

        broker.run(publish, consume, threads)
        self.context["fuel"] = {}

    @logging.log_task_wrapper(LOG.info,
                              _("Enter context: `fuel_environments`"))
    def setup(self):
        """Create Fuel environments, using the broker pattern."""

        self.context.setdefault("fuel", {})
        self.context["fuel"].setdefault("environments", [])
        threads = self.config["resource_management_workers"]

        LOG.debug("Creating %(envs)d environments using %(threads)s threads" %
                  {"envs": self.config["environments"],
                   "threads": threads})
        self.fscenario = fuel_utils.FuelScenario(self.context)
        self.context["fuel"]["environments"] = self._create_envs()

        if len(self.context[
                "fuel"]["environments"]) != self.config["environments"]:
            raise exceptions.ContextSetupFailure(
                ctx_name=self.get_name(),
                msg=_("failed to create the requested"
                      " number of environments."))

    @logging.log_task_wrapper(LOG.info, _("Exit context: `fuel_environments`"))
    def cleanup(self):
        """Delete environments, using the broker pattern."""
        self._delete_envs()
