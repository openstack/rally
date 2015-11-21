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

from six import moves

from rally.common.i18n import _
from rally.common import logging
from rally.common import utils as rutils
from rally import consts
from rally.plugins.openstack.scenarios.monasca import utils as monasca_utils
from rally.task import context


LOG = logging.getLogger(__name__)


@context.configure(name="monasca_metrics", order=510)
class MonascaMetricGenerator(context.Context):
    """Context for creating metrics  for benchmarks."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "name": {
                "type": "string"
            },
            "dimensions": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string"
                    },
                    "service": {
                        "type": "string"
                    },
                    "hostname": {
                        "type": "string"
                    },
                    "url": {
                        "type": "string"
                    }
                }
            },
            "metrics_per_tenant": {
                "type": "integer",
                "minimum": 1
            },
            "value_meta": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "value_meta_key": {
                            "type": "string"
                        },
                        "value_meta_value": {
                            "type": "string"
                        }
                    }
                }
            }
        },
        "additionalProperties": False
    }

    DEFAULT_CONFIG = {
        "metrics_per_tenant": 2
    }

    @logging.log_task_wrapper(LOG.info, _("Enter context: `Monasca`"))
    def setup(self):
        new_metric = {}

        if "dimensions" in self.config:
            new_metric = {
                "dimensions": self.config["dimensions"]
            }

        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):
            scenario = monasca_utils.MonascaScenario(
                context={"user": user, "task": self.context["task"]}
            )
            for i in moves.xrange(self.config["metrics_per_tenant"]):
                scenario._create_metrics(**new_metric)
                rutils.interruptable_sleep(0.001)
        rutils.interruptable_sleep(
            monasca_utils.CONF.benchmark.monasca_metric_create_prepoll_delay,
            atomic_delay=1)

    @logging.log_task_wrapper(LOG.info, _("Exit context: `Monasca`"))
    def cleanup(self):
        # We don't have API for removal of metrics
        pass
