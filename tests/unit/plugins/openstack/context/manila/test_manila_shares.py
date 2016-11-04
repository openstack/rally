# Copyright 2016 Mirantis Inc.
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

import copy

import ddt
import mock
import six

from rally import consts as rally_consts
from rally.plugins.openstack.context.manila import consts
from rally.plugins.openstack.context.manila import manila_shares
from tests.unit import test

MANILA_UTILS_PATH = (
    "rally.plugins.openstack.scenarios.manila.utils.ManilaScenario.")


class Fake(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getitem__(self, item):
        return getattr(self, item)

    def to_dict(self):
        return self.__dict__


@ddt.ddt
class SharesTestCase(test.TestCase):
    TENANTS_AMOUNT = 3
    USERS_PER_TENANT = 4
    SHARES_PER_TENANT = 7
    SHARE_NETWORKS = [{"id": "sn_%s_id" % d} for d in range(3)]

    def _get_context(self, use_share_networks=False, shares_per_tenant=None,
                     share_size=1, share_proto="fake_proto", share_type=None):
        tenants = {}
        for t_id in range(self.TENANTS_AMOUNT):
            tenants[six.text_type(t_id)] = {"name": six.text_type(t_id)}
        users = []
        for t_id in sorted(list(tenants.keys())):
            for i in range(self.USERS_PER_TENANT):
                users.append(
                    {"id": i, "tenant_id": t_id, "credential": "fake"})
        context = {
            "config": {
                "users": {
                    "tenants": self.TENANTS_AMOUNT,
                    "users_per_tenant": self.USERS_PER_TENANT,
                    "user_choice_method": "round_robin",
                },
                consts.SHARE_NETWORKS_CONTEXT_NAME: {
                    "use_share_networks": use_share_networks,
                    "share_networks": self.SHARE_NETWORKS,
                },
                consts.SHARES_CONTEXT_NAME: {
                    "shares_per_tenant": (
                        shares_per_tenant or self.SHARES_PER_TENANT),
                    "size": share_size,
                    "share_proto": share_proto,
                    "share_type": share_type,
                },
            },
            "admin": {
                "credential": mock.MagicMock(),
            },
            "task": mock.MagicMock(),
            "users": users,
            "tenants": tenants,
        }
        if use_share_networks:
            for t in context["tenants"].keys():
                context["tenants"][t][consts.SHARE_NETWORKS_CONTEXT_NAME] = {
                    "share_networks": self.SHARE_NETWORKS,
                }
        return context

    def test_init(self):
        ctxt = {
            "task": mock.MagicMock(),
            "config": {
                consts.SHARES_CONTEXT_NAME: {"foo": "bar"},
                "fake": {"fake_key": "fake_value"},
            },
        }

        inst = manila_shares.Shares(ctxt)

        self.assertEqual(
            {"foo": "bar", "shares_per_tenant": 1, "size": 1,
             "share_proto": "NFS", "share_type": None},
            inst.config)
        self.assertIn(
            rally_consts.JSON_SCHEMA, inst.CONFIG_SCHEMA.get("$schema"))
        self.assertFalse(inst.CONFIG_SCHEMA.get("additionalProperties"))
        self.assertEqual("object", inst.CONFIG_SCHEMA.get("type"))
        props = inst.CONFIG_SCHEMA.get("properties", {})
        self.assertEqual(
            {"minimum": 1, "type": "integer"}, props.get("shares_per_tenant"))
        self.assertEqual({"minimum": 1, "type": "integer"}, props.get("size"))
        self.assertEqual({"type": "string"}, props.get("share_proto"))
        self.assertEqual({"type": "string"}, props.get("share_type"))
        self.assertEqual(455, inst.get_order())
        self.assertEqual(consts.SHARES_CONTEXT_NAME, inst.get_name())

    @mock.patch(MANILA_UTILS_PATH + "_create_share")
    @ddt.data(True, False)
    def test_setup(
            self,
            use_share_networks,
            mock_manila_scenario__create_share):
        share_type = "fake_share_type"
        ctxt = self._get_context(
            use_share_networks=use_share_networks, share_type=share_type)
        inst = manila_shares.Shares(ctxt)
        shares = [
            Fake(id="fake_share_id_%d" % s_id)
            for s_id in range(self.TENANTS_AMOUNT * self.SHARES_PER_TENANT)
        ]
        mock_manila_scenario__create_share.side_effect = shares
        expected_ctxt = copy.deepcopy(ctxt)

        inst.setup()

        self.assertEqual(
            self.TENANTS_AMOUNT * self.SHARES_PER_TENANT,
            mock_manila_scenario__create_share.call_count)
        for d in range(self.TENANTS_AMOUNT):
            self.assertEqual(
                [
                    s.to_dict() for s in shares[
                        (d * self.SHARES_PER_TENANT):(
                            d * self.SHARES_PER_TENANT + self.SHARES_PER_TENANT
                        )
                    ]
                ],
                inst.context.get("tenants", {}).get("%s" % d, {}).get("shares")
            )
        self.assertEqual(expected_ctxt["task"], inst.context.get("task"))
        self.assertEqual(expected_ctxt["config"], inst.context.get("config"))
        self.assertEqual(expected_ctxt["users"], inst.context.get("users"))
        if use_share_networks:
            mock_calls = [
                mock.call(
                    share_proto=ctxt["config"][consts.SHARES_CONTEXT_NAME][
                        "share_proto"],
                    size=ctxt["config"][consts.SHARES_CONTEXT_NAME]["size"],
                    share_type=ctxt["config"][consts.SHARES_CONTEXT_NAME][
                        "share_type"],
                    share_network=self.SHARE_NETWORKS[
                        int(t_id) % len(self.SHARE_NETWORKS)]["id"]
                ) for t_id in expected_ctxt["tenants"].keys()
            ]
        else:
            mock_calls = [
                mock.call(
                    share_proto=ctxt["config"][consts.SHARES_CONTEXT_NAME][
                        "share_proto"],
                    size=ctxt["config"][consts.SHARES_CONTEXT_NAME]["size"],
                    share_type=ctxt["config"][consts.SHARES_CONTEXT_NAME][
                        "share_type"],
                ) for t_id in expected_ctxt["tenants"].keys()
            ]
        mock_manila_scenario__create_share.assert_has_calls(
            mock_calls, any_order=True)

    @mock.patch(MANILA_UTILS_PATH + "_create_share")
    @mock.patch("rally.plugins.openstack.cleanup.manager.cleanup")
    def test_cleanup(
            self,
            mock_cleanup_manager_cleanup,
            mock_manila_scenario__create_share):
        ctxt = self._get_context()
        inst = manila_shares.Shares(ctxt)
        shares = [
            Fake(id="fake_share_id_%d" % s_id)
            for s_id in range(self.TENANTS_AMOUNT * self.SHARES_PER_TENANT)
        ]
        mock_manila_scenario__create_share.side_effect = shares
        inst.setup()

        inst.cleanup()

        mock_cleanup_manager_cleanup.assert_called_once_with(
            names=["manila.shares"],
            users=inst.context.get("users", []),
        )
