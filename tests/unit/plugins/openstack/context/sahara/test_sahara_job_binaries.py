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

from rally.plugins.openstack.context.sahara import sahara_job_binaries
from tests.unit import test

CTX = "rally.plugins.openstack.context.sahara"


class SaharaJobBinariesTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(SaharaJobBinariesTestCase, self).setUp()
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
                                       "credential": "credential"})

        self.user_key = [{"id": i, "tenant_id": j, "credential": "credential"}
                         for j in range(self.tenants_num)
                         for i in range(self.users_per_tenant)]

        self.context.update({
            "config": {
                "users": {
                    "tenants": self.tenants_num,
                    "users_per_tenant": self.users_per_tenant,
                },
                "sahara_job_binaries": {
                    "libs": [
                        {
                            "name": "test.jar",
                            "download_url": "http://example.com/test.jar"
                        }
                    ],
                    "mains": [
                        {
                            "name": "test.jar",
                            "download_url": "http://example.com/test.jar"
                        }
                    ]
                },
            },
            "admin": {"credential": mock.MagicMock()},
            "task": mock.MagicMock(),
            "users": self.users_key,
            "tenants": self.tenants
        })

    @mock.patch("%s.sahara_job_binaries.resource_manager.cleanup" % CTX)
    @mock.patch(("%s.sahara_job_binaries.SaharaJobBinaries."
                 "download_and_save_lib") % CTX)
    @mock.patch("%s.sahara_job_binaries.osclients" % CTX)
    def test_setup_and_cleanup(
            self,
            mock_osclients,
            mock_sahara_job_binaries_download_and_save_lib,
            mock_cleanup):

        mock_sahara = mock_osclients.Clients(mock.MagicMock()).sahara()

        sahara_ctx = sahara_job_binaries.SaharaJobBinaries(self.context)

        download_calls = []

        for i in range(self.tenants_num):
            download_calls.append(mock.call(
                sahara=mock_sahara,
                lib_type="mains",
                name="test.jar",
                download_url="http://example.com/test.jar",
                tenant_id=str(i)))
            download_calls.append(mock.call(
                sahara=mock_sahara,
                lib_type="libs",
                name="test.jar",
                download_url="http://example.com/test.jar",
                tenant_id=str(i)))

        sahara_ctx.setup()

        (mock_sahara_job_binaries_download_and_save_lib.
         assert_has_calls(download_calls))

        sahara_ctx.cleanup()

        mock_cleanup.assert_called_once_with(
            names=["sahara.job_binary_internals", "sahara.job_binaries"],
            users=self.context["users"])

    @mock.patch("%s.sahara_job_binaries.requests" % CTX)
    @mock.patch("%s.sahara_job_binaries.osclients" % CTX)
    def test_download_and_save_lib(self, mock_osclients, mock_requests):

        mock_requests.get.content.return_value = "some_binary_content"
        mock_sahara = mock_osclients.Clients(mock.MagicMock()).sahara()
        mock_sahara.job_binary_internals.create.return_value = (
            mock.MagicMock(id=42))

        sahara_ctx = sahara_job_binaries.SaharaJobBinaries(self.context)

        sahara_ctx.context["tenants"]["0"]["sahara"] = {"mains": []}
        sahara_ctx.context["tenants"]["0"]["sahara"]["libs"] = []

        sahara_ctx.download_and_save_lib(sahara=mock_sahara,
                                         lib_type="mains",
                                         name="test_binary",
                                         download_url="http://somewhere",
                                         tenant_id="0")

        sahara_ctx.download_and_save_lib(sahara=mock_sahara,
                                         lib_type="libs",
                                         name="test_binary_2",
                                         download_url="http://somewhere",
                                         tenant_id="0")

        mock_requests.get.assert_called_once_with("http://somewhere")
