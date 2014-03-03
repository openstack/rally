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
            "tenants": []
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

    @mock.patch("%s.utils.create_openstack_clients" % BASE)
    @mock.patch("%s.utils.delete_keystone_resources" % BASE)
    def test_cleaner_admin(self, mock_del_keystone, mock_create_os_clients):
        context = {
            "task": mock.MagicMock(),
            "admin": {"endpoint": mock.MagicMock()},
        }
        res_cleaner = cleaner_ctx.ResourceCleaner(context)

        admin_client = mock.MagicMock()
        admin_client.__getitem__ = mock.MagicMock(return_value="keystone_cl")
        mock_create_os_clients.return_value = admin_client

        with res_cleaner:
            res_cleaner.setup()

        mock_create_os_clients.assert_called_once_with(
            context["admin"]["endpoint"])
        admin_client.__getitem__.assert_called_once_with("keystone")
        mock_del_keystone.assert_called_once_with("keystone_cl")

    @mock.patch("%s.utils.create_openstack_clients" % BASE)
    @mock.patch("%s.utils.delete_nova_resources" % BASE)
    @mock.patch("%s.utils.delete_glance_resources" % BASE)
    @mock.patch("%s.utils.delete_cinder_resources" % BASE)
    def test_cleaner_users(self, mock_del_cinder, mock_del_glance,
                           mock_del_nova, mock_create_os_clients):

        context = {
            "task": mock.MagicMock(),
            "users": [{"endpoint": mock.MagicMock()},
                      {"endpoint": mock.MagicMock()}],
            "tenants": [mock.MagicMock()]
        }
        res_cleaner = cleaner_ctx.ResourceCleaner(context)

        client = mock.MagicMock()
        client.__getitem__ = mock.MagicMock(side_effect=lambda cl: cl + "_cl")
        mock_create_os_clients.return_value = client

        with res_cleaner:
            res_cleaner.setup()

        expected = [mock.call(context["users"][0]["endpoint"]),
                    mock.call(context["users"][1]["endpoint"])]
        mock_create_os_clients.assert_has_calls(expected, any_order=True)

        os_clients = ["nova", "glance", "keystone", "cinder"]
        expected = [mock.call(c) for c in os_clients] * len(context["users"])
        self.assertEqual(client.__getitem__.mock_calls, expected)

        expected = [mock.call("nova_cl")] * len(context["users"])
        self.assertEqual(mock_del_nova.mock_calls, expected)
        expected = [mock.call("glance_cl",
                              "keystone_cl")] * len(context["users"])
        self.assertEqual(mock_del_glance.mock_calls, expected)
        expected = [mock.call("cinder_cl")] * len(context["users"])
        self.assertEqual(mock_del_cinder.mock_calls, expected)
