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

from rally.plugins.openstack.context.magnum import ca_certs
from tests.unit import test

CTX = "rally.plugins.openstack.context.magnum"
SCN = "rally.plugins.openstack.scenarios"


class CaCertsGeneratorTestCase(test.ScenarioTestCase):

    def _gen_tenants(self, count):
        tenants = {}
        for id_ in range(count):
            tenants[str(id_)] = {"name": str(id_)}
            tenants[str(id_)]["cluster"] = "rally_cluster_uuid"
        return tenants

    def test__generate_csr_and_key(self):

        ca_cert_ctx = ca_certs.CaCertGenerator(self.context)
        result = ca_cert_ctx._generate_csr_and_key()

        assert result["csr"] is not None
        assert result["key"] is not None

    @mock.patch("%s.magnum.utils.MagnumScenario._create_ca_certificate" % SCN)
    @mock.patch("%s.magnum.utils.MagnumScenario._get_ca_certificate" % SCN)
    @mock.patch("%s.ca_certs.open" % CTX, side_effect=mock.mock_open(),
                create=True)
    @mock.patch("%s.ca_certs.CaCertGenerator._generate_csr_and_key"
                % CTX)
    @mock.patch("%s.magnum.utils.MagnumScenario._get_cluster_template" % SCN)
    @mock.patch("%s.magnum.utils.MagnumScenario._get_cluster" % SCN,
                return_value=mock.Mock())
    def test_setup(self, mock_magnum_scenario__get_cluster,
                   mock_magnum_scenario__get_cluster_template,
                   mock_ca_cert_generator__generate_csr_and_key,
                   mock_open,
                   mock_magnum_scenario__get_ca_certificate,
                   mock_magnum_scenario__create_ca_certificate):
        tenants_count = 2
        users_per_tenant = 5

        tenants = self._gen_tenants(tenants_count)
        users = []
        for ten_id in tenants:
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": ten_id,
                              "credential": mock.MagicMock()})

        self.context.update({
            "config": {
                "users": {
                    "tenants": tenants_count,
                    "users_per_tenant": users_per_tenant,
                    "concurrent": 10,
                },
                "clusters": {
                    "cluster_template_uuid": "123456789",
                    "node_count": 2
                },
                "ca_certs": {
                    "directory": ""
                }
            },
            "users": users,
            "tenants": tenants
        })

        fake_ct = mock.Mock()
        fake_ct.tls_disabled = False
        mock_magnum_scenario__get_cluster_template.return_value = fake_ct
        fake_tls = {"csr": "fake_csr", "key": "fake_key"}
        mock_ca_cert_generator__generate_csr_and_key.return_value = fake_tls
        fake_ca_cert = mock.Mock()
        fake_ca_cert.pem = "fake_ca_cert"
        mock_magnum_scenario__get_ca_certificate.return_value = fake_ca_cert
        fake_cert = mock.Mock()
        fake_cert.pem = "fake_cert"
        mock_magnum_scenario__create_ca_certificate.return_value = fake_cert

        ca_cert_ctx = ca_certs.CaCertGenerator(self.context)
        ca_cert_ctx.setup()

        mock_cluster = mock_magnum_scenario__get_cluster.return_value
        mock_calls = [mock.call(mock_cluster.cluster_template_id)
                      for i in range(tenants_count)]
        mock_magnum_scenario__get_cluster_template.assert_has_calls(
            mock_calls)
        mock_calls = [mock.call("rally_cluster_uuid")
                      for i in range(tenants_count)]
        mock_magnum_scenario__get_cluster.assert_has_calls(mock_calls)
        mock_magnum_scenario__get_ca_certificate.assert_has_calls(mock_calls)
        fake_csr_req = {"cluster_uuid": "rally_cluster_uuid",
                        "csr": fake_tls["csr"]}
        mock_calls = [mock.call(fake_csr_req)
                      for i in range(tenants_count)]
        mock_magnum_scenario__create_ca_certificate.assert_has_calls(
            mock_calls)

    @mock.patch("%s.magnum.utils.MagnumScenario._create_ca_certificate" % SCN)
    @mock.patch("%s.magnum.utils.MagnumScenario._get_ca_certificate" % SCN)
    @mock.patch("%s.magnum.utils.MagnumScenario._get_cluster_template" % SCN)
    @mock.patch("%s.magnum.utils.MagnumScenario._get_cluster" % SCN,
                return_value=mock.Mock())
    def test_tls_disabled_setup(self, mock_magnum_scenario__get_cluster,
                                mock_magnum_scenario__get_cluster_template,
                                mock_magnum_scenario__get_ca_certificate,
                                mock_magnum_scenario__create_ca_certificate):
        tenants_count = 2
        users_per_tenant = 5

        tenants = self._gen_tenants(tenants_count)
        users = []
        for ten_id in tenants:
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": ten_id,
                              "credential": mock.MagicMock()})

        self.context.update({
            "config": {
                "users": {
                    "tenants": tenants_count,
                    "users_per_tenant": users_per_tenant,
                    "concurrent": 10,
                },
                "clusters": {
                    "cluster_template_uuid": "123456789",
                    "node_count": 2
                },
                "ca_certs": {
                    "directory": ""
                }
            },
            "users": users,
            "tenants": tenants
        })

        fake_ct = mock.Mock()
        fake_ct.tls_disabled = True
        mock_magnum_scenario__get_cluster_template.return_value = fake_ct

        ca_cert_ctx = ca_certs.CaCertGenerator(self.context)
        ca_cert_ctx.setup()

        mock_cluster = mock_magnum_scenario__get_cluster.return_value
        mock_calls = [mock.call(mock_cluster.cluster_template_id)
                      for i in range(tenants_count)]
        mock_magnum_scenario__get_cluster_template.assert_has_calls(
            mock_calls)
        mock_calls = [mock.call("rally_cluster_uuid")
                      for i in range(tenants_count)]
        mock_magnum_scenario__get_cluster.assert_has_calls(mock_calls)
        mock_magnum_scenario__get_ca_certificate.assert_not_called()
        mock_magnum_scenario__create_ca_certificate.assert_not_called()

    @mock.patch("os.remove", return_value=mock.Mock())
    @mock.patch("os.path.join", return_value=mock.Mock())
    @mock.patch("%s.magnum.utils.MagnumScenario._get_cluster_template" % SCN)
    @mock.patch("%s.magnum.utils.MagnumScenario._get_cluster" % SCN,
                return_value=mock.Mock())
    def test_cleanup(self, mock_magnum_scenario__get_cluster,
                     mock_magnum_scenario__get_cluster_template,
                     mock_os_path_join, mock_os_remove):

        tenants_count = 2
        users_per_tenant = 5

        tenants = self._gen_tenants(tenants_count)
        users = []
        for ten_id in tenants:
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": ten_id,
                              "credential": mock.MagicMock()})

        self.context.update({
            "config": {
            },
            "ca_certs_directory": "",
            "users": users,
            "tenants": tenants
        })

        fake_ct = mock.Mock()
        fake_ct.tls_disabled = False
        mock_magnum_scenario__get_cluster_template.return_value = fake_ct

        ca_cert_ctx = ca_certs.CaCertGenerator(self.context)
        ca_cert_ctx.cleanup()

        cluster_uuid = "rally_cluster_uuid"
        dir = self.context["ca_certs_directory"]
        mock_os_path_join.assert_has_calls(dir, cluster_uuid.__add__(".key"))
        mock_os_path_join.assert_has_calls(
            dir, cluster_uuid.__add__("_ca.crt"))
        mock_os_path_join.assert_has_calls(dir, cluster_uuid.__add__(".crt"))

    @mock.patch("os.remove", return_value=mock.Mock())
    @mock.patch("os.path.join", return_value=mock.Mock())
    @mock.patch("%s.magnum.utils.MagnumScenario._get_cluster_template" % SCN)
    @mock.patch("%s.magnum.utils.MagnumScenario._get_cluster" % SCN,
                return_value=mock.Mock())
    def test_tls_disabled_cleanup(self, mock_magnum_scenario__get_cluster,
                                  mock_magnum_scenario__get_cluster_template,
                                  mock_os_path_join, mock_os_remove):

        tenants_count = 2
        users_per_tenant = 5

        tenants = self._gen_tenants(tenants_count)
        users = []
        for ten_id in tenants:
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": ten_id,
                              "credential": mock.MagicMock()})

        self.context.update({
            "config": {
            },
            "ca_certs_directory": "",
            "users": users,
            "tenants": tenants
        })

        fake_ct = mock.Mock()
        fake_ct.tls_disabled = True
        mock_magnum_scenario__get_cluster_template.return_value = fake_ct

        ca_cert_ctx = ca_certs.CaCertGenerator(self.context)
        ca_cert_ctx.cleanup()

        mock_os_path_join.assert_not_called()
        mock_os_remove.assert_not_called()
