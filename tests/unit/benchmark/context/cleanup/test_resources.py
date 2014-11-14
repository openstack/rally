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
from neutronclient.common import exceptions as neutron_exceptions

from rally.benchmark.context.cleanup import base
from rally.benchmark.context.cleanup import resources
from rally.benchmark.scenarios.keystone import utils as keystone_utils
from rally import utils
from tests.unit import test

BASE = "rally.benchmark.context.cleanup.resources"


class AllResourceManagerTestCase(test.TestCase):

    def test_res_manager_special_field(self):

        for res_mgr in utils.itersubclasses(base.ResourceManager):
            manager_name = "%s.%s" % (res_mgr.__module__, res_mgr.__name__)

            fields = filter(lambda x: not x.startswith("__"), dir(res_mgr))

            available_opts = set([
                "_admin_required", "_perform_for_admin_only",
                "_tenant_resource", "_service", "_resource", "_order",
                "_max_attempts", "_timeout", "_interval", "_threads",
                "_manager", "id", "is_deleted", "delete", "list"
            ])

            extra_opts = set(fields) - available_opts

            self.assertFalse(
                extra_opts,
                ("ResourceManager %(name)s contains extra fields: %(opts)s."
                 " Remove them to pass this test")
                % {"name": manager_name, "opts": ", ".join(extra_opts)})


class SynchronizedDeletionTestCase(test.TestCase):

    def test_is_deleted(self):
        self.assertTrue(resources.SynchronizedDeletion().is_deleted())


class QuotaMixinTestCase(test.TestCase):

    def test_id(self):
        quota = resources.QuotaMixin()
        quota.raw_resource = mock.MagicMock()
        self.assertEqual(quota.raw_resource, quota.id())

    def test_delete(self):
        quota = resources.QuotaMixin()
        mock_manager = mock.MagicMock()
        quota._manager = lambda: mock_manager
        quota.raw_resource = mock.MagicMock()

        quota.delete()
        mock_manager.delete.assert_called_once_with(quota.raw_resource)

    def test_list(self):
        quota = resources.QuotaMixin()
        quota.tenant_uuid = None
        self.assertEqual([], quota.list())

        quota.tenant_uuid = mock.MagicMock()
        self.assertEqual([quota.tenant_uuid], quota.list())


class NovaSecurityGroupTestCase(test.TestCase):

    @mock.patch("%s.base.ResourceManager._manager" % BASE)
    def test_list(self, mock_manager):
        secgroups = [mock.MagicMock(), mock.MagicMock(), mock.MagicMock()]
        secgroups[0].name = "a"
        secgroups[1].name = "b"
        secgroups[2].name = "default"

        mock_manager().list.return_value = secgroups
        self.assertEqual(secgroups[:2], resources.NovaSecurityGroup().list())


class NeutronMixinTestCase(test.TestCase):

    def get_neutron_mixin(self):
        neut = resources.NeutronMixin()
        neut._service = "neutron"
        return neut

    def test_manager(self):
        neut = self.get_neutron_mixin()
        neut.user = mock.MagicMock()
        self.assertEqual(neut.user.neutron.return_value, neut._manager())

    def test_id(self):
        neut = self.get_neutron_mixin()
        neut.raw_resource = {"id": "test"}
        self.assertEqual("test", neut.id())

    def test_delete(self):
        neut = self.get_neutron_mixin()
        neut.user = mock.MagicMock()
        neut._resource = "some_resource"
        neut.raw_resource = {"id": "42"}

        neut.delete()
        neut.user.neutron().delete_some_resource.assert_called_once_with("42")

    def test_list(self):
        neut = self.get_neutron_mixin()
        neut.user = mock.MagicMock()
        neut._resource = "some_resource"
        neut.tenant_uuid = "user_tenant"

        some_resources = [{"tenant_id": neut.tenant_uuid}, {"tenant_id": "a"}]
        neut.user.neutron().list_some_resources.return_value = {
            "some_resources": some_resources
        }

        self.assertEqual([some_resources[0]], neut.list())

        neut.user.neutron().list_some_resources.assert_called_once_with(
            {"tenant_id": neut.tenant_uuid})


