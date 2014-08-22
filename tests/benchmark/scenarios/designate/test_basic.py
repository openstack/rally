# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# Author: Endre Karlson <endre.karlson@hp.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock

from rally.benchmark.scenarios.designate import basic
from tests import test

DESIGNATE_BASIC = "rally.benchmark.scenarios.designate.basic.DesignateBasic"


class DesignateBasicTestCase(test.TestCase):

    @mock.patch(DESIGNATE_BASIC + "._list_domains")
    @mock.patch(DESIGNATE_BASIC + "._create_domain")
    def test_create_and_list_networks(self, mock_create, mock_list):
        scenario = basic.DesignateBasic()

        # Default options
        scenario.create_and_list_domains()
        mock_create.assert_called_once_with()
        mock_list.assert_called_once_with()

    @mock.patch(DESIGNATE_BASIC + "._delete_domain")
    @mock.patch(DESIGNATE_BASIC + "._create_domain")
    def test_create_and_delete_domain(self, mock_create, mock_delete):
        scenario = basic.DesignateBasic()

        mock_create.return_value = {"id": "123"}

        # Default options
        scenario.create_and_delete_domain()

        mock_create.assert_called_once_with()
        mock_delete.assert_called_once_with("123")

    @mock.patch(DESIGNATE_BASIC + "._list_domains")
    def test_list_domains(self, mock_list):
        scenario = basic.DesignateBasic()

        # Default options
        scenario.list_domains()
        mock_list.assert_called_once_with()
