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

import mock
from oslo_config import cfg

from rally.plugins.openstack.scenarios.murano import utils
from tests.unit import test

MRN_UTILS = "rally.plugins.openstack.scenarios.murano.utils"
CONF = cfg.CONF


class MuranoScenarioTestCase(test.ScenarioTestCase):

    def test_list_environments(self):
        self.clients("murano").environments.list.return_value = []
        scenario = utils.MuranoScenario(context=self.context)
        return_environments_list = scenario._list_environments()
        self.assertEqual([], return_environments_list)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "murano.list_environments")

    def test_create_environments(self):
        mock_create = mock.Mock(return_value="foo_env")
        self.clients("murano").environments.create = mock_create
        scenario = utils.MuranoScenario(context=self.context)
        create_env = scenario._create_environment("env_name")
        self.assertEqual("foo_env", create_env)
        mock_create.assert_called_once_with({"name": "env_name"})
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "murano.create_environment")

    def test_delete_environment(self):
        environment = mock.Mock(id="id")
        self.clients("murano").environments.delete.return_value = "ok"
        scenario = utils.MuranoScenario(context=self.context)
        scenario._delete_environment(environment)
        self.clients("murano").environments.delete.assert_called_once_with(
            environment.id
        )

        self.mock_wait_for_delete.mock.assert_called_once_with(
            environment,
            update_resource=self.mock_get_from_manager.mock.return_value,
            timeout=CONF.benchmark.delete_environment_timeout,
            check_interval=CONF.benchmark.delete_environment_check_interval)
        self.mock_get_from_manager.mock.assert_called_once_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "murano.delete_environment")

    def test_create_session(self):
        self.clients("murano").sessions.configure.return_value = "sess"
        scenario = utils.MuranoScenario(context=self.context)
        create_sess = scenario._create_session("id")
        self.assertEqual("sess", create_sess)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "murano.create_session")

    def test__create_service(self,):
        self.clients("murano").services.post.return_value = "app"
        mock_env = mock.Mock(id="ip")
        mock_sess = mock.Mock(id="ip")
        scenario = utils.MuranoScenario(context=self.context)

        create_app = scenario._create_service(mock_env, mock_sess,
                                              "fake_full_name",
                                              atomic_action=True)

        self.assertEqual("app", create_app)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "murano.create_service")

    def test_deploy_environment(self):
        environment = mock.Mock(id="id")
        session = mock.Mock(id="id")
        self.clients("murano").sessions.deploy.return_value = "ok"
        scenario = utils.MuranoScenario(context=self.context)
        scenario._deploy_environment(environment, session)

        self.clients("murano").sessions.deploy.assert_called_once_with(
            environment.id, session.id
        )

        self.mock_wait_for.mock.assert_called_once_with(
            environment,
            update_resource=self.mock_get_from_manager.mock.return_value,
            is_ready=self.mock_resource_is.mock.return_value,
            check_interval=CONF.benchmark.deploy_environment_check_interval,
            timeout=CONF.benchmark.deploy_environment_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with(
            ["DEPLOY FAILURE"])
        self.mock_resource_is.mock.assert_called_once_with("READY")
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "murano.deploy_environment")
