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

from six import moves

from rally.common import logging
from rally.common import utils as rutils
from rally.common import validation
from rally import consts
from rally import exceptions
from rally.plugins.openstack.scenarios.ceilometer import utils as ceilo_utils
from rally.task import context


LOG = logging.getLogger(__name__)


@validation.add("required_platform", platform="openstack", users=True)
@context.configure(name="ceilometer", platform="openstack", order=450)
class CeilometerSampleGenerator(context.Context):
    """Creates ceilometer samples and resources."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "counter_name": {
                "type": "string"
            },
            "counter_type": {
                "type": "string"
            },
            "counter_unit": {
                "type": "string"
            },
            "counter_volume": {
                "type": "number",
                "minimum": 0
            },
            "resources_per_tenant": {
                "type": "integer",
                "minimum": 1
            },
            "samples_per_resource": {
                "type": "integer",
                "minimum": 1
            },
            "timestamp_interval": {
                "type": "integer",
                "minimum": 1
            },
            "metadata_list": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string"
                        },
                        "name": {
                            "type": "string"
                        },
                        "deleted": {
                            "type": "string"
                        },
                        "created_at": {
                            "type": "string"
                        }
                    },
                    "additionalProperties": False
                }
            },
            "batch_size": {
                "type": "integer",
                "minimum": 1
            },
            "batches_allow_lose": {
                "type": "integer",
                "minimum": 0
            }
        },
        "required": ["counter_name", "counter_type", "counter_unit",
                     "counter_volume"],
        "additionalProperties": False
    }

    DEFAULT_CONFIG = {
        "resources_per_tenant": 5,
        "samples_per_resource": 5,
        "timestamp_interval": 60
    }

    def _store_batch_samples(self, scenario, batches, batches_allow_lose):
        batches_allow_lose = batches_allow_lose or 0
        unsuccess = 0
        for i, batch in enumerate(batches, start=1):
            try:
                samples = scenario._create_samples(batch)
            except Exception:
                unsuccess += 1
                LOG.warning("Failed to store batch %d of Ceilometer samples"
                            " during context creation" % i)
        if unsuccess > batches_allow_lose:
            raise exceptions.ContextSetupFailure(
                ctx_name=self.get_name(),
                msg="Context failed to store too many batches of samples")

        return samples

    def setup(self):
        new_sample = {
            "counter_name": self.config["counter_name"],
            "counter_type": self.config["counter_type"],
            "counter_unit": self.config["counter_unit"],
            "counter_volume": self.config["counter_volume"],
        }
        resources = []

        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):
            self.context["tenants"][tenant_id]["samples"] = []
            self.context["tenants"][tenant_id]["resources"] = []
            scenario = ceilo_utils.CeilometerScenario(
                context={"user": user, "task": self.context["task"]}
            )
            for i in moves.xrange(self.config["resources_per_tenant"]):
                samples_to_create = scenario._make_samples(
                    count=self.config["samples_per_resource"],
                    interval=self.config["timestamp_interval"],
                    metadata_list=self.config.get("metadata_list"),
                    batch_size=self.config.get("batch_size"),
                    **new_sample)
                samples = self._store_batch_samples(
                    scenario, samples_to_create,
                    self.config.get("batches_allow_lose")
                )
                for sample in samples:
                    self.context["tenants"][tenant_id]["samples"].append(
                        sample.to_dict())
                self.context["tenants"][tenant_id]["resources"].append(
                    samples[0].resource_id)
                resources.append((user, samples[0].resource_id))

        # NOTE(boris-42): Context should wait until samples are processed
        from ceilometerclient import exc

        for user, resource_id in resources:
            scenario = ceilo_utils.CeilometerScenario(
                context={"user": user, "task": self.context["task"]})

            success = False
            for i in range(60):
                try:
                    scenario._get_resource(resource_id)
                    success = True
                    break
                except exc.HTTPNotFound:
                    time.sleep(3)
            if not success:
                raise exceptions.ContextSetupFailure(
                    ctx_name=self.get_name(),
                    msg="Ceilometer Resource %s is not found" % resource_id)

    def cleanup(self):
        # We don't have API for removal of samples and resources
        pass
