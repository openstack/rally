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

from rally.plugins.openstack.context.network import allow_ssh
from tests.unit import fakes
from tests.unit import test


CTX = "rally.plugins.openstack.context.network.allow_ssh"


class AllowSSHContextTestCase(test.TestCase):

    def setUp(self):
        super(AllowSSHContextTestCase, self).setUp()
        self.users = 2
        self.secgroup_name = "test-secgroup"

        self.ctx_with_secgroup = test.get_test_context()
        self.ctx_with_secgroup.update({
            "users": [
                {
                    "tenant_id": "uuid1",
                    "credential": "credential",
                    "secgroup": {"id": "secgroup_id", "name": "secgroup"}
                }
            ] * self.users,
            "admin": {"tenant_id": "uuid2", "credential": "admin_credential"},
            "tenants": {"uuid1": {"id": "uuid1", "name": "uuid1"}},
        })
        self.ctx_without_secgroup = test.get_test_context()
        self.ctx_without_secgroup.update({
            "users": [{"tenant_id": "uuid1",
                       "credential": "credential"},
                      {"tenant_id": "uuid1",
                       "credential": "credential"}],
            "admin": {"tenant_id": "uuid2", "credential": "admin_credential"},
            "tenants": {"uuid1": {"id": "uuid1", "name": "uuid1"}},
        })

    @mock.patch("%s.osclients.Clients" % CTX)
    def test__prepare_open_secgroup(self, mock_clients):
        fake_nova = fakes.FakeNovaClient()
        self.assertEqual(len(fake_nova.security_groups.list()), 1)
        mock_cl = mock.MagicMock()
        mock_cl.nova.return_value = fake_nova
        mock_clients.return_value = mock_cl

        ret = allow_ssh._prepare_open_secgroup("credential",
                                               self.secgroup_name)
        self.assertEqual(self.secgroup_name, ret["name"])

        self.assertEqual(2, len(fake_nova.security_groups.list()))
        self.assertIn(
            self.secgroup_name,
            [sg.name for sg in fake_nova.security_groups.list()])

        # run prep again, check that another security group is not created
        allow_ssh._prepare_open_secgroup("credential", self.secgroup_name)
        self.assertEqual(2, len(fake_nova.security_groups.list()))

    @mock.patch("%s.osclients.Clients" % CTX)
    def test__prepare_open_secgroup_rules(self, mock_clients):
        fake_nova = fakes.FakeNovaClient()

        # NOTE(hughsaunders) Default security group is precreated
        self.assertEqual(1, len(fake_nova.security_groups.list()))
        mock_cl = mock.MagicMock()
        mock_cl.nova.return_value = fake_nova
        mock_clients.return_value = mock_cl

        allow_ssh._prepare_open_secgroup("credential", self.secgroup_name)

        self.assertEqual(2, len(fake_nova.security_groups.list()))
        rally_open = fake_nova.security_groups.find(self.secgroup_name)
        self.assertEqual(3, len(rally_open.rules))

        # run prep again, check that extra rules are not created
        allow_ssh._prepare_open_secgroup("credential", self.secgroup_name)
        rally_open = fake_nova.security_groups.find(self.secgroup_name)
        self.assertEqual(3, len(rally_open.rules))

    @mock.patch("%s.osclients.Clients" % CTX)
    @mock.patch("%s._prepare_open_secgroup" % CTX)
    @mock.patch("rally.plugins.openstack.wrappers.network.wrap")
    def test_secgroup_setup_cleanup_with_secgroup_supported(
            self, mock_network_wrap, mock__prepare_open_secgroup,
            mock_clients):
        mock_network_wrapper = mock.MagicMock()
        mock_network_wrapper.supports_extension.return_value = (
            True, "")
        mock_network_wrap.return_value = mock_network_wrapper
        mock__prepare_open_secgroup.return_value = {
            "name": "secgroup",
            "id": "secgroup_id"}
        mock_clients.return_value = mock.MagicMock()

        secgrp_ctx = allow_ssh.AllowSSH(self.ctx_with_secgroup)
        secgrp_ctx.setup()
        self.assertEqual(self.ctx_with_secgroup, secgrp_ctx.context)
        secgrp_ctx.cleanup()

        self.assertEqual(
            [
                mock.call("admin_credential"),
                mock.call("credential"),
                mock.call().nova(),
                mock.call().nova().security_groups.get("secgroup_id"),
                mock.call().nova().security_groups.get().delete()
            ],
            mock_clients.mock_calls)

        mock_network_wrap.assert_called_once_with(
            mock_clients.return_value, secgrp_ctx, config={})

    @mock.patch("%s.osclients.Clients" % CTX)
    @mock.patch("rally.plugins.openstack.wrappers.network.wrap")
    def test_secgroup_setup_with_secgroup_unsupported(
            self, mock_network_wrap, mock_clients):
        mock_network_wrapper = mock.MagicMock()
        mock_network_wrapper.supports_extension.return_value = (
            False, "Not supported")
        mock_network_wrap.return_value = mock_network_wrapper
        mock_clients.return_value = mock.MagicMock()

        secgrp_ctx = allow_ssh.AllowSSH(dict(self.ctx_without_secgroup))
        secgrp_ctx.setup()
        self.assertEqual(self.ctx_without_secgroup, secgrp_ctx.context)

        mock_clients.assert_called_once_with("admin_credential")

        mock_network_wrap.assert_called_once_with(
            mock_clients.return_value, secgrp_ctx, config={})
