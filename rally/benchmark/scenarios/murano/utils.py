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
from rally.benchmark import utils as bench_utils


class MuranoScenario(base.Scenario):
    """Base class for Murano scenarios with basic atomic actions."""

    @base.atomic_action_timer("murano.list_environments")
    def _list_environments(self):
        """Return user images list."""
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
    def _delete_environment(self, environment, timeout=180, check_interval=2):
        """Delete given environment.

        Return when the environment is actually deleted.

        :param environment: Environment instance
        :param timeout: Timeout in seconds after which a TimeoutException
                        will be raised, by default 180
        :param check_interval: Interval in seconds between the two consecutive
                               readiness checks, by default 2
        """
        self.clients("murano").environments.delete(environment.id)
        bench_utils.wait_for_delete(
            environment,
            update_resource=bench_utils.get_from_manager(),
            timeout=timeout,
            check_interval=check_interval
        )

    @base.atomic_action_timer("murano.create_session")
    def _create_session(self, environment_id):
        """Create session for environment with specific id

        :param environment_id: Environment id
        :returns: Session instance
        """
        return self.clients("murano").sessions.configure(environment_id)
