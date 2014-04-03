# Copyright 2014: Dassault Systemes
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

import copy
import jsonschema
import mock
import random

from rally.benchmark.context import quotas
from tests import test


class NovaQuotasTestCase(test.TestCase):

    @mock.patch("rally.benchmark.context.quotas.osclients.Clients.nova")
    def test_update(self, client_mock):
        nova_quotas = quotas.NovaQuotas(client_mock)

        tenant_id = "endpoint"
        quotas_values = {
            "volumes": 10,
            "snapshots": 50,
            "gigabytes": 1000
        }

        nova_quotas.update(tenant_id, **quotas_values)
        client_mock.quotas.update.assert_called_once_with(tenant_id,
                                                          **quotas_values)

    @mock.patch("rally.benchmark.context.quotas.osclients.Clients.nova")
    def test_delete(self, client_mock):
        nova_quotas = quotas.NovaQuotas(client_mock)

        tenant_id = "endpoint"

        nova_quotas.delete(tenant_id)
        client_mock.quotas.delete.assert_called_once_with(tenant_id)


class CinderQuotasTestCase(test.TestCase):

    @mock.patch("rally.benchmark.context.quotas.osclients.Clients.cinder")
    def test_update(self, client_mock):
        cinder_quotas = quotas.NovaQuotas(client_mock)
        tenant_id = "endpoint"
        quotas_values = {
            "instances": 10,
            "cores": 100,
            "ram": 100000,
            "floating-ips": 100,
            "fixed-ips": 10000,
            "metadata-items": 5,
            "injected-files": 5,
            "injected-file-content-bytes": 2048,
            "injected-file-path-bytes": 1024,
            "key-pairs": 50,
            "security-groups": 50,
            "security-group-rules": 50
        }
        cinder_quotas.update(tenant_id, **quotas_values)
        client_mock.quotas.update.assert_called_once_with(tenant_id,
                                                          **quotas_values)

    @mock.patch("rally.benchmark.context.quotas.osclients.Clients.nova")
    def test_delete(self, client_mock):
        pass
        # Currently, no method to delete quotas available in cinder client:
        # Will be added with https://review.openstack.org/#/c/74841/
        #cinder_quotas = quotas.NovaQuotas(client_mock)
        #tenant_id = "endpoint"
        #cinder_quotas.delete(tenant_id)
        #client_mock.quotas.delete.assert_called_once_with(tenant_id)


