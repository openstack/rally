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

from rally.benchmark.context.cleanup import admin_cleanup
from tests import fakes
from tests import test


BASE = "rally.benchmark.context.cleanup.admin_cleanup"


class AdminCleanupTestCase(test.TestCase):

    def test_with_statement(self):
        fake_admin_ctx = fakes.FakeUserContext({}).context
        fake_admin_ctx["config"] = {"admin_cleanup": ["keystone"]}
        admin_cleaner = admin_cleanup.AdminCleanup(fake_admin_ctx)
        admin_cleaner.setup()

        admin_cleaner._cleanup_resources = mock.MagicMock()

        with admin_cleaner as cleaner:
            self.assertEqual(admin_cleaner, cleaner)

        admin_cleaner._cleanup_resources.assert_called_once_with()

    @mock.patch("%s.osclients.Clients" % BASE)
    @mock.patch("%s.utils.delete_keystone_resources" % BASE)
    def test_cleaner_admin(self, mock_del_keystone, mock_clients):
        context = {
            "task": mock.MagicMock(),
            "config": {"admin_cleanup": ["keystone"]},
            "admin": {"endpoint": mock.MagicMock()},
        }
        res_cleaner = admin_cleanup.AdminCleanup(context)

        fake_keystone = mock.MagicMock()
        mock_clients.return_value.keystone.return_value = fake_keystone

        with res_cleaner:
            res_cleaner.setup()

        mock_clients.assert_called_once_with(context["admin"]["endpoint"])
        mock_clients.return_value.keystone.assert_called_with()
        mock_del_keystone.assert_called_once_with(fake_keystone)
