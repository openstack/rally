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

CTX = "rally.task.context"
MURANO_SCENARIO = ("rally.plugins.openstack.scenarios.murano."
                   "environments.MuranoEnvironments")


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

    @mock.patch(MURANO_SCENARIO + "._list_environments")
    def test_list_environments(self, mock__list_environments):
        scenario = environments.MuranoEnvironments(self.context)
        scenario._list_environments()
        mock__list_environments.assert_called_once_with()

    @mock.patch(MURANO_SCENARIO + "._create_session")
    @mock.patch(MURANO_SCENARIO + "._delete_environment")
    @mock.patch(MURANO_SCENARIO + "._create_environment")
    @mock.patch(MURANO_SCENARIO + ".generate_random_name")
    def test_create_and_delete_environment(
            self, mock_generate_random_name, mock__create_environment,
            mock__delete_environment, mock__create_session):
        scenario = environments.MuranoEnvironments(self.context)
        fake_environment = mock.Mock(id="fake_id")
        mock__create_environment.return_value = fake_environment
        mock_generate_random_name.return_value = "foo"
        scenario.create_and_delete_environment()
        mock__create_environment.assert_called_once_with()
        mock__create_session.assert_called_once_with(fake_environment.id)
        mock__delete_environment.assert_called_once_with(fake_environment)

    @mock.patch(MURANO_SCENARIO + "._create_environment")
    @mock.patch(MURANO_SCENARIO + "._create_session")
    @mock.patch(MURANO_SCENARIO + "._create_service")
    @mock.patch(MURANO_SCENARIO + "._deploy_environment")
    def test_create_and_deploy_environment(
            self, mock__deploy_environment, mock__create_service,
            mock__create_session, mock__create_environment):

        fake_environment = mock.MagicMock(id="fake_env_id")
        mock__create_environment.return_value = fake_environment

        fake_session = mock.Mock(id="fake_session_id")
        mock__create_session.return_value = fake_session

        scenario = environments.MuranoEnvironments(self.context)
        scenario.context = self._get_context()
        scenario.context["tenants"] = {
            "fake_tenant_id": {
                "packages": [mock.MagicMock()]
            }
        }

        scenario.create_and_deploy_environment(1)

        mock__create_environment.assert_called_once_with()
        mock__create_session.assert_called_once_with(fake_environment.id)
        mock__create_service.assert_called_once_with(
            fake_environment, fake_session, "fake", atomic_action=False)
        mock__deploy_environment.assert_called_once_with(
            fake_environment, fake_session)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "murano.create_services")