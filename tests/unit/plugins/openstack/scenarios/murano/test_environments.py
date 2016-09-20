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

from rally.plugins.openstack.scenarios.murano import environments
from tests.unit import test

MURANO_SCENARIO = ("rally.plugins.openstack.scenarios.murano."
                   "environments")


class MuranoEnvironmentsTestCase(test.ScenarioTestCase):

    def _get_context(self):
        self.context.update({
            "tenant": {
                "packages": [mock.MagicMock(fully_qualified_name="fake")]
            },
            "user": {
                "tenant_id": "fake_tenant_id"
            },
            "config": {
                "murano_packages": {
                    "app_package": (
                        "rally-jobs/extra/murano/"
                        "applications/HelloReporter/"
                        "io.murano.apps.HelloReporter.zip")
                }
            }
        })
        return self.context

    def test_list_environments(self):
        TEST_TARGET = "ListEnvironments"
        list_env_module = ("{}.{}.{}").format(MURANO_SCENARIO,
                                              TEST_TARGET,
                                              "_list_environments")
        scenario = environments.ListEnvironments(self.context)
        with mock.patch(list_env_module) as mock_list_env:
            scenario.run()
            mock_list_env.assert_called_once_with()

    def test_create_and_delete_environment(self):
        TEST_TARGET = "CreateAndDeleteEnvironment"
        generate_random_name_module = ("{}.{}.{}").format(
            MURANO_SCENARIO, TEST_TARGET, "generate_random_name")
        create_env_module = ("{}.{}.{}").format(MURANO_SCENARIO,
                                                TEST_TARGET,
                                                "_create_environment")
        create_session_module = ("{}.{}.{}").format(MURANO_SCENARIO,
                                                    TEST_TARGET,
                                                    "_create_session")
        delete_env_module = ("{}.{}.{}").format(MURANO_SCENARIO,
                                                TEST_TARGET,
                                                "_delete_environment")
        scenario = environments.CreateAndDeleteEnvironment(self.context)
        with mock.patch(generate_random_name_module) as mock_random_name:
            with mock.patch(create_env_module) as mock_create_env:
                with mock.patch(create_session_module) as mock_create_session:
                    with mock.patch(delete_env_module) as mock_delete_env:
                        fake_env = mock.Mock(id="fake_id")
                        mock_create_env.return_value = fake_env
                        mock_random_name.return_value = "foo"
                        scenario.run()
                        mock_create_env.assert_called_once_with()
                        mock_create_session.assert_called_once_with(
                            fake_env.id)
                        mock_delete_env.assert_called_once_with(
                            fake_env)

    def test_create_and_deploy_environment(self):
        TEST_TARGET = "CreateAndDeployEnvironment"
        create_env_module = ("{}.{}.{}").format(MURANO_SCENARIO,
                                                TEST_TARGET,
                                                "_create_environment")
        create_session_module = ("{}.{}.{}").format(MURANO_SCENARIO,
                                                    TEST_TARGET,
                                                    "_create_session")
        create_service_module = ("{}.{}.{}").format(MURANO_SCENARIO,
                                                    TEST_TARGET,
                                                    "_create_service")
        deploy_env_module = ("{}.{}.{}").format(MURANO_SCENARIO,
                                                TEST_TARGET,
                                                "_deploy_environment")
        scenario = environments.CreateAndDeployEnvironment(self.context)
        with mock.patch(create_env_module) as mock_create_env:
            with mock.patch(create_session_module) as mock_create_session:
                with mock.patch(create_service_module) as mock_create_service:
                    with mock.patch(deploy_env_module) as mock_deploy_env:
                        fake_env = mock.MagicMock(id="fake_env_id")
                        mock_create_env.return_value = fake_env

                        fake_session = mock.Mock(id="fake_session_id")
                        mock_create_session.return_value = fake_session

                        scenario.context = self._get_context()
                        scenario.context["tenants"] = {
                            "fake_tenant_id": {
                                "packages": [mock.MagicMock()]
                            }
                        }

                        scenario.run(1)

                        mock_create_env.assert_called_once_with()
                        mock_create_session.assert_called_once_with(
                            fake_env.id)
                        mock_create_service.assert_called_once_with(
                            fake_env,
                            fake_session,
                            "fake",
                            atomic_action=False)
                        mock_deploy_env.assert_called_once_with(
                            fake_env, fake_session)
                        self._test_atomic_action_timer(
                            scenario.atomic_actions(),
                            "murano.create_services")
