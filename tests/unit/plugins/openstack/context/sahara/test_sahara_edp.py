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

from rally.plugins.openstack.context.sahara import sahara_edp
from tests.unit import test

CTX = "rally.plugins.openstack.context.sahara"


class SaharaEDPTestCase(test.TestCase):

    def setUp(self):
        super(SaharaEDPTestCase, self).setUp()
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

    @property
    def context_without_edp_keys(self):
        context = test.get_test_context()
        context.update({
            "config": {
                "users": {
                    "tenants": self.tenants_num,
                    "users_per_tenant": self.users_per_tenant,
                },
                "sahara_edp": {
                    "input_type": "hdfs",
                    "output_type": "hdfs",
                    "input_url": "hdfs://test_host/",
                    "output_url_prefix": "hdfs://test_host/out_",
                    "libs": [
                        {
                            "name": "test.jar",
                            "download_url": "http://example.com/test.jar"
                        }
                    ]
                },
            },
            "admin": {"endpoint": mock.MagicMock()},
            "users": self.users_key,
            "tenants": self.tenants
        })
        return context

    @mock.patch("%s.sahara_edp.resource_manager.cleanup" % CTX)
    @mock.patch("%s.sahara_edp.requests" % CTX)
    @mock.patch("%s.sahara_edp.osclients" % CTX)
    def test_setup_and_cleanup(self, mock_osclients, mock_requests,
                               mock_cleanup):

        mock_sahara = mock_osclients.Clients(mock.MagicMock()).sahara()
        mock_sahara.data_sources.create.return_value = mock.MagicMock(id=42)
        mock_sahara.job_binary_internals.create.return_value = (
            mock.MagicMock(id=42))

        mock_requests.get().content = "test_binary"

        ctx = self.context_without_edp_keys
        sahara_ctx = sahara_edp.SaharaEDP(ctx)

        input_ds_crete_calls = []
        download_calls = []
        job_binary_internals_calls = []
        job_binaries_calls = []

        for i in range(self.tenants_num):
            input_ds_crete_calls.append(mock.call(
                name="input_ds", description="",
                data_source_type="hdfs",
                url="hdfs://test_host/"))
            download_calls.append(mock.call("http://example.com/test.jar"))
            job_binary_internals_calls.append(mock.call(
                name="test.jar",
                data="test_binary"))
            job_binaries_calls.append(mock.call(
                name="test.jar",
                url="internal-db://42",
                description="",
                extra={}))

        sahara_ctx.setup()

        mock_sahara.data_sources.create.assert_has_calls(input_ds_crete_calls)
        mock_requests.get.assert_has_calls(download_calls)
        mock_sahara.job_binary_internals.create.assert_has_calls(
            job_binary_internals_calls)
        mock_sahara.job_binaries.create.assert_has_calls(job_binaries_calls)

        sahara_ctx.cleanup()

        mock_cleanup.assert_called_once_with(
            names=["sahara.job_executions", "sahara.jobs",
                   "sahara.job_binary_internals", "sahara.job_binaries",
                   "sahara.data_sources"],
            users=ctx["users"])
