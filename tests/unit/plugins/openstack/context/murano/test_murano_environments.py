# Copyright 2015: Mirantis Inc.
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

import mock

from rally.plugins.openstack.context.murano import murano_environments
from tests.unit import test

CTX = "rally.plugins.openstack.context.murano.murano_environments"
SCN = "rally.plugins.openstack.scenarios"


class MuranoEnvironmentGeneratorTestCase(test.TestCase):

    def setUp(self):
        super(MuranoEnvironmentGeneratorTestCase, self).setUp()

    @staticmethod
    def _get_context():
        return {
            "config": {
                "users": {
                    "tenants": 2,
                    "users_per_tenant": 1,
                    "concurrent": 1,
                },
                "murano_environments": {
                    "environments_per_tenant": 1
                }
            },
            "admin": {
                "credential": mock.MagicMock()
            },
            "task": mock.MagicMock(),
            "users": [
                {
                    "id": "user_0",
                    "tenant_id": "tenant_0",
                    "credential": "credential"
                },
                {
                    "id": "user_1",
                    "tenant_id": "tenant_1",
                    "credential": "credential"
                }
            ],
            "tenants": {
                "tenant_0": {"name": "tenant_0_name"},
                "tenant_1": {"name": "tenant_1_name"}
            }
        }

    @mock.patch("%s.murano.utils.MuranoScenario._create_environment" % SCN)
    def test_setup(self, mock_murano_scenario__create_environment):
        mock_env = mock.MagicMock()
        mock_murano_scenario__create_environment.return_value = mock_env

        murano_ctx = murano_environments.EnvironmentGenerator(
            self._get_context())
        murano_ctx.setup()

        self.assertEqual(2, len(murano_ctx.context["tenants"]))
        tenant_id = murano_ctx.context["users"][0]["tenant_id"]
        self.assertEqual([mock_env],
                         murano_ctx.context["tenants"][tenant_id][
                             "environments"])

    @mock.patch("%s.murano.utils.MuranoScenario._create_environment" % SCN)
    @mock.patch("%s.resource_manager.cleanup" % CTX)
    def test_cleanup(self, mock_cleanup,
                     mock_murano_scenario__create_environment):
        mock_env = mock.Mock()
        mock_murano_scenario__create_environment.return_value = mock_env

        murano_ctx = murano_environments.EnvironmentGenerator(
            self._get_context())
        murano_ctx.setup()
        murano_ctx.cleanup()

        mock_cleanup.assert_called_once_with(names=["murano.environments"],
                                             users=murano_ctx.context["users"])
