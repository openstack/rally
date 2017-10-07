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

from rally.common import utils
from rally import exceptions
from rally.plugins.openstack.context import api_versions
from rally.task import context
from tests.unit import test


@ddt.ddt
class OpenStackServicesTestCase(test.TestCase):

    def setUp(self):
        super(OpenStackServicesTestCase, self).setUp()
        self.mock_clients = mock.patch(
            "rally.plugins.openstack.osclients.Clients").start()
        osclient_kc = self.mock_clients.return_value.keystone
        self.mock_kc = osclient_kc.return_value
        self.service_catalog = osclient_kc.service_catalog
        self.service_catalog.get_endpoints.return_value = []
        self.mock_kc.services.list.return_value = []

    @ddt.data(({"nova": {"service_type": "compute", "version": 2},
                "cinder": {"service_name": "cinderv2", "version": 2},
                "neutron": {"service_type": "network"},
                "glance": {"service_name": "glance"},
                "heat": {"version": 1}}, True),
              ({"nova": {"service_type": "compute",
                         "service_name": "nova"}}, False),
              ({"keystone": {"service_type": "foo"}}, False),
              ({"nova": {"version": "foo"}}, False),
              ({}, False))
    @ddt.unpack
    def test_validate(self, config, valid):
        results = context.Context.validate("api_versions", None, None, config)
        if valid:
            self.assertEqual([], results)
        else:
            self.assertGreater(len(results), 0)

    def test_setup_with_wrong_service_name(self):
        context_obj = {
            "config": {api_versions.OpenStackAPIVersions.get_fullname(): {
                "nova": {"service_name": "service_name"}}},
            "admin": {"credential": mock.MagicMock()},
            "users": [{"credential": mock.MagicMock()}]}
        ctx = api_versions.OpenStackAPIVersions(context_obj)
        self.assertRaises(exceptions.ValidationError, ctx.setup)
        self.service_catalog.get_endpoints.assert_called_once_with()
        self.mock_kc.services.list.assert_called_once_with()

    def test_setup_with_wrong_service_name_and_without_admin(self):
        context_obj = {
            "config": {api_versions.OpenStackAPIVersions.get_fullname(): {
                "nova": {"service_name": "service_name"}}},
            "users": [{"credential": mock.MagicMock()}]}
        ctx = api_versions.OpenStackAPIVersions(context_obj)
        self.assertRaises(exceptions.ContextSetupFailure, ctx.setup)
        self.service_catalog.get_endpoints.assert_called_once_with()
        self.assertFalse(self.mock_kc.services.list.called)

    def test_setup_with_wrong_service_type(self):
        context_obj = {
            "config": {api_versions.OpenStackAPIVersions.get_fullname(): {
                "nova": {"service_type": "service_type"}}},
            "users": [{"credential": mock.MagicMock()}]}
        ctx = api_versions.OpenStackAPIVersions(context_obj)
        self.assertRaises(exceptions.ValidationError, ctx.setup)
        self.service_catalog.get_endpoints.assert_called_once_with()

    def test_setup_with_service_name(self):
        self.mock_kc.services.list.return_value = [
            utils.Struct(type="computev21", name="NovaV21")]
        name = api_versions.OpenStackAPIVersions.get_fullname()
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
