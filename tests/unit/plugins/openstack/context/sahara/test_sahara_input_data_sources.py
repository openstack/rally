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

from rally.plugins.openstack.context.sahara import sahara_input_data_sources
from tests.unit import test

CTX = "rally.plugins.openstack.context.sahara"


class SaharaInputDataSourcesTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(SaharaInputDataSourcesTestCase, self).setUp()
        self.tenants_num = 2
        self.users_per_tenant = 2
        self.users = self.tenants_num * self.users_per_tenant
        self.task = mock.MagicMock()

        self.tenants = {}
        self.users_key = []

        for i in range(self.tenants_num):
            self.tenants[str(i)] = {"id": str(i), "name": str(i),
                                    "sahara_image": "42"}
            for j in range(self.users_per_tenant):
                self.users_key.append({"id": "%s_%s" % (str(i), str(j)),
                                       "tenant_id": str(i),
                                       "endpoint": "endpoint"})

        self.user_key = [{"id": i, "tenant_id": j, "endpoint": "endpoint"}
                         for j in range(self.tenants_num)
                         for i in range(self.users_per_tenant)]

        self.context.update({
            "config": {
                "users": {
                    "tenants": self.tenants_num,
                    "users_per_tenant": self.users_per_tenant,
                },
                "sahara_input_data_sources": {
                    "input_type": "hdfs",
                    "input_url": "hdfs://test_host/",
                },
            },
            "admin": {"endpoint": mock.MagicMock()},
            "users": self.users_key,
            "tenants": self.tenants
        })

    @mock.patch("%s.sahara_input_data_sources.resource_manager.cleanup" % CTX)
    @mock.patch("%s.sahara_input_data_sources.osclients" % CTX)
    def test_setup_and_cleanup(self, mock_osclients, mock_cleanup):

        mock_sahara = mock_osclients.Clients(mock.MagicMock()).sahara()
        mock_sahara.data_sources.create.return_value = mock.MagicMock(id=42)

        sahara_ctx = sahara_input_data_sources.SaharaInputDataSources(
            self.context)
        sahara_ctx.generate_random_name = mock.Mock()

        input_ds_crete_calls = []

        for i in range(self.tenants_num):
            input_ds_crete_calls.append(mock.call(
                name=sahara_ctx.generate_random_name.return_value,
                description="",
                data_source_type="hdfs",
                url="hdfs://test_host/"))

        sahara_ctx.setup()

        mock_sahara.data_sources.create.assert_has_calls(
            input_ds_crete_calls)

        sahara_ctx.cleanup()

        mock_cleanup.assert_called_once_with(
            names=["sahara.job_executions", "sahara.jobs",
                   "sahara.data_sources"],
            users=self.context["users"])
