# Copyright 2013: Mirantis Inc.
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

from rally.benchmark.scenarios.keystone import basic
from tests import test


KEYSTONE_BASE = "rally.benchmark.scenarios.keystone."
KEYSTONE_BASIC = KEYSTONE_BASE + "basic.KeystoneBasic."
KEYSTONE_UTILS = KEYSTONE_BASE + "utils."


class KeystoneBasicTestCase(test.TestCase):

    @mock.patch(KEYSTONE_UTILS + "generate_keystone_name")
    @mock.patch(KEYSTONE_BASIC + "_user_create")
    def test_create_user(self, mock_create, mock_gen_name):
        mock_gen_name.return_value = "teeeest"
        basic.KeystoneBasic.create_user(name_length=20, password="tttt",
                                        **{"tenant_id": "id"})

        mock_create.assert_called_once_with(name_length=20, password="tttt",
                                            **{"tenant_id": "id"})

    @mock.patch(KEYSTONE_UTILS + "generate_keystone_name")
    @mock.patch(KEYSTONE_BASIC + "_resource_delete")
    @mock.patch(KEYSTONE_BASIC + "_user_create")
    def test_create_delete_user(self, mock_create, mock_delete, mock_gen_name):
        create_result = {}
        mock_create.return_value = create_result
        mock_gen_name.return_value = "teeeest"

        basic.KeystoneBasic.create_delete_user(name_length=30, email="abcd",
                                               **{"enabled": True})

        mock_create.assert_called_once_with(name_length=30, email="abcd",
                                            **{"enabled": True})
        mock_delete.assert_called_once_with(create_result)
