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

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.murano import utils
from rally.task import atomic
from rally.task import validation


"""Scenarios for Murano environments."""


@validation.required_clients("murano")
@validation.required_services(consts.Service.MURANO)
@scenario.configure(context={"cleanup": ["murano.environments"]},
                    name="MuranoEnvironments.list_environments")
class ListEnvironments(utils.MuranoScenario):

    def run(self):
        """List the murano environments.

        Run murano environment-list for listing all environments.
        """
        self._list_environments()


@validation.required_clients("murano")
@validation.required_services(consts.Service.MURANO)
@scenario.configure(context={"cleanup": ["murano.environments"]},
                    name="MuranoEnvironments.create_and_delete_environment")
class CreateAndDeleteEnvironment(utils.MuranoScenario):

    def run(self):
        """Create environment, session and delete environment."""
        environment = self._create_environment()

        self._create_session(environment.id)
        self._delete_environment(environment)


@validation.required_clients("murano")
@validation.required_services(consts.Service.MURANO)
@validation.required_contexts("murano_packages")
@scenario.configure(context={"cleanup": ["murano"], "roles": ["admin"]},
                    name="MuranoEnvironments.create_and_deploy_environment")
class CreateAndDeployEnvironment(utils.MuranoScenario):

    def run(self, packages_per_env=1):
        """Create environment, session and deploy environment.

        Create environment, create session, add app to environment
        packages_per_env times, send environment to deploy.

        :param packages_per_env: number of packages per environment
        """
        environment = self._create_environment()
        session = self._create_session(environment.id)
        package = self.context["tenant"]["packages"][0]

        with atomic.ActionTimer(self, "murano.create_services"):
            for i in range(packages_per_env):
                self._create_service(environment, session,
                                     package.fully_qualified_name,
                                     atomic_action=False)

        self._deploy_environment(environment, session)