class NeutronPortTestCase(test.TestCase):

    def test_delete(self):
        raw_res = {"device_owner": "abbabaab", "id": "some_id"}
        user = mock.MagicMock()

        resources.NeutronPort(resource=raw_res, user=user).delete()

        user.neutron().delete_port.assert_called_once_with(raw_res["id"])

    def test_delete_port_raise_exception(self):
        raw_res = {"device_owner": "abbabaab", "id": "some_id"}
        user = mock.MagicMock()
        user.neutron().delete_port.side_effect = (
            neutron_exceptions.PortNotFoundClient)

        resources.NeutronPort(resource=raw_res, user=user).delete()

        user.neutron().delete_port.assert_called_once_with(raw_res["id"])

    def test_delete_port_device_owner(self):
        raw_res = {
            "device_owner": "network:router_interface",
            "id": "some_id",
            "device_id": "dev_id"
        }
        user = mock.MagicMock()

        resources.NeutronPort(resource=raw_res, user=user).delete()

        user.neutron().remove_interface_router.assert_called_once_with(
            raw_res["device_id"], {"port_id": raw_res["id"]})


class GlanceImageTestCase(test.TestCase):

    @mock.patch("%s.GlanceImage._manager" % BASE)
    def test_list(self, mock_manager):
        glance = resources.GlanceImage()
        glance.tenant_uuid = mock.MagicMock()

        mock_manager().list.return_value = ["a", "b", "c"]

        self.assertEqual(["a", "b", "c"], glance.list())
        mock_manager().list.assert_called_once_with(owner=glance.tenant_uuid)


class CeilometerTestCase(test.TestCase):

    def test_id(self):
        ceil = resources.CeilometerAlarms()
        ceil.raw_resource = mock.MagicMock()
        self.assertEqual(ceil.raw_resource.alarm_id, ceil.id())

    @mock.patch("%s.CeilometerAlarms._manager" % BASE)
    def test_list(self, mock_manager):

        ceil = resources.CeilometerAlarms()
        ceil.tenant_uuid = mock.MagicMock()
        mock_manager().list.return_value = ["a", "b", "c"]
        mock_manager.reset_mock()

        self.assertEqual(["a", "b", "c"], ceil.list())
        mock_manager().list.assert_called_once_with(
            q=[{"field": "project_id", "op": "eq", "value": ceil.tenant_uuid}])


class KeystoneMixinTestCase(test.TestCase):

    def test_is_deleted(self):
        self.assertTrue(resources.KeystoneMixin().is_deleted())

    def get_keystone_mixin(self):
        kmixin = resources.KeystoneMixin()
        kmixin._service = "keystone"
        return kmixin

    @mock.patch("%s.keystone_wrapper.wrap" % BASE)
    def test_manager(self, mock_wrap):
        keystone_mixin = self.get_keystone_mixin()
        keystone_mixin.admin = mock.MagicMock()
        self.assertEqual(mock_wrap.return_value, keystone_mixin._manager())
        mock_wrap.assert_called_once_with(
            keystone_mixin.admin.keystone.return_value)

    @mock.patch("%s.keystone_wrapper.wrap" % BASE)
    def test_delete(self, mock_wrap):
        keystone_mixin = self.get_keystone_mixin()
        keystone_mixin._resource = "some_resource"
        keystone_mixin.id = lambda: "id_a"
        keystone_mixin.admin = mock.MagicMock()

        keystone_mixin.delete()
        mock_wrap.assert_called_once_with(
            keystone_mixin.admin.keystone.return_value)
        mock_wrap().delete_some_resource.assert_called_once_with("id_a")

    @mock.patch("%s.keystone_wrapper.wrap" % BASE)
    def test_list(self, mock_wrap):
        keystone_mixin = self.get_keystone_mixin()
        keystone_mixin._resource = "some_resource2"
        keystone_mixin.admin = mock.MagicMock()

        result = [mock.MagicMock(), mock.MagicMock(), mock.MagicMock()]
        prefix = keystone_utils.KeystoneScenario.RESOURCE_NAME_PREFIX
        result[0].name = prefix + "keystone-a"
        result[1].name = prefix + "keystone-b"
        result[2].name = "not_a_keystone_pattern"

        mock_wrap().list_some_resource2s.return_value = result

        self.assertEqual(result[:2], keystone_mixin.list())
        mock_wrap().list_some_resource2s.assert_called_once_with()
