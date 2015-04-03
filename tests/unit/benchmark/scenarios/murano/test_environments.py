# Copyright 2015: Mirantis Inc.
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

from rally.benchmark.scenarios.murano import environments
from tests.unit import test

CTX = "rally.benchmark.context"
MURANO_SCENARIO = ("rally.benchmark.scenarios.murano."
                   "environments.MuranoEnvironments")


class MuranoEnvironmentsTestCase(test.TestCase):

    @mock.patch(MURANO_SCENARIO + "._list_environments")
    def test_list_environments(self, mock_list):
        scenario = environments.MuranoEnvironments()
        scenario._list_environments()
        mock_list.assert_called_once_with()

    @mock.patch(MURANO_SCENARIO + "._create_session")
    @mock.patch(MURANO_SCENARIO + "._delete_environment")
    @mock.patch(MURANO_SCENARIO + "._create_environment")
    @mock.patch(MURANO_SCENARIO + "._generate_random_name")
    def test_create_and_delete_environment(self, mock_random_name,
                                           mock_create, mock_delete,
                                           mock_session):
        scenario = environments.MuranoEnvironments()
        fake_environment = mock.Mock(id="fake_id")
        mock_create.return_value = fake_environment
        mock_random_name.return_value = "foo"
        scenario.create_and_delete_environment()
        mock_create.assert_called_once_with()
        mock_session.assert_called_once_with(fake_environment.id)
        mock_delete.assert_called_once_with(fake_environment)
