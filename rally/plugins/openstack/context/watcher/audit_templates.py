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

import random

import six

from rally.common.i18n import _
from rally.common import logging
from rally import consts
from rally import osclients
from rally.plugins.openstack.cleanup import manager as resource_manager
from rally.plugins.openstack.scenarios.watcher import utils as watcher_utils
from rally.plugins.openstack import types
from rally.task import context


LOG = logging.getLogger(__name__)


@context.configure(name="audit_templates", order=550)
class AuditTemplateGenerator(context.Context):
    """Context class for adding temporary audit template for benchmarks."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "fill_strategy": {"enum": ["round_robin", "random", None]},
        "params": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": {
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string"
                            }
                        }
                    },
                    "strategy": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string"
                            }
                        }
                    },
                },
            },
        },
        "additionalProperties": True,
        "required": ["params"]
    }

    DEFAULT_CONFIG = {
        "audit_templates_per_admin": 1,
        "fill_strategy": "round_robin"
    }

    @logging.log_task_wrapper(LOG.info, _("Enter context: `Audit Templates`"))
    def setup(self):
        watcher_scenario = watcher_utils.WatcherScenario(
            {"admin": self.context["admin"], "task": self.context["task"],
             "config": {
                 "api_versions": self.context["config"].get(
                     "api_versions", [])}
             })

        clients = osclients.Clients(self.context["admin"]["credential"])

        self.context["audit_templates"] = []
        for i in six.moves.range(self.config["audit_templates_per_admin"]):
            cfg_size = len(self.config["params"])
            if self.config["fill_strategy"] == "round_robin":
                audit_params = self.config["params"][i % cfg_size]
            elif self.config["fill_strategy"] == "random":
                audit_params = random.choice(self.config["params"])

            goal_id = types.WatcherGoal.transform(
                clients=clients,
                resource_config=audit_params["goal"])
            strategy_id = types.WatcherStrategy.transform(
                clients=clients,
                resource_config=audit_params["strategy"])

            audit_template = watcher_scenario._create_audit_template(
                goal_id, strategy_id)
            self.context["audit_templates"].append(audit_template.uuid)

    @logging.log_task_wrapper(LOG.info, _("Exit context: `Audit Templates`"))
    def cleanup(self):
        resource_manager.cleanup(names=["watcher.action_plan",
                                        "watcher.audit_template"],
                                 admin=self.context.get("admin", []))