class QuotasTestCase(test.TestCase):

    def setUp(self):
        super(QuotasTestCase, self).setUp()
        self.unlimited = -1
        self.context = {
            "config": {
            },
            "tenants": [
                {"endpoint": mock.MagicMock(), "id": mock.MagicMock()},
                {"endpoint": mock.MagicMock(), "id": mock.MagicMock()}
            ],
            "admin": {"endpoint": mock.MagicMock()},
            "task": {}
        }

    def test_quotas_schemas(self):
        ctx = copy.deepcopy(self.context)
        ctx["config"]["quotas"] = {
            "cinder": {
                "volumes": self.unlimited,
                "snapshots": self.unlimited,
                "gigabytes": self.unlimited
            },
            "nova": {
                "instances": self.unlimited,
                "cores": self.unlimited,
                "ram": self.unlimited,
                "floating-ips": self.unlimited,
                "fixed-ips": self.unlimited,
                "metadata-items": self.unlimited,
                "injected-files": self.unlimited,
                "injected-file-content-bytes": self.unlimited,
                "injected-file-path-bytes": self.unlimited,
                "key-pairs": self.unlimited,
                "security-groups": self.unlimited,
                "security-group-rules": self.unlimited
            }
        }
        for service in ctx["config"]["quotas"]:
            for key in ctx["config"]["quotas"][service]:
                # Test invalid values
                ctx["config"]["quotas"][service][key] = self.unlimited - 1
                try:
                    quotas.Quotas.validate(ctx["config"])
                except jsonschema.ValidationError:
                    pass
                else:
                    self.fail('Invalid value %s must raise a validation error'
                              % ctx["config"]["quotas"][service][key])

                ctx["config"]["quotas"][service][key] = 2.5
                try:
                    quotas.Quotas.validate(ctx["config"])
                except jsonschema.ValidationError:
                    pass
                else:
                    self.fail('Invalid value %s must raise a validation error'
                              % ctx["config"]["quotas"][service][key])

                ctx["config"]["quotas"][service][key] = "-1"
                try:
                    quotas.Quotas.validate(ctx["config"])
                except jsonschema.ValidationError:
                    pass
                else:
                    self.fail('Invalid value %s must raise a validation error'
                              % ctx["config"]["quotas"][service][key])

                # Test valid values
                ctx["config"]["quotas"][service][key] = \
                    random.randint(0, 1000000)
                try:
                    quotas.Quotas.validate(ctx["config"])
                except jsonschema.ValidationError:
                    self.fail("Positive integers are valid quota values")

                ctx["config"]["quotas"][service][key] = self.unlimited
                try:
                    quotas.Quotas.validate(ctx["config"])
                except jsonschema.ValidationError:
                    self.fail("%d is a valid quota value" % self.unlimited)

            # Test additional keys are refused
            ctx["config"]["quotas"][service]["additional"] = self.unlimited
            try:
                quotas.Quotas.validate(ctx["config"])
            except jsonschema.ValidationError:
                pass
            else:
                self.fail('Additional keys must raise a validation error')
            del ctx["config"]["quotas"][service]["additional"]

            # Test valid keys are optional
            ctx["config"]["quotas"][service] = {}
            try:
                quotas.Quotas.validate(ctx["config"])
            except jsonschema.ValidationError:
                self.fail("Valid quota keys are optional")

    @mock.patch("rally.benchmark.context.quotas.osclients.Clients")
    @mock.patch("rally.benchmark.context.quotas.CinderQuotas")
    def test_cinder_quotas(self, mock_quotas, mock_osclients):
        ctx = copy.deepcopy(self.context)
        ctx["config"]["quotas"] = {
            "cinder": {
                "volumes": self.unlimited,
                "snapshots": self.unlimited,
                "gigabytes": self.unlimited
            }
        }

        tenants = ctx["tenants"]
        cinder_quotas = ctx["config"]["quotas"]["cinder"]
        with quotas.Quotas(ctx) as quotas_ctx:
            quotas_ctx.setup()
            expected_setup_calls = []
            for tenant in tenants:
                expected_setup_calls.extend([mock.call()
                                                 .update(tenant["id"],
                                                         **cinder_quotas)])
            mock_quotas.assert_has_calls(expected_setup_calls, any_order=True)
            mock_quotas.reset_mock()

        expected_cleanup_calls = []
        for tenant in tenants:
            expected_cleanup_calls.extend([mock.call().delete(tenant["id"])])
        mock_quotas.assert_has_calls(expected_cleanup_calls, any_order=True)

    @mock.patch("rally.benchmark.context.quotas.osclients.Clients")
    @mock.patch("rally.benchmark.context.quotas.NovaQuotas")
    def test_nova_quotas(self, mock_quotas, mock_osclients):
        ctx = copy.deepcopy(self.context)

        ctx["config"]["quotas"] = {
            "nova": {
                "instances": self.unlimited,
                "cores": self.unlimited,
                "ram": self.unlimited,
                "floating-ips": self.unlimited,
                "fixed-ips": self.unlimited,
                "metadata-items": self.unlimited,
                "injected-files": self.unlimited,
                "injected-file-content-bytes": self.unlimited,
                "injected-file-path-bytes": self.unlimited,
                "key-pairs": self.unlimited,
                "security-groups": self.unlimited,
                "security-group-rules": self.unlimited,
            }
        }

        tenants = ctx["tenants"]
        nova_quotas = ctx["config"]["quotas"]["nova"]
        with quotas.Quotas(ctx) as quotas_ctx:
            quotas_ctx.setup()
            expected_setup_calls = []
            for tenant in tenants:
                expected_setup_calls.extend([mock.call()
                                                 .update(tenant["id"],
                                                         **nova_quotas)])
            mock_quotas.assert_has_calls(expected_setup_calls, any_order=True)
            mock_quotas.reset_mock()

        expected_cleanup_calls = []
        for tenant in tenants:
            expected_cleanup_calls.extend([mock.call().delete(tenant["id"])])
        mock_quotas.assert_has_calls(expected_cleanup_calls, any_order=True)

    @mock.patch("rally.benchmark.context.quotas.osclients.Clients")
    @mock.patch("rally.benchmark.context.quotas.NovaQuotas")
    @mock.patch("rally.benchmark.context.quotas.CinderQuotas")
    def test_no_quotas(self, mock_cinder_quotas, mock_nova_quotas,
                       mock_osclients):
        ctx = copy.deepcopy(self.context)
        if "quotas" in ctx["config"]:
            del ctx["config"]["quotas"]

        with quotas.Quotas(ctx) as quotas_ctx:
            quotas_ctx.setup()
            self.assertFalse(mock_cinder_quotas.update.called)
            self.assertFalse(mock_nova_quotas.update.called)
            mock_nova_quotas.reset_mock()
            mock_cinder_quotas.reset_mock()

        tenants = ctx["tenants"]
        expected_cleanup_calls = []
        for tenant in tenants:
            expected_cleanup_calls.extend([mock.call().delete(tenant["id"])])
        mock_nova_quotas.assert_has_calls(expected_cleanup_calls,
                                          any_order=True)
        mock_cinder_quotas.assert_has_calls(expected_cleanup_calls,
                                            any_order=True)
