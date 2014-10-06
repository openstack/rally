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

from rally.benchmark.context.cleanup import user_cleanup
from tests.unit import fakes
from tests.unit import test


BASE = "rally.benchmark.context.cleanup.user_cleanup"


class UserCleanupTestCase(test.TestCase):

    def test_with_statement_no_user(self):
        context = {
            "task": mock.MagicMock(),
            "admin": mock.MagicMock(),
            "users": [],
            "tenants": [],
        }
        user_cleaner = user_cleanup.UserCleanup(context)
        with user_cleaner:
            user_cleaner.setup()

    def test_with_statement(self):
        fake_user_ctx = fakes.FakeUserContext({}).context
        fake_user_ctx["config"] = {"cleanup": ["nova"]}
        user_cleaner = user_cleanup.UserCleanup(fake_user_ctx)
        user_cleaner.setup()

        user_cleaner._cleanup_resources = mock.MagicMock()

        with user_cleaner as cleaner:
            self.assertEqual(user_cleaner, cleaner)

        user_cleaner._cleanup_resources.assert_called_once_with()

    @mock.patch("%s.osclients.Clients" % BASE)
    @mock.patch("%s.utils.delete_nova_resources" % BASE)
    @mock.patch("%s.utils.delete_glance_resources" % BASE)
    @mock.patch("%s.utils.delete_cinder_resources" % BASE)
    @mock.patch("%s.utils.delete_neutron_resources" % BASE)
    def test_cleaner_resources(self, mock_del_neutron, mock_del_cinder,
                               mock_del_glance, mock_del_nova, mock_clients):
        context = {
            "task": mock.MagicMock(),
            "users": [{"endpoint": mock.MagicMock()},
                      {"endpoint": mock.MagicMock()}],
            "config": {"cleanup": ["cinder", "nova", "glance", "neutron"]},
            "tenants": [mock.MagicMock()]
        }
        user_cleaner = user_cleanup.UserCleanup(context)

        with user_cleaner:
            user_cleaner.setup()

        expected = [mock.call(context["users"][0]["endpoint"]),
                    mock.call(context["users"][1]["endpoint"])]
        mock_clients.assert_has_calls(expected, any_order=True)

        self.assertEqual(mock_del_nova.call_count, 2)
        self.assertEqual(mock_del_glance.call_count, 2)
        self.assertEqual(mock_del_cinder.call_count, 2)
        self.assertEqual(mock_del_neutron.call_count, 2)

    @mock.patch("%s.UserCleanup._cleanup_resources" % BASE)
    def test_cleaner_default_behavior(self, mock_cleanup):
        context = {
            "task": mock.MagicMock(),
            "users": [{"endpoint": mock.MagicMock()},
                      {"endpoint": mock.MagicMock()}],
        }
        user_cleaner = user_cleanup.UserCleanup(context)

        with user_cleaner:
            user_cleaner.setup()

        self.assertEqual(mock_cleanup.call_count, 0)
