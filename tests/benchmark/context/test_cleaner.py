# Copyright 2014: Mirantis Inc.
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

import mock

from rally.benchmark.context import cleaner as cleaner_ctx

from tests import fakes
from tests import test


BASE = "rally.benchmark.context.cleaner"


class ResourceCleanerTestCase(test.TestCase):

    def test_with_statement_no_user_no_admin(self):
        context = {
            "task": mock.MagicMock(),
            "admin": None,
            "users": [],
            "tenants": [],
            "scenario_name": "NovaServers.boot_server_from_volume_and_delete"
        }
        resource_cleaner = cleaner_ctx.ResourceCleaner(context)
        with resource_cleaner:
            resource_cleaner.setup()

    def test_with_statement(self):
        fake_user_ctx = fakes.FakeUserContext({}).context
        res_cleaner = cleaner_ctx.ResourceCleaner(fake_user_ctx)

        res_cleaner._cleanup_users_resources = mock.MagicMock()
        res_cleaner._cleanup_admin_resources = mock.MagicMock()

        with res_cleaner as cleaner:
            self.assertEqual(res_cleaner, cleaner)

        res_cleaner._cleanup_users_resources.assert_called_once_with()
        res_cleaner._cleanup_admin_resources.assert_called_once_with()

    @mock.patch("%s.osclients.Clients" % BASE)
    @mock.patch("%s.utils.delete_keystone_resources" % BASE)
    def test_cleaner_admin(self, mock_del_keystone, mock_clients):
        context = {
            "task": mock.MagicMock(),
            "scenario_name": 'NovaServers.boot_server_from_volume_and_delete',
            "admin": {"endpoint": mock.MagicMock()},
        }
        res_cleaner = cleaner_ctx.ResourceCleaner(context)

        mock_clients.return_value.keystone.return_value = 'keystone'

        with res_cleaner:
            res_cleaner.setup()

        mock_clients.assert_called_once_with(context["admin"]["endpoint"])
        mock_clients.return_value.keystone.assert_called_once_with()
        mock_del_keystone.assert_called_once_with('keystone')

    @mock.patch("rally.benchmark.scenarios.nova.servers.NovaServers."
                "boot_server_from_volume_and_delete")
    @mock.patch("%s.osclients.Clients" % BASE)
    @mock.patch("%s.utils.delete_nova_resources" % BASE)
    @mock.patch("%s.utils.delete_glance_resources" % BASE)
    @mock.patch("%s.utils.delete_cinder_resources" % BASE)
    def test_cleaner_users_all_services(self, mock_del_cinder,
                                        mock_del_glance, mock_del_nova,
                                        mock_clients, mock_scenario_method):
        del mock_scenario_method.cleanup_services
        context = {
            "task": mock.MagicMock(),
            "users": [{"endpoint": mock.MagicMock()},
                      {"endpoint": mock.MagicMock()}],
            "scenario_name": "NovaServers.boot_server_from_volume_and_delete",
            "tenants": [mock.MagicMock()]
        }
        res_cleaner = cleaner_ctx.ResourceCleaner(context)

        with res_cleaner:
            res_cleaner.setup()

        expected = [mock.call(context["users"][0]["endpoint"]),
                    mock.call(context["users"][1]["endpoint"])]
        mock_clients.assert_has_calls(expected, any_order=True)

        self.assertEqual(mock_del_nova.call_count, 2)
        self.assertEqual(mock_del_glance.call_count, 2)
        self.assertEqual(mock_del_cinder.call_count, 2)

    @mock.patch("%s.osclients.Clients" % BASE)
    @mock.patch("%s.utils.delete_nova_resources" % BASE)
    @mock.patch("%s.utils.delete_glance_resources" % BASE)
    @mock.patch("%s.utils.delete_cinder_resources" % BASE)
    def test_cleaner_users_by_service(self, mock_del_cinder, mock_del_glance,
                                      mock_del_nova, mock_clients):

        context = {
            "task": mock.MagicMock(),
            "users": [{"endpoint": mock.MagicMock()},
                      {"endpoint": mock.MagicMock()}],
            "scenario_name": 'NovaServers.boot_server_from_volume_and_delete',
            "tenants": [mock.MagicMock()]
        }
        res_cleaner = cleaner_ctx.ResourceCleaner(context)

        with res_cleaner:
            res_cleaner.setup()

        expected = [mock.call(context["users"][0]["endpoint"]),
                    mock.call(context["users"][1]["endpoint"])]
        mock_clients.assert_has_calls(expected, any_order=True)

        self.assertEqual(mock_del_nova.call_count, 2)
        self.assertEqual(mock_del_glance.call_count, 0)
        self.assertEqual(mock_del_cinder.call_count, 2)
