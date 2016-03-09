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

from rally.plugins.openstack.cleanup import base
from tests.unit import test


BASE = "rally.plugins.openstack.cleanup.base"


class ResourceDecoratorTestCase(test.TestCase):

    def test_resource(self):

        @base.resource("service", "res")
        class Fake(object):
            pass

        self.assertEqual(Fake._service, "service")
        self.assertEqual(Fake._resource, "res")


class ResourceManagerTestCase(test.TestCase):

    def test__manager(self):
        user = mock.MagicMock()
        user.service1().resource1 = "user_res"

        manager = base.ResourceManager(user=user)
        manager._service = "service1"
        manager._resource = "resource1"

        self.assertEqual("user_res", manager._manager())

    def test__manager_admin(self):
        admin = mock.MagicMock()
        admin.service1().resource1 = "admin_res"

        manager = base.ResourceManager(admin=admin)
        manager._service = "service1"
        manager._resource = "resource1"
        manager._admin_required = True

        self.assertEqual("admin_res", manager._manager())

    def test_id(self):
        resource = mock.MagicMock(id="test_id")

        manager = base.ResourceManager(resource=resource)
        self.assertEqual(resource.id, manager.id())

    def test_name(self):
        resource = mock.MagicMock(name="test_name")

        manager = base.ResourceManager(resource=resource)
        self.assertEqual(resource.name, manager.name())

    @mock.patch("%s.ResourceManager._manager" % BASE)
    def test_is_deleted(self, mock_resource_manager__manager):
        raw_res = mock.MagicMock(status="deleted")
        mock_resource_manager__manager().get.return_value = raw_res
        mock_resource_manager__manager.reset_mock()

        resource = mock.MagicMock(id="test_id")

        manager = base.ResourceManager(resource=resource)
        self.assertTrue(manager.is_deleted())
        raw_res.status = "DELETE_COMPLETE"
        self.assertTrue(manager.is_deleted())
        raw_res.status = "ACTIVE"
        self.assertFalse(manager.is_deleted())

        mock_resource_manager__manager.assert_has_calls(
            [mock.call(), mock.call().get(resource.id)] * 3)
        self.assertEqual(mock_resource_manager__manager.call_count, 3)

    @mock.patch("%s.ResourceManager._manager" % BASE)
    def test_is_deleted_exceptions(self, mock_resource_manager__manager):

        class Fake500Exc(Exception):
            code = 500

        class Fake404Exc(Exception):
            code = 404

        mock_resource_manager__manager.side_effect = [
            Exception, Fake500Exc, Fake404Exc]

        manager = base.ResourceManager(resource=mock.MagicMock())
        self.assertFalse(manager.is_deleted())
        self.assertFalse(manager.is_deleted())
        self.assertTrue(manager.is_deleted())

    @mock.patch("%s.ResourceManager._manager" % BASE)
    def test_delete(self, mock_resource_manager__manager):
        res = mock.MagicMock(id="test_id")

        manager = base.ResourceManager(resource=res)
        manager.delete()

        mock_resource_manager__manager.assert_has_calls(
            [mock.call(), mock.call().delete(res.id)])

    @mock.patch("%s.ResourceManager._manager" % BASE)
    def test_list(self, mock_resource_manager__manager):
        base.ResourceManager().list()
        mock_resource_manager__manager.assert_has_calls(
            [mock.call(), mock.call().list()])
