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

import uuid

from oslo_config import cfg

from rally.task.scenarios import base
from rally.task import utils

CONF = cfg.CONF

MURANO_TIMEOUT_OPTS = [
    cfg.IntOpt("delete_environment_timeout", default=180,
               help="A timeout in seconds for an environment delete"),
    cfg.IntOpt("deploy_environment_timeout", default=1200,
               help="A timeout in seconds for an environment deploy"),
    cfg.IntOpt("delete_environment_check_interval", default=2,
               help="Delete environment check interval in seconds"),
    cfg.IntOpt("deploy_environment_check_interval", default=5,
               help="Deploy environment check interval in seconds")
]

benchmark_group = cfg.OptGroup(name="benchmark", title="benchmark options")
CONF.register_opts(MURANO_TIMEOUT_OPTS, group=benchmark_group)


class MuranoScenario(base.Scenario):
    """Base class for Murano scenarios with basic atomic actions."""

    @base.atomic_action_timer("murano.list_environments")
    def _list_environments(self):
        """Return environments list."""
        return self.clients("murano").environments.list()

    @base.atomic_action_timer("murano.create_environment")
    def _create_environment(self, env_name=None):
        """Create environment.

        :param env_name: String used to name environment

        :returns: Environment instance
        """
        env_name = env_name or self._generate_random_name()
        return self.clients("murano").environments.create({"name": env_name})

    @base.atomic_action_timer("murano.delete_environment")
    def _delete_environment(self, environment):
        """Delete given environment.

        Return when the environment is actually deleted.

        :param environment: Environment instance
        """
        self.clients("murano").environments.delete(environment.id)
        utils.wait_for_delete(
            environment,
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.delete_environment_timeout,
            check_interval=CONF.benchmark.delete_environment_check_interval
        )

    @base.atomic_action_timer("murano.create_session")
    def _create_session(self, environment_id):
        """Create session for environment with specific id

        :param environment_id: Environment id
        :returns: Session instance
        """
        return self.clients("murano").sessions.configure(environment_id)

    def _create_service(self, environment, session, full_package_name,
                        image_name=None, flavor_name=None,
                        atomic_action=True):
        """Create Murano service.

        :param environment: Environment instance
        :param session: Session instance
        :param full_package_name: full name of the Murano package
        :param image_name: Image name
        :param flavor_name: Flavor name
        :param atomic_action: True if this is atomic action
        :returns: Service instance
        """
        app_id = str(uuid.uuid4())
        data = {"?": {"id": app_id,
                      "type": full_package_name},
                "name": self._generate_random_name("rally_")}

        if atomic_action:
            with base.AtomicAction(self, "murano.create_service"):
                return self.clients("murano").services.post(
                    environment_id=environment.id, path="/", data=data,
                    session_id=session.id)
        else:
            return self.clients("murano").services.post(
                environment_id=environment.id, path="/", data=data,
                session_id=session.id)

    @base.atomic_action_timer("murano.deploy_environment")
    def _deploy_environment(self, environment, session):
        """Deploy environment.

        :param environment: Environment instance
        :param session: Session instance
        """
        self.clients("murano").sessions.deploy(environment.id,
                                               session.id)
        utils.wait_for(
            environment, is_ready=utils.resource_is("READY"),
            update_resource=utils.get_from_manager(["DEPLOY FAILURE"]),
            timeout=CONF.benchmark.deploy_environment_timeout,
            check_interval=CONF.benchmark.deploy_environment_check_interval
        )
