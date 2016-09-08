# Copyright 2015 Mirantis Inc.
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

import ddt
import mock
import six

from rally import consts as rally_consts
from rally.plugins.openstack.context.manila import consts
from rally.plugins.openstack.context.manila import manila_security_services
from tests.unit import test

CONTEXT_NAME = consts.SECURITY_SERVICES_CONTEXT_NAME


@ddt.ddt
class SecurityServicesTestCase(test.ScenarioTestCase):
    TENANTS_AMOUNT = 3
    USERS_PER_TENANT = 4
    SECURITY_SERVICES = [
        {"security_service_type": ss_type,
         "dns_ip": "fake_dns_ip_%s" % ss_type,
         "server": "fake_server_%s" % ss_type,
         "domain": "fake_domain_%s" % ss_type,
         "user": "fake_user_%s" % ss_type,
         "password": "fake_password_%s" % ss_type}
        for ss_type in ("ldap", "kerberos", "active_directory")
    ]

    def _get_context(self, security_services=None, networks_per_tenant=2,
                     neutron_network_provider=True):
        if security_services is None:
            security_services = self.SECURITY_SERVICES
        tenants = {}
        for t_id in range(self.TENANTS_AMOUNT):
            tenants[six.text_type(t_id)] = {"name": six.text_type(t_id)}
            tenants[six.text_type(t_id)]["networks"] = []
            for i in range(networks_per_tenant):
                network = {"id": "fake_net_id_%s" % i}
                if neutron_network_provider:
                    network["subnets"] = ["fake_subnet_id_of_net_%s" % i]
                else:
                    network["cidr"] = "101.0.5.0/24"
                tenants[six.text_type(t_id)]["networks"].append(network)
        users = []
        for t_id in tenants.keys():
            for i in range(self.USERS_PER_TENANT):
                users.append({"id": i, "tenant_id": t_id, "endpoint": "fake"})
        context = {
            "config": {
                "users": {
                    "tenants": self.TENANTS_AMOUNT,
                    "users_per_tenant": self.USERS_PER_TENANT,
                },
                CONTEXT_NAME: {
                    "security_services": security_services,
                },
            },
            "admin": {
                "endpoint": mock.MagicMock(),
            },
            "task": mock.MagicMock(),
            "users": users,
            "tenants": tenants,
        }
        return context

    def test_init(self):
        context = {
            "task": mock.MagicMock(),
            "config": {
                CONTEXT_NAME: {"foo": "bar"},
                "not_manila": {"not_manila_key": "not_manila_value"},
            }
        }

        inst = manila_security_services.SecurityServices(context)

        self.assertEqual(inst.config.get("foo"), "bar")
        self.assertFalse(inst.config.get("security_services"))
        self.assertIn(
            rally_consts.JSON_SCHEMA, inst.CONFIG_SCHEMA.get("$schema"))
        self.assertEqual(False, inst.CONFIG_SCHEMA.get("additionalProperties"))
        self.assertEqual("object", inst.CONFIG_SCHEMA.get("type"))
        props = inst.CONFIG_SCHEMA.get("properties", {})
        self.assertEqual({"type": "array"}, props.get("security_services"))
        self.assertEqual(445, inst.get_order())
        self.assertEqual(CONTEXT_NAME, inst.get_name())

    @mock.patch.object(manila_security_services.manila_utils, "ManilaScenario")
    @ddt.data(True, False)
    def test_setup_security_services_set(self, neutron_network_provider,
                                         mock_manila_scenario):
        ctxt = self._get_context(
            neutron_network_provider=neutron_network_provider)
        inst = manila_security_services.SecurityServices(ctxt)

        inst.setup()

        self.assertEqual(
            self.TENANTS_AMOUNT, mock_manila_scenario.call_count)
        self.assertEqual(
            mock_manila_scenario.call_args_list,
            [mock.call({
                "task": inst.task,
                "config": {"api_versions": []},
                "user": user})
             for user in inst.context["users"] if user["id"] == 0]
        )
        mock_create_security_service = (
            mock_manila_scenario.return_value._create_security_service)
        expected_calls = []
        for ss in self.SECURITY_SERVICES:
            expected_calls.extend([mock.call(**ss), mock.call().to_dict()])
        mock_create_security_service.assert_has_calls(expected_calls)
        self.assertEqual(
            self.TENANTS_AMOUNT * len(self.SECURITY_SERVICES),
            mock_create_security_service.call_count)
        self.assertEqual(
            self.TENANTS_AMOUNT,
            len(inst.context["config"][CONTEXT_NAME]["security_services"]))
        for tenant in inst.context["tenants"]:
            self.assertEqual(
                self.TENANTS_AMOUNT,
                len(inst.context["tenants"][tenant][CONTEXT_NAME][
                    "security_services"])
            )

    @mock.patch.object(manila_security_services.manila_utils, "ManilaScenario")
    def test_setup_security_services_not_set(self, mock_manila_scenario):
        ctxt = self._get_context(security_services=[])
        inst = manila_security_services.SecurityServices(ctxt)

        inst.setup()

        self.assertFalse(mock_manila_scenario.called)
        self.assertFalse(
            mock_manila_scenario.return_value._create_security_service.called)
        self.assertIn(CONTEXT_NAME, inst.context["config"])
        self.assertIn(
            "security_services", inst.context["config"][CONTEXT_NAME])
        self.assertEqual(
            0,
            len(inst.context["config"][CONTEXT_NAME]["security_services"]))
        for tenant in inst.context["tenants"]:
            self.assertEqual(
                0,
                len(inst.context["tenants"][tenant][CONTEXT_NAME][
                    "security_services"])
            )

    @mock.patch.object(manila_security_services, "resource_manager")
    def test_cleanup_security_services_enabled(self, mock_resource_manager):
        ctxt = self._get_context()
        inst = manila_security_services.SecurityServices(ctxt)

        inst.cleanup()

        mock_resource_manager.cleanup.assert_called_once_with(
            names=["manila.security_services"], users=ctxt["users"])
