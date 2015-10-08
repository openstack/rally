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

from rally import exceptions
from rally.plugins.openstack.context.keystone import api_versions
from tests.unit import test

CTX = "rally.plugins.openstack.context.keystone.api_versions"


class OpenStackServicesTestCase(test.TestCase):

    def test_validate_correct_config(self):
        api_versions.OpenStackAPIVersions.validate({
            "nova": {"service_type": "compute", "version": 2},
            "cinder": {"service_name": "cinderv2", "version": 2},
            "neutron": {"service_type": "network"},
            "glance": {"service_name": "glance"},
            "heat": {"version": 1}
        })

    def test_validate_wrong_configs(self):
        self.assertRaises(
            exceptions.PluginNotFound,
            api_versions.OpenStackAPIVersions.validate,
            {"invalid": {"service_type": "some_type"}},
            "Non-existing clients should be caught.")

        self.assertRaises(
            jsonschema.ValidationError,
            api_versions.OpenStackAPIVersions.validate,
            {"nova": {"some_key": "some_value"}},
            "Additional properties should be restricted.")

        self.assertRaises(
            exceptions.ValidationError,
            api_versions.OpenStackAPIVersions.validate,
            {"keystone": {"service_type": "identity"}},
            "Setting service_type is allowed only for those clients, which "
            "support it.")

        self.assertRaises(
            exceptions.ValidationError,
            api_versions.OpenStackAPIVersions.validate,
            {"keystone": {"service_name": "keystone"}},
            "Setting service_name is allowed only for those clients, which "
            "support it.")

        self.assertRaises(
            exceptions.ValidationError,
            api_versions.OpenStackAPIVersions.validate,
            {"keystone": {"version": 1}},
            "Setting version is allowed only for those clients, which "
            "support it.")

        self.assertRaises(
            exceptions.ValidationError,
            api_versions.OpenStackAPIVersions.validate,
            {"nova": {"version": 666}},
            "Unsupported version should be caught.")

    @mock.patch("%s.osclients.Clients.services" % CTX, return_value={})
    def test_setup_with_wrong_service_name(self, mock_clients_services):
        context = {
            "config": {api_versions.OpenStackAPIVersions.get_name(): {
                "nova": {"service_name": "service_name"}}},
            "admin": {"endpoint": mock.MagicMock()}}
        ctx = api_versions.OpenStackAPIVersions(context)
        self.assertRaises(exceptions.ValidationError, ctx.setup)
        mock_clients_services.assert_called_once_with()

    @mock.patch("%s.osclients.Clients.services" % CTX, return_value={})
    def test_setup_with_wrong_service_type(self, mock_clients_services):
        context = {
            "config": {api_versions.OpenStackAPIVersions.get_name(): {
                "nova": {"service_type": "service_type"}}},
            "admin": {"endpoint": mock.MagicMock()}}
        ctx = api_versions.OpenStackAPIVersions(context)
        self.assertRaises(exceptions.ValidationError, ctx.setup)
        mock_clients_services.assert_called_once_with()

    @mock.patch("%s.osclients.Clients.services" % CTX)
    def test_setup_with_service_name(self, mock_clients_services):
        mock_clients_services.return_value = {"computev21": "NovaV21"}
        context = {
            "config": {api_versions.OpenStackAPIVersions.get_name(): {
                "nova": {"service_name": "NovaV21"}}},
            "admin": {"endpoint": mock.MagicMock()}}
        ctx = api_versions.OpenStackAPIVersions(copy.deepcopy(context))

        ctx.setup()

        mock_clients_services.assert_called_once_with()

        self.assertEqual("computev21", ctx.config["nova"]["service_type"])