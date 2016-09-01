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

import jsonschema
import mock

from rally.common import utils
from rally import exceptions
from rally.plugins.openstack.context import api_versions
from tests.unit import test


class OpenStackServicesTestCase(test.TestCase):

    def setUp(self):
        super(OpenStackServicesTestCase, self).setUp()
        self.mock_clients = mock.patch("rally.osclients.Clients").start()
        osclient_kc = self.mock_clients.return_value.keystone
        self.mock_kc = osclient_kc.return_value
        self.service_catalog = osclient_kc.service_catalog
        self.service_catalog.get_endpoints.return_value = []
        self.mock_kc.services.list.return_value = []

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

    def test_setup_with_wrong_service_name(self):
        context = {
            "config": {api_versions.OpenStackAPIVersions.get_name(): {
                "nova": {"service_name": "service_name"}}},
            "admin": {"credential": mock.MagicMock()},
            "users": [{"credential": mock.MagicMock()}]}
        ctx = api_versions.OpenStackAPIVersions(context)
        self.assertRaises(exceptions.ValidationError, ctx.setup)
        self.service_catalog.get_endpoints.assert_called_once_with()
        self.mock_kc.services.list.assert_called_once_with()

    def test_setup_with_wrong_service_name_and_without_admin(self):
        context = {
            "config": {api_versions.OpenStackAPIVersions.get_name(): {
                "nova": {"service_name": "service_name"}}},
            "users": [{"credential": mock.MagicMock()}]}
        ctx = api_versions.OpenStackAPIVersions(context)
        self.assertRaises(exceptions.BenchmarkSetupFailure, ctx.setup)
        self.service_catalog.get_endpoints.assert_called_once_with()
        self.assertFalse(self.mock_kc.services.list.called)

    def test_setup_with_wrong_service_type(self):
        context = {
            "config": {api_versions.OpenStackAPIVersions.get_name(): {
                "nova": {"service_type": "service_type"}}},
            "users": [{"credential": mock.MagicMock()}]}
        ctx = api_versions.OpenStackAPIVersions(context)
        self.assertRaises(exceptions.ValidationError, ctx.setup)
        self.service_catalog.get_endpoints.assert_called_once_with()

    def test_setup_with_service_name(self):
        self.mock_kc.services.list.return_value = [
            utils.Struct(type="computev21", name="NovaV21")]
        name = api_versions.OpenStackAPIVersions.get_name()
        context = {
            "config": {name: {"nova": {"service_name": "NovaV21"}}},
            "admin": {"credential": mock.MagicMock()},
            "users": [{"credential": mock.MagicMock()}]}
        ctx = api_versions.OpenStackAPIVersions(context)
        ctx.setup()

        self.service_catalog.get_endpoints.assert_called_once_with()
        self.mock_kc.services.list.assert_called_once_with()

        self.assertEqual(
            "computev21",
            ctx.context["config"]["api_versions"]["nova"]["service_type"])
