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

import jsonschema
import mock

from rally.plugins.openstack.context.cleanup import base
from rally.plugins.openstack.context.cleanup import user
from tests.unit import test


BASE = "rally.plugins.openstack.context.cleanup.user"


class UserCleanupTestCase(test.TestCase):

    @mock.patch("%s.manager" % BASE)
    def test_validate(self, mock_manager):
        mock_manager.list_resource_names.return_value = set(["a", "b", "c"])
        user.UserCleanup.validate(["a"])
        mock_manager.list_resource_names.assert_called_once_with(
            admin_required=False)

    @mock.patch("%s.manager" % BASE)
    def test_validate_no_such_cleanup(self, mock_manager):
        mock_manager.list_resource_names.return_value = set(["a", "b", "c"])
        self.assertRaises(base.NoSuchCleanupResources,
                          user.UserCleanup.validate, ["a", "b", "d"])
        mock_manager.list_resource_names.assert_called_once_with(
            admin_required=False)

    def test_validate_invalid_config(self):
        self.assertRaises(jsonschema.ValidationError,
                          user.UserCleanup.validate, {})

    @mock.patch("%s.manager.find_resource_managers" % BASE,
                return_value=[mock.MagicMock(), mock.MagicMock()])
    @mock.patch("%s.manager.SeekAndDestroy" % BASE)
    def test_cleanup(self, mock_seek_and_destroy, mock_find_resource_managers):

        ctx = {
            "config": {"cleanup": ["a", "b"]},
            "users": mock.MagicMock(),
            "task": mock.MagicMock()
        }

        admin_cleanup = user.UserCleanup(ctx)
        admin_cleanup.setup()
        admin_cleanup.cleanup()

        mock_find_resource_managers.assert_called_once_with(("a", "b"), False)

        mock_seek_and_destroy.assert_has_calls([
            mock.call(
                mock_find_resource_managers.return_value[0],
                None, ctx["users"], None),
            mock.call().exterminate(),
            mock.call(
                mock_find_resource_managers.return_value[1],
                None, ctx["users"], None),
            mock.call().exterminate()
        ])

    @mock.patch("%s.manager.find_resource_managers" % BASE,
                return_value=[mock.MagicMock(), mock.MagicMock()])
    @mock.patch("%s.manager.SeekAndDestroy" % BASE)
    def test_cleanup_user_with_api_versions(
            self,
            mock_seek_and_destroy,
            mock_find_resource_managers):

        ctx = {
            "config":
                {"admin_cleanup": ["a", "b"],
                 "api_versions":
                     {"cinder":
                         {"version": "1",
                          "service_type": "volume"
                          }
                      }
                 },
            "admin": mock.MagicMock(),
            "users": mock.MagicMock(),
            "task": mock.MagicMock()
        }

        user_cleanup = user.UserCleanup(ctx)
        user_cleanup.setup()
        user_cleanup.cleanup()

        mock_find_resource_managers.assert_called_once_with({}, False)
        mock_seek_and_destroy.assert_has_calls([
            mock.call(
                mock_find_resource_managers.return_value[0],
                None,
                ctx["users"],
                ctx["config"]["api_versions"]),
            mock.call().exterminate(),
            mock.call(
                mock_find_resource_managers.return_value[1],
                None,
                ctx["users"],
                ctx["config"]["api_versions"]),
            mock.call().exterminate()
        ])
