# Copyright 2015 Mirantis Inc.
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

import ddt
import mock

from rally.plugins.openstack.scenarios.manila import shares
from tests.unit import test


@ddt.ddt
class ManilaSharesTestCase(test.TestCase):

    @ddt.data(
        {},
        {"detailed": True},
        {"detailed": False},
        {"search_opts": None},
        {"search_opts": {}},
        {"search_opts": {"foo": "bar"}},
        {"detailed": True, "search_opts": None},
        {"detailed": False, "search_opts": None},
        {"detailed": True, "search_opts": {"foo": "bar"}},
        {"detailed": False, "search_opts": {"quuz": "foo"}},
    )
    @ddt.unpack
    def test_list_shares(self, detailed=True, search_opts=None):
        scenario = shares.ManilaShares()
        scenario._list_shares = mock.MagicMock()

        scenario.list_shares(detailed=detailed, search_opts=search_opts)

        scenario._list_shares.assert_called_once_with(
            detailed=detailed, search_opts=search_opts)
