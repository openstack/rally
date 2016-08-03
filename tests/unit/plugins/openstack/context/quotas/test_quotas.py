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

from rally.common import logging
from rally.plugins.openstack.context.quotas import quotas
from tests.unit import test

QUOTAS_PATH = "rally.plugins.openstack.context.quotas"


@ddt.ddt
class QuotasTestCase(test.TestCase):

    def setUp(self):
        super(QuotasTestCase, self).setUp()
        self.unlimited = -1
        self.context = {
            "config": {
            },
            "tenants": {
                "t1": {"credential": mock.MagicMock()},
                "t2": {"credential": mock.MagicMock()}},
            "admin": {"credential": mock.MagicMock()},
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

    @mock.patch("%s.quotas.osclients.Clients" % QUOTAS_PATH)
    @mock.patch("%s.cinder_quotas.CinderQuotas" % QUOTAS_PATH)
    @ddt.data(True, False)
    def test_cinder_quotas(self, ex_users, mock_cinder_quotas, mock_clients):
        cinder_quo = mock_cinder_quotas.return_value
        ctx = copy.deepcopy(self.context)
        if ex_users:
            ctx["existing_users"] = None
        ctx["config"]["quotas"] = {
            "cinder": {
                "volumes": self.unlimited,
                "snapshots": self.unlimited,
                "gigabytes": self.unlimited
            }
        }

        tenants = ctx["tenants"]
        cinder_quotas = ctx["config"]["quotas"]["cinder"]
        cinder_quo.get.return_value = cinder_quotas
        with quotas.Quotas(ctx) as quotas_ctx:
            quotas_ctx.setup()
            if ex_users:
                self.assertEqual([mock.call(tenant) for tenant in tenants],
                                 cinder_quo.get.call_args_list)
            self.assertEqual([mock.call(tenant, **cinder_quotas)
                              for tenant in tenants],
                             cinder_quo.update.call_args_list)
            mock_cinder_quotas.reset_mock()

        if ex_users:
            self.assertEqual([mock.call(tenant, **cinder_quotas)
                              for tenant in tenants],
                             cinder_quo.update.call_args_list)
        else:
            self.assertEqual([mock.call(tenant) for tenant in tenants],
                             cinder_quo.delete.call_args_list)

    @mock.patch("%s.quotas.osclients.Clients" % QUOTAS_PATH)
    @mock.patch("%s.nova_quotas.NovaQuotas" % QUOTAS_PATH)
    @ddt.data(True, False)
    def test_nova_quotas(self, ex_users, mock_nova_quotas, mock_clients):
        nova_quo = mock_nova_quotas.return_value
        ctx = copy.deepcopy(self.context)
        if ex_users:
            ctx["existing_users"] = None

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

        tenants = ctx["tenants"]
        nova_quotas = ctx["config"]["quotas"]["nova"]
        nova_quo.get.return_value = nova_quotas
        with quotas.Quotas(ctx) as quotas_ctx:
            quotas_ctx.setup()
            if ex_users:
                self.assertEqual([mock.call(tenant) for tenant in tenants],
                                 nova_quo.get.call_args_list)
            self.assertEqual([mock.call(tenant, **nova_quotas)
                              for tenant in tenants],
                             nova_quo.update.call_args_list)
            mock_nova_quotas.reset_mock()

        if ex_users:
            self.assertEqual([mock.call(tenant, **nova_quotas)
                              for tenant in tenants],
                             nova_quo.update.call_args_list)
        else:
            self.assertEqual([mock.call(tenant) for tenant in tenants],
                             nova_quo.delete.call_args_list)

    @mock.patch("%s.quotas.osclients.Clients" % QUOTAS_PATH)
    @mock.patch("%s.neutron_quotas.NeutronQuotas" % QUOTAS_PATH)
    @ddt.data(True, False)
    def test_neutron_quotas(self, ex_users, mock_neutron_quotas, mock_clients):
        neutron_quo = mock_neutron_quotas.return_value
        ctx = copy.deepcopy(self.context)
        if ex_users:
            ctx["existing_users"] = None

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

        tenants = ctx["tenants"]
        neutron_quotas = ctx["config"]["quotas"]["neutron"]
        neutron_quo.get.return_value = neutron_quotas
        with quotas.Quotas(ctx) as quotas_ctx:
            quotas_ctx.setup()
            if ex_users:
                self.assertEqual([mock.call(tenant) for tenant in tenants],
                                 neutron_quo.get.call_args_list)
            self.assertEqual([mock.call(tenant, **neutron_quotas)
                              for tenant in tenants],
                             neutron_quo.update.call_args_list)
            neutron_quo.reset_mock()

        if ex_users:
            self.assertEqual([mock.call(tenant, **neutron_quotas)
                              for tenant in tenants],
                             neutron_quo.update.call_args_list)
        else:
            self.assertEqual([mock.call(tenant) for tenant in tenants],
                             neutron_quo.delete.call_args_list)

    @mock.patch("rally.plugins.openstack.context."
                "quotas.quotas.osclients.Clients")
    @mock.patch("rally.plugins.openstack.context."
                "quotas.nova_quotas.NovaQuotas")
    @mock.patch("rally.plugins.openstack.context."
                "quotas.cinder_quotas.CinderQuotas")
    @mock.patch("rally.plugins.openstack.context."
                "quotas.neutron_quotas.NeutronQuotas")
    def test_no_quotas(self, mock_neutron_quotas, mock_cinder_quotas,
                       mock_nova_quotas, mock_clients):
        ctx = copy.deepcopy(self.context)
        if "quotas" in ctx["config"]:
            del ctx["config"]["quotas"]

        with quotas.Quotas(ctx) as quotas_ctx:
            quotas_ctx.setup()
            self.assertFalse(mock_cinder_quotas.update.called)
            self.assertFalse(mock_nova_quotas.update.called)
            self.assertFalse(mock_neutron_quotas.update.called)

        self.assertFalse(mock_cinder_quotas.delete.called)
        self.assertFalse(mock_nova_quotas.delete.called)
        self.assertFalse(mock_neutron_quotas.delete.called)

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
        quotas_path = "%s.%s" % (QUOTAS_PATH, quotas_class_path)
        with mock.patch(quotas_path) as mock_quotas:
            mock_quotas.return_value.update.side_effect = Exception

            ctx = copy.deepcopy(self.context)
            ctx["config"]["quotas"] = quotas_ctxt

            quotas_instance = quotas.Quotas(ctx)
            quotas_instance.original_quotas = []
            for service in quotas_ctxt:
                for tenant in self.context["tenants"]:
                    quotas_instance.original_quotas.append(
                        (service, tenant, quotas_ctxt[service]))
            # NOTE(boris-42): ensure that cleanup didn't raise exceptions.
            with logging.LogCatcher(quotas.LOG) as log:
                quotas_instance.cleanup()

                log.assertInLogs("Failed to restore quotas for tenant")

            self.assertEqual(mock_quotas.return_value.update.call_count,
                             len(self.context["tenants"]))
