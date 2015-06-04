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
import random

import ddt
import jsonschema
import mock

from rally.plugins.openstack.context.quotas import quotas
from tests.unit import test

QUOTAS_PATH = "rally.plugins.openstack.context.quotas."


@ddt.ddt
class QuotasTestCase(test.TestCase):

    def setUp(self):
        super(QuotasTestCase, self).setUp()
        self.unlimited = -1
        self.context = {
            "config": {
            },
            "tenants": {
                "t1": {"endpoint": mock.MagicMock()},
                "t2": {"endpoint": mock.MagicMock()}},
            "admin": {"endpoint": mock.MagicMock()},
            "task": mock.MagicMock()
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
                "floating_ips": self.unlimited,
                "fixed_ips": self.unlimited,
                "metadata_items": self.unlimited,
                "injected_files": self.unlimited,
                "injected_file_content_bytes": self.unlimited,
                "injected_file_path_bytes": self.unlimited,
                "key_pairs": self.unlimited,
                "security_groups": self.unlimited,
                "security_group_rules": self.unlimited
            },
            "neutron": {
                "network": self.unlimited,
                "subnet": self.unlimited,
                "port": self.unlimited,
                "router": self.unlimited,
                "floatingip": self.unlimited,
                "security_group": self.unlimited,
                "security_group_rule": self.unlimited
            }
        }
        for service in ctx["config"]["quotas"]:
            for key in ctx["config"]["quotas"][service]:
                # Test invalid values
                ctx["config"]["quotas"][service][key] = self.unlimited - 1
                try:
                    quotas.Quotas.validate(ctx["config"]["quotas"])
                except jsonschema.ValidationError:
                    pass
                else:
                    self.fail("Invalid value %s must raise a validation error"
                              % ctx["config"]["quotas"][service][key])

                ctx["config"]["quotas"][service][key] = 2.5
                try:
                    quotas.Quotas.validate(ctx["config"]["quotas"])
                except jsonschema.ValidationError:
                    pass
                else:
                    self.fail("Invalid value %s must raise a validation error"
                              % ctx["config"]["quotas"][service][key])

                ctx["config"]["quotas"][service][key] = "-1"
                try:
                    quotas.Quotas.validate(ctx["config"]["quotas"])
                except jsonschema.ValidationError:
                    pass
                else:
                    self.fail("Invalid value %s must raise a validation error"
                              % ctx["config"]["quotas"][service][key])

                # Test valid values
                ctx["config"]["quotas"][service][key] = random.randint(0,
                                                                       1000000)
                try:
                    quotas.Quotas.validate(ctx["config"]["quotas"])
                except jsonschema.ValidationError:
                    self.fail("Positive integers are valid quota values")

                ctx["config"]["quotas"][service][key] = self.unlimited
                try:
                    quotas.Quotas.validate(ctx["config"]["quotas"])
                except jsonschema.ValidationError:
                    self.fail("%d is a valid quota value" % self.unlimited)

            # Test additional keys are refused
            ctx["config"]["quotas"][service]["additional"] = self.unlimited
            try:
                quotas.Quotas.validate(ctx["config"]["quotas"])
            except jsonschema.ValidationError:
                pass
            else:
                self.fail("Additional keys must raise a validation error")
            del ctx["config"]["quotas"][service]["additional"]

            # Test valid keys are optional
            ctx["config"]["quotas"][service] = {}
            try:
                quotas.Quotas.validate(ctx["config"]["quotas"])
            except jsonschema.ValidationError:
                self.fail("Valid quota keys are optional")

    @mock.patch("rally.plugins.openstack.context."
                "quotas.quotas.osclients.Clients")
    @mock.patch("rally.plugins.openstack.context."
                "quotas.cinder_quotas.CinderQuotas")
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
                expected_setup_calls.append(mock.call()
                                                .update(tenant,
                                                        **cinder_quotas))
            mock_quotas.assert_has_calls(expected_setup_calls, any_order=True)
            mock_quotas.reset_mock()

        expected_cleanup_calls = []
        for tenant in tenants:
            expected_cleanup_calls.append(mock.call().delete(tenant))
        mock_quotas.assert_has_calls(expected_cleanup_calls, any_order=True)

    @mock.patch("rally.plugins.openstack.context."
                "quotas.quotas.osclients.Clients")
    @mock.patch("rally.plugins.openstack.context."
                "quotas.nova_quotas.NovaQuotas")
    def test_nova_quotas(self, mock_quotas, mock_osclients):
        ctx = copy.deepcopy(self.context)

        ctx["config"]["quotas"] = {
            "nova": {
                "instances": self.unlimited,
                "cores": self.unlimited,
                "ram": self.unlimited,
                "floating-ips": self.unlimited,
                "fixed-ips": self.unlimited,
                "metadata_items": self.unlimited,
                "injected_files": self.unlimited,
                "injected_file_content_bytes": self.unlimited,
                "injected_file_path_bytes": self.unlimited,
                "key_pairs": self.unlimited,
                "security_groups": self.unlimited,
                "security_group_rules": self.unlimited,
            }
        }

        nova_quotas = ctx["config"]["quotas"]["nova"]
        with quotas.Quotas(ctx) as quotas_ctx:
            quotas_ctx.setup()
            expected_setup_calls = []
            for tenant in ctx["tenants"]:
                expected_setup_calls.append(mock.call()
                                                .update(tenant,
                                                        **nova_quotas))
            mock_quotas.assert_has_calls(expected_setup_calls, any_order=True)
            mock_quotas.reset_mock()

        expected_cleanup_calls = []
        for tenant in ctx["tenants"]:
            expected_cleanup_calls.append(mock.call().delete(tenant))
        mock_quotas.assert_has_calls(expected_cleanup_calls, any_order=True)

    @mock.patch("rally.plugins.openstack.context."
                "quotas.quotas.osclients.Clients")
    @mock.patch("rally.plugins.openstack.context."
                "quotas.neutron_quotas.NeutronQuotas")
    def test_neutron_quotas(self, mock_quotas, mock_osclients):
        ctx = copy.deepcopy(self.context)

        ctx["config"]["quotas"] = {
            "neutron": {
                "network": self.unlimited,
                "subnet": self.unlimited,
                "port": self.unlimited,
                "router": self.unlimited,
                "floatingip": self.unlimited,
                "security_group": self.unlimited,
                "security_group_rule": self.unlimited
            }
        }

        neutron_quotas = ctx["config"]["quotas"]["neutron"]
        with quotas.Quotas(ctx) as quotas_ctx:
            quotas_ctx.setup()
            expected_setup_calls = []
            for tenant in ctx["tenants"]:
                expected_setup_calls.append(mock.call()
                                                .update(tenant,
                                                        **neutron_quotas))
            mock_quotas.assert_has_calls(expected_setup_calls, any_order=True)
            mock_quotas.reset_mock()

        expected_cleanup_calls = []
        for tenant in ctx["tenants"]:
            expected_cleanup_calls.append(mock.call().delete(tenant))
        mock_quotas.assert_has_calls(expected_cleanup_calls, any_order=True)

    @mock.patch("rally.plugins.openstack.context."
                "quotas.quotas.osclients.Clients")
    @mock.patch("rally.plugins.openstack.context."
                "quotas.nova_quotas.NovaQuotas")
    @mock.patch("rally.plugins.openstack.context."
                "quotas.cinder_quotas.CinderQuotas")
    @mock.patch("rally.plugins.openstack.context."
                "quotas.neutron_quotas.NeutronQuotas")
    def test_no_quotas(self, mock_neutron_quota, mock_cinder_quotas,
                       mock_nova_quotas, mock_osclients):
        ctx = copy.deepcopy(self.context)
        if "quotas" in ctx["config"]:
            del ctx["config"]["quotas"]

        with quotas.Quotas(ctx) as quotas_ctx:
            quotas_ctx.setup()
            self.assertFalse(mock_cinder_quotas.update.called)
            self.assertFalse(mock_nova_quotas.update.called)
            self.assertFalse(mock_neutron_quota.update.called)

        self.assertFalse(mock_cinder_quotas.delete.called)
        self.assertFalse(mock_nova_quotas.delete.called)
        self.assertFalse(mock_neutron_quota.delete.called)

    @ddt.data(
        {"quotas_ctxt": {"nova": {"cpu": 1}},
         "quotas_class_path": "nova_quotas.NovaQuotas"},
        {"quotas_ctxt": {"neutron": {"network": 2}},
         "quotas_class_path": "neutron_quotas.NeutronQuotas"},
        {"quotas_ctxt": {"cinder": {"volumes": 3}},
         "quotas_class_path": "cinder_quotas.CinderQuotas"},
        {"quotas_ctxt": {"manila": {"shares": 4}},
         "quotas_class_path": "manila_quotas.ManilaQuotas"},
        {"quotas_ctxt": {"designate": {"domains": 5}},
         "quotas_class_path": "designate_quotas.DesignateQuotas"},
    )
    @ddt.unpack
    def test_exception_during_cleanup(self, quotas_ctxt, quotas_class_path):
        with mock.patch(QUOTAS_PATH + quotas_class_path) as mock_quotas:
            mock_quotas.delete.side_effect = type(
                "ExceptionDuringCleanup", (Exception, ), {})

            ctx = copy.deepcopy(self.context)
            ctx["config"]["quotas"] = quotas_ctxt

            # NOTE(boris-42): ensure that cleanup didn't raise exceptions.
            quotas.Quotas(ctx).cleanup()

            self.assertEqual(mock_quotas.return_value.delete.call_count,
                             len(self.context["tenants"]))
