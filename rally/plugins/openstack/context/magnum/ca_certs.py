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

import os

from cryptography.hazmat import backends
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography import x509
from cryptography.x509 import oid

from rally.common import utils as rutils
from rally.common import validation
from rally import consts
from rally.plugins.openstack.scenarios.magnum import utils as magnum_utils
from rally.task import context


@validation.add("required_platform", platform="openstack", users=True)
@context.configure(name="ca_certs", platform="openstack", order=490)
class CaCertGenerator(context.Context):
    """Creates ca certs."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "directory": {
                "type": "string",
            }
        },
        "additionalProperties": False
    }

    def _generate_csr_and_key(self):
        """Return a dict with a new csr and key."""
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=backends.default_backend())

        csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
            x509.NameAttribute(oid.NameOID.COMMON_NAME, u"Magnum User"),
        ])).sign(key, hashes.SHA256(), backends.default_backend())

        result = {
            "csr": csr.public_bytes(encoding=serialization.Encoding.PEM),
            "key": key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()),
        }

        return result

    def setup(self):
        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):

            magnum_scenario = magnum_utils.MagnumScenario({
                "user": user,
                "task": self.context["task"],
                "config": {"api_versions": self.context["config"].get(
                    "api_versions", [])}
            })

            # get the cluster and cluster_template
            cluster_uuid = str(self.context["tenants"][tenant_id]["cluster"])
            cluster = magnum_scenario._get_cluster(cluster_uuid)
            cluster_template = magnum_scenario._get_cluster_template(
                cluster.cluster_template_id)

            if not cluster_template.tls_disabled:
                tls = self._generate_csr_and_key()
                dir = ""
                if self.config.get("directory") is not None:
                    dir = self.config.get("directory")
                self.context["ca_certs_directory"] = dir
                fname = os.path.join(dir, cluster_uuid + ".key")
                with open(fname, "w") as key_file:
                    key_file.write(tls["key"])
                # get CA certificate for this cluster
                ca_cert = magnum_scenario._get_ca_certificate(cluster_uuid)
                fname = os.path.join(dir, cluster_uuid + "_ca.crt")
                with open(fname, "w") as ca_cert_file:
                    ca_cert_file.write(ca_cert.pem)
                # send csr to Magnum to have it signed
                csr_req = {"cluster_uuid": cluster_uuid,
                           "csr": tls["csr"]}
                cert = magnum_scenario._create_ca_certificate(csr_req)
                fname = os.path.join(dir, cluster_uuid + ".crt")
                with open(fname, "w") as cert_file:
                    cert_file.write(cert.pem)

    def cleanup(self):
        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):

            magnum_scenario = magnum_utils.MagnumScenario({
                "user": user,
                "task": self.context["task"],
                "config": {"api_versions": self.context["config"].get(
                    "api_versions", [])}
            })

            # get the cluster and cluster_template
            cluster_uuid = str(self.context["tenants"][tenant_id]["cluster"])
            cluster = magnum_scenario._get_cluster(cluster_uuid)
            cluster_template = magnum_scenario._get_cluster_template(
                cluster.cluster_template_id)

            if not cluster_template.tls_disabled:
                dir = self.context["ca_certs_directory"]
                fname = os.path.join(dir, cluster_uuid + ".key")
                os.remove(fname)
                fname = os.path.join(dir, cluster_uuid + "_ca.crt")
                os.remove(fname)
                fname = os.path.join(dir, cluster_uuid + ".crt")
                os.remove(fname)
