# Copyright 2016: Mirantis Inc.
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

import os_faults

from rally.common import logging
from rally.common import objects
from rally import consts
from rally.task import hook

LOG = logging.getLogger(__name__)


@hook.configure(name="fault_injection")
class FaultInjectionHook(hook.Hook):
    """Performs fault injection using os-faults library.

    Configuration:
        action - string that represents an action (more info in [1])
        verify - whether to verify connection to cloud nodes or not

    This plugin discovers extra config of ExistingCloud
    and looks for "cloud_config" field. If cloud_config is present then
    it will be used to connect to the cloud by os-faults.

    Another option is to provide os-faults config file through
    OS_FAULTS_CONFIG env variable. Format of the config can
    be found in [1].

    [1] http://os-faults.readthedocs.io/en/latest/usage.html
    """

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "action": {"type": "string"},
            "verify": {"type": "boolean"},
        },
        "required": [
            "action",
        ],
        "additionalProperties": False,
    }

    def get_cloud_config(self):
        deployment = objects.Deployment.get(self.task["deployment_uuid"])
        deployment_config = deployment["config"]
        if deployment_config["type"] != "ExistingCloud":
            return None

        extra_config = deployment_config.get("extra", {})
        return extra_config.get("cloud_config")

    def run(self):
        # get cloud configuration
        cloud_config = self.get_cloud_config()

        # connect to the cloud
        injector = os_faults.connect(cloud_config)

        # verify that all nodes are available
        if self.config.get("verify"):
            injector.verify()

        LOG.debug("Injecting fault: %s", self.config["action"])
        os_faults.human_api(injector, self.config["action"])
