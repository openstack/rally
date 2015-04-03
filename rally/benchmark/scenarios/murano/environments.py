# Copyright 2015: Mirantis Inc.
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

from rally.benchmark.scenarios import base
from rally.benchmark.scenarios.murano import utils
from rally.benchmark.scenarios.vm import utils as vm_utils
from rally.benchmark import validation
from rally.common import log as logging
from rally import consts

LOG = logging.getLogger(__name__)


class MuranoEnvironments(utils.MuranoScenario, vm_utils.VMScenario):
    """Benchmark scenarios for Murano environments."""
    @validation.required_clients("murano")
    @validation.required_services(consts.Service.MURANO)
    @base.scenario(context={"cleanup": ["murano.environments"]})
    def list_environments(self):
        """List the murano environments.

        Run murano environment-list for listing all environments.
        """
        self._list_environments()

    @validation.required_clients("murano")
    @validation.required_services(consts.Service.MURANO)
    @base.scenario(context={"cleanup": ["murano.environments"]})
    def create_and_delete_environment(self):
        """Create environment, session and delete environment."""
        environment = self._create_environment()

        self._create_session(environment.id)
        self._delete_environment(environment)
