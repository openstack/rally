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

from rally.common import objects
from rally.plugins.openstack.context.sahara import sahara_output_data_sources
from tests.unit import test

CTX = "rally.plugins.openstack.context.sahara"


class SaharaOutputDataSourcesTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(SaharaOutputDataSourcesTestCase, self).setUp()
        fake_dict = objects.Credential("http://fake.example.org:5000/v2.0/",
                                       "user", "passwd")
        self.tenants_num = 2
        self.users_per_tenant = 2
        self.users = self.tenants_num * self.users_per_tenant
        self.task = mock.MagicMock()

        self.tenants = {}
        self.users_key = []

        for i in range(self.tenants_num):
            self.tenants[str(i)] = {"id": str(i), "name": str(i),
                                    "sahara": {"image": "42"}}
            for j in range(self.users_per_tenant):
                self.users_key.append({"id": "%s_%s" % (str(i), str(j)),
                                       "tenant_id": str(i),
                                       "credential": fake_dict})

        self.user_key = [{"id": i, "tenant_id": j, "credential": "credential"}
                         for j in range(self.tenants_num)
                         for i in range(self.users_per_tenant)]
        self.context.update({
            "config": {
                "users": {
                    "tenants": self.tenants_num,
                    "users_per_tenant": self.users_per_tenant,
                },
                "sahara_output_data_sources": {
                    "output_type": "hdfs",
                    "output_url_prefix": "hdfs://test_host/",
                },
            },
            "admin": {"credential": mock.MagicMock()},
            "task": mock.MagicMock(),
            "users": self.users_key,
            "tenants": self.tenants
        })

    def check_setup(self):
        context = sahara_output_data_sources.SaharaOutputDataSources.context[
            "sahara"]["output_conf"]
        self.assertIsNotNone(context.get("output_type"))
        self.assertIsNotNone(context.get("output_url_prefix"))

    @mock.patch("%s.sahara_output_data_sources.resource_manager.cleanup" % CTX)
    @mock.patch("%s.sahara_output_data_sources.osclients" % CTX)
    def test_setup_and_cleanup_hdfs(self, mock_osclients, mock_cleanup):

        mock_sahara = mock_osclients.Clients(mock.MagicMock()).sahara()
        mock_sahara.data_sources.create.return_value = mock.MagicMock(
            id=42)

        sahara_ctx = sahara_output_data_sources.SaharaOutputDataSources(
            self.context)
        sahara_ctx.generate_random_name = mock.Mock()

        output_ds_crete_calls = []

        for i in range(self.tenants_num):
            output_ds_crete_calls.append(mock.call(
                name=sahara_ctx.generate_random_name.return_value,
                description="",
                data_source_type="hdfs",
                url="hdfs://test_host/"))

        sahara_ctx.setup()

        mock_sahara.data_sources.create.assert_has_calls(
            output_ds_crete_calls)

        sahara_ctx.cleanup()

        mock_cleanup.assert_called_once_with(
            names=["sahara.data_sources"],
            users=self.context["users"])

    @mock.patch("%s.sahara_output_data_sources.osclients" % CTX)
    def test_setup_inputs_swift(self, mock_osclients):
        mock_sahara = mock_osclients.Clients(mock.MagicMock()).sahara()

        self.context.update({
            "config": {
                "users": {
                    "tenants": self.tenants_num,
                    "users_per_tenant": self.users_per_tenant,
                },
                "sahara_output_data_sources": {
                    "output_type": "swift",
                    "output_url_prefix": "rally",
                },
            },
            "admin": {"credential": mock.MagicMock()},
            "task": mock.MagicMock(),
            "users": self.users_key,
            "tenants": self.tenants,
            "user_choice_method": "random",
        })

        sahara_ctx = sahara_output_data_sources.SaharaOutputDataSources(
            self.context)
        sahara_ctx.generate_random_name = mock.Mock(return_value="random_name")

        output_ds_crete_calls = []
        for i in range(self.tenants_num):
            output_ds_crete_calls.append(mock.call(
                name="random_name",
                description="",
                data_source_type="swift",
                url="swift://random_name.sahara/",
                credential_user="user",
                credential_pass="passwd"
            ))

        sahara_ctx.setup()

        mock_sahara.data_sources.create.assert_has_calls(
            output_ds_crete_calls)

        sahara_ctx.cleanup()
