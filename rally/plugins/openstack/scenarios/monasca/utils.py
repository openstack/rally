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
import time
import uuid

from oslo_config import cfg

from rally.plugins.openstack import scenario
from rally.task import atomic


MONASCA_BENCHMARK_OPTS = [
    cfg.FloatOpt(
        "monasca_metric_create_prepoll_delay",
        default=15.0,
        help="Delay between creating Monasca metrics and polling for "
             "its elements.")
]

CONF = cfg.CONF
benchmark_group = cfg.OptGroup(name="benchmark", title="benchmark options")
CONF.register_opts(MONASCA_BENCHMARK_OPTS, group=benchmark_group)


class MonascaScenario(scenario.OpenStackScenario):
    """Base class for Monasca scenarios with basic atomic actions."""

    @atomic.action_timer("monasca.list_metrics")
    def _list_metrics(self, **kwargs):
        """Get list of user's metrics.

        :param kwargs: optional arguments for list query:
                       name, dimensions, start_time, etc
        :returns list of monasca metrics
        """
        return self.clients("monasca").metrics.list(**kwargs)

    @atomic.action_timer("monasca.create_metrics")
    def _create_metrics(self, **kwargs):
        """Create user metrics.

        :param kwargs: attributes for metric creation:
                       name, dimension, timestamp, value, etc
        """
        timestamp = int(time.time() * 1000)
        kwargs.update({"name": self.generate_random_name(),
                       "timestamp": timestamp,
                       "value": random.random(),
                       "value_meta": {
                           "key": str(uuid.uuid4())[:10]}})
        self.clients("monasca").metrics.create(**kwargs)